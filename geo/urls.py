from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import GeoPointViewSet, MessageViewSet, NearbySearchView

router = DefaultRouter()
router.register("points", GeoPointViewSet, basename="geopoint")
router.register("messages", MessageViewSet, basename="message")

urlpatterns = [
    path("search/", NearbySearchView.as_view(), name="nearby-search"),
    path("", include(router.urls)),
]
