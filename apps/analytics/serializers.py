from rest_framework import serializers

from .models import Visit


class VisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visit
        fields = ["id", "path", "created_at"]
        read_only_fields = fields


class TrackVisitSerializer(serializers.Serializer):
    """Corps de requête accepté par POST /api/analytics/track-visit/."""

    path = serializers.CharField(required=False, allow_blank=True, default="")


class DailyCountSerializer(serializers.Serializer):
    date = serializers.DateField()
    count = serializers.IntegerField()


class BreakdownEntrySerializer(serializers.Serializer):
    label = serializers.CharField()
    value = serializers.IntegerField()


class DashboardSerializer(serializers.Serializer):
    """Reprend exactement la forme de `DashboardData` côté frontend
    (components/admin/DashboardOverview.tsx), pour que le branchement futur
    du frontend sur cette API soit une simple substitution de source de
    données, sans changement de composant."""

    document_count = serializers.IntegerField()
    folder_count = serializers.IntegerField()
    today_visits = serializers.IntegerField()
    total_visits = serializers.IntegerField()
    visits = DailyCountSerializer(many=True)
    category_breakdown = BreakdownEntrySerializer(many=True)
    format_breakdown = BreakdownEntrySerializer(many=True)
