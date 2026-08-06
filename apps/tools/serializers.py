from rest_framework import serializers

from .models import EcosystemTool


class EcosystemToolSerializer(serializers.ModelSerializer):
    class Meta:
        model = EcosystemTool
        fields = ["id", "name", "description", "status", "url", "created_at"]
        read_only_fields = ["id", "created_at"]
