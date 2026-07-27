from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("geo.urls")),
    path("api-auth/", include("rest_framework.urls")),  # логин/логаут для browsable API
]
