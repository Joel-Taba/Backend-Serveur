from django.db import models

from apps.common.models import TimeStampedModel


class EcosystemTool(TimeStampedModel):
    """Une entrée de la vitrine « Nos Outils » côté frontend
    (lib/tools.ts / onglet Nos Outils de Catalogue.tsx) — rendue
    dynamique et administrable depuis cette API."""

    class Status(models.TextChoices):
        AVAILABLE = "disponible", "Disponible"
        IN_DEVELOPMENT = "en-developpement", "En développement"

    name = models.CharField("nom", max_length=150)
    description = models.TextField("description")
    status = models.CharField("statut", max_length=20, choices=Status.choices, default=Status.IN_DEVELOPMENT)
    url = models.URLField("lien", blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "outil"
        verbose_name_plural = "outils de l'écosystème"

    def __str__(self) -> str:
        return self.name
