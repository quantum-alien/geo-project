from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models import Count, Q
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import GeoPoint, Message
from .serializers import (
    GeoPointDetailSerializer,
    GeoPointSerializer,
    MessageSerializer,
    NearbySearchQuerySerializer,
)


class GeoPointViewSet(viewsets.ModelViewSet):
    """
    CRUD по геометкам.

    /api/points/            -> list, create
    /api/points/{id}/       -> retrieve (с вложенными сообщениями), update, delete
    /api/points/{id}/messages/  -> GET (список сообщений метки) / POST (добавить сообщение)
    """

    queryset = GeoPoint.objects.annotate(messages_count=Count("messages"))
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "name"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return GeoPointDetailSerializer
        return GeoPointSerializer

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=user)

    @action(detail=True, methods=["get", "post"], url_path="messages")
    def messages(self, request, pk=None):
        point = self.get_object()

        if request.method == "POST":
            serializer = MessageSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            author = request.user if request.user.is_authenticated else None
            serializer.save(point=point, author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        messages_qs = point.messages.select_related("author").order_by("-created_at")
        page = self.paginate_queryset(messages_qs)
        serializer = MessageSerializer(page if page is not None else messages_qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """
    Плоский доступ к сообщениям, полезен для модерации/поиска без
    привязки к конкретному URL метки. Метка передаётся полем `point`.

    /api/messages/          -> list (?point=<id> для фильтрации), create
    /api/messages/{id}/     -> retrieve, update, delete
    """

    queryset = Message.objects.select_related("author", "point").all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    search_fields = ["text"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        point_id = self.request.query_params.get("point")
        if point_id:
            qs = qs.filter(point_id=point_id)
        return qs

    def perform_create(self, serializer):
        if "point" not in serializer.validated_data:
            raise serializers.ValidationError(
                {"point": "Обязательное поле при создании через /api/messages/."}
            )
        author = self.request.user if self.request.user.is_authenticated else None
        serializer.save(author=author)


class NearbySearchView(APIView):
    """
    Поиск контента (меток и сообщений) в заданном радиусе от пользователя.

    GET /api/search/?lat=55.751244&lon=37.618423&radius_m=2000&q=кофе&limit=50

    Параметры:
      lat, lon   — координаты пользователя (обязательны)
      radius_m   — радиус поиска в метрах (по умолчанию settings.GEO_SEARCH_DEFAULT_RADIUS_M)
      q          — необязательная текстовая фильтрация по названию/описанию метки и тексту сообщений
      limit      — максимум объектов в каждом из списков (по умолчанию 50, максимум 200)

    Запрос использует geography-поле и индекс GiST, поэтому фильтрация
    `location__distance_lte` эффективно выполняется средствами PostGIS
    (ST_DWithin), а не постобработкой в Python.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query_serializer = NearbySearchQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        data = query_serializer.validated_data

        lat = data["lat"]
        lon = data["lon"]
        radius_m = data.get("radius_m", settings.GEO_SEARCH_DEFAULT_RADIUS_M)
        max_radius = settings.GEO_SEARCH_MAX_RADIUS_M
        if radius_m > max_radius:
            return Response(
                {"radius_m": f"Максимальный допустимый радиус — {max_radius} м."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        limit = data.get("limit", 50)
        q = data.get("q", "").strip()

        user_location = Point(lon, lat, srid=4326)
        distance_filter = {"location__distance_lte": (user_location, D(m=radius_m))}

        points_qs = (
            GeoPoint.objects.filter(**distance_filter)
            .annotate(distance=Distance("location", user_location))
            .annotate(messages_count=Count("messages"))
            .order_by("distance")
        )

        message_distance_filter = {
            "point__location__distance_lte": (user_location, D(m=radius_m))
        }
        messages_qs = (
            Message.objects.filter(**message_distance_filter)
            .select_related("author", "point")
            .annotate(distance=Distance("point__location", user_location))
            .order_by("distance")
        )

        if q:
            points_qs = points_qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
            messages_qs = messages_qs.filter(text__icontains=q)

        points_qs = points_qs[:limit]
        messages_qs = messages_qs[:limit]

        return Response(
            {
                "query": {
                    "lat": lat,
                    "lon": lon,
                    "radius_m": radius_m,
                    "q": q or None,
                },
                "points": GeoPointSerializer(points_qs, many=True).data,
                "messages": MessageSerializer(messages_qs, many=True).data,
            }
        )
