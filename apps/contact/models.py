from django.db import models

from apps.common.models import TimeStampedModel


class ContactMessage(TimeStampedModel):
    """Miroir de l'espace de contact de la FAQ côté frontend
    (components/ContactForm.tsx) : plainte, encouragement, critique,
    appréciation ou autre."""

    class MessageType(models.TextChoices):
        APPRECIATION = "appreciation", "Appréciation"
        SUGGESTION = "suggestion", "Suggestion"
        CRITIQUE = "critique", "Critique"
        PLAINTE = "plainte", "Plainte"
        AUTRE = "autre", "Autre"

    name = models.CharField("nom", max_length=150, blank=True)
    email = models.EmailField("email", blank=True)
    message_type = models.CharField(
        "type de message", max_length=20, choices=MessageType.choices, default=MessageType.AUTRE
    )
    message = models.TextField("message")
    is_read = models.BooleanField("lu", default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "message de contact"
        verbose_name_plural = "messages de contact"

    def __str__(self) -> str:
        return f"{self.get_message_type_display()} — {self.name or 'anonyme'} — {self.created_at:%Y-%m-%d}"
