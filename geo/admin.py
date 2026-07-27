from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import GeoPoint, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ["created_at"]


@admin.register(GeoPoint)
class GeoPointAdmin(GISModelAdmin):
    list_display = ["id", "name", "created_by", "created_at"]
    search_fields = ["name", "description"]
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "point", "author", "created_at"]
    search_fields = ["text"]
    list_filter = ["created_at"]
