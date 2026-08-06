import logging

from django.conf import settings
from django.core.mail import send_mail
from rest_framework import permissions, viewsets

from apps.common.permissions import IsManager

from .models import ContactMessage
from .serializers import ContactMessageCreateSerializer, ContactMessageSerializer

logger = logging.getLogger(__name__)


class ContactMessageViewSet(viewsets.ModelViewSet):
    """/api/contact/messages/

    POST est ouvert à tous (l'espace de contact de la FAQ ne demande pas de
    compte) ; le reste (liste, marquage comme lu) est réservé aux
    gestionnaires. Miroir de la section contact de components/Faq.tsx."""

    queryset = ContactMessage.objects.all()
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return ContactMessageCreateSerializer
        return ContactMessageSerializer

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        return [IsManager()]

    def perform_create(self, serializer):
        message = serializer.save()
        send_mail(
            subject=f"[Flores Gong Nota] {message.get_message_type_display()}",
            message=f"{message.message}\n\n— {message.name or 'Un visiteur du site'} ({message.email or 'email non renseigné'})",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.CONTACT_NOTIFICATION_EMAIL],
            fail_silently=True,
        )
        logger.info("Nouveau message de contact (%s)", message.message_type)
