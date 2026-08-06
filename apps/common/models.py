from django.db import models


class TimeStampedModel(models.Model):
    """Ajoute created_at/updated_at à tout modèle qui en hérite — évite de
    répéter ces deux champs (et leurs options) dans chaque app."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
