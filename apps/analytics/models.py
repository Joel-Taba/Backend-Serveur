from django.db import models


class Visit(models.Model):
    """Une visite de la plateforme — équivalent du compteur de visites
    (.cache/analytics.json) mis en place côté frontend en attendant un vrai
    système de comptes. Sert de proxy honnête à « connexions » pour le
    tableau de bord tant que le suivi par utilisateur n'existe pas."""

    path = models.CharField("chemin visité", max_length=255, blank=True)
    ip_address = models.GenericIPAddressField("adresse IP", null=True, blank=True)
    user_agent = models.CharField("user agent", max_length=300, blank=True)
    created_at = models.DateTimeField("date", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "visite"
        verbose_name_plural = "visites"
        indexes = [models.Index(fields=["created_at"])]

    def __str__(self) -> str:
        return f"{self.path or '/'} — {self.created_at:%Y-%m-%d %H:%M}"
