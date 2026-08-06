from rest_framework import serializers

from .models import ContactMessage


class ContactMessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["id", "name", "email", "message_type", "message", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_message(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Le message ne peut pas être vide.")
        return value


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["id", "name", "email", "message_type", "message", "is_read", "created_at"]
        read_only_fields = ["id", "name", "email", "message_type", "message", "created_at"]
