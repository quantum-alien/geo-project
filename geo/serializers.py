from django.contrib.gis.geos import Point
from rest_framework import serializers

from .models import GeoPoint, Message


class MessageSerializer(serializers.ModelSerializer):
    """
    Сообщение, привязанное к геометке.

    Поле `point` необязательно здесь, так как при создании через вложенный
    маршрут /api/points/{id}/messages/ метка подставляется во вьюхе
    автоматически. При создании через плоский /api/messages/ поле `point`
    нужно передать явно — это проверяется в MessageViewSet.perform_create.
    """

    author_username = serializers.CharField(
        source="author.username", read_only=True, default=None
    )
    distance_m = serializers.SerializerMethodField()

    point = serializers.PrimaryKeyRelatedField(
        queryset=GeoPoint.objects.all(), required=False
    )

    class Meta:
        model = Message
        fields = [
            "id",
            "point",
            "text",
            "author",
            "author_username",
            "created_at",
            "distance_m",
        ]
        read_only_fields = ["id", "author", "created_at"]

    def get_distance_m(self, obj):
        distance = getattr(obj, "distance", None)
        return round(distance.m, 2) if distance is not None else None


class GeoPointSerializer(serializers.ModelSerializer):
    """
    Геометка. На вход/выход отдаём обычные широту/долготу (lat/lon),
    чтобы не заставлять клиентов API работать с GeoJSON вручную.
    """

    lat = serializers.FloatField(
        write_only=True, required=False, min_value=-90.0, max_value=90.0
    )
    lon = serializers.FloatField(
        write_only=True, required=False, min_value=-180.0, max_value=180.0
    )
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    messages_count = serializers.IntegerField(read_only=True, default=None)
    distance_m = serializers.SerializerMethodField()

    class Meta:
        model = GeoPoint
        fields = [
            "id",
            "name",
            "description",
            "latitude",
            "longitude",
            "lat",
            "lon",
            "distance_m",
            "messages_count",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def get_latitude(self, obj):
        return obj.location.y

    def get_longitude(self, obj):
        return obj.location.x

    def get_distance_m(self, obj):
        distance = getattr(obj, "distance", None)
        return round(distance.m, 2) if distance is not None else None

    def validate(self, attrs):
        is_create = self.instance is None
        has_lat = "lat" in attrs
        has_lon = "lon" in attrs
        if is_create and not (has_lat and has_lon):
            raise serializers.ValidationError(
                "Поля 'lat' и 'lon' обязательны при создании геометки."
            )
        if has_lat != has_lon:
            raise serializers.ValidationError(
                "Поля 'lat' и 'lon' должны передаваться вместе."
            )
        return attrs

    def create(self, validated_data):
        lat = validated_data.pop("lat")
        lon = validated_data.pop("lon")
        validated_data["location"] = Point(lon, lat, srid=4326)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        lat = validated_data.pop("lat", None)
        lon = validated_data.pop("lon", None)
        if lat is not None and lon is not None:
            validated_data["location"] = Point(lon, lat, srid=4326)
        return super().update(instance, validated_data)


class GeoPointDetailSerializer(GeoPointSerializer):
    """Детальное представление метки со вложенными сообщениями."""

    messages = MessageSerializer(many=True, read_only=True)

    class Meta(GeoPointSerializer.Meta):
        fields = GeoPointSerializer.Meta.fields + ["messages"]


class NearbySearchQuerySerializer(serializers.Serializer):
    """Валидация query-параметров эндпоинта поиска по радиусу."""

    lat = serializers.FloatField(min_value=-90.0, max_value=90.0)
    lon = serializers.FloatField(min_value=-180.0, max_value=180.0)
    radius_m = serializers.FloatField(min_value=1, required=False)
    q = serializers.CharField(required=False, allow_blank=True)
    limit = serializers.IntegerField(min_value=1, max_value=200, required=False)
