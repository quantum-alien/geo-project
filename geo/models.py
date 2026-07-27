from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models


class GeoPoint(models.Model):
    """
    Географическая метка на карте.

    Поле `location` хранится как geography(Point, 4326) — это позволяет
    PostGIS считать расстояния в метрах "из коробки", без ручного
    приведения единиц измерения, и использовать GiST-индекс для быстрого
    поиска ближайших объектов.
    """

    name = models.CharField("название", max_length=255)
    description = models.TextField("описание", blank=True, default="")
    location = gis_models.PointField(
        "координаты",
        geography=True,
        srid=4326,
        spatial_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="автор",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="points",
    )
    created_at = models.DateTimeField("создано", auto_now_add=True)
    updated_at = models.DateTimeField("обновлено", auto_now=True)

    class Meta:
        verbose_name = "геометка"
        verbose_name_plural = "геометки"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.location.y:.5f}, {self.location.x:.5f})"


class Message(models.Model):
    """Сообщение, привязанное к конкретной геометке."""

    point = models.ForeignKey(
        GeoPoint,
        verbose_name="метка",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="автор",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="messages",
    )
    text = models.TextField("текст")
    created_at = models.DateTimeField("создано", auto_now_add=True)

    class Meta:
        verbose_name = "сообщение"
        verbose_name_plural = "сообщения"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Message #{self.pk} @ {self.point_id}"
