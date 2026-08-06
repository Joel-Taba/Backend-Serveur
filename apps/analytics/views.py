from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsManager
from apps.library.models import Category, Document

from .models import Visit
from .serializers import DashboardSerializer, TrackVisitSerializer

VISITS_WINDOW_DAYS = 14


def _client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _daily_visit_counts(days: int) -> list[dict]:
    since = timezone.localdate() - timedelta(days=days - 1)
    rows = (
        Visit.objects.filter(created_at__date__gte=since)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
    )
    counts_by_day = {row["day"]: row["count"] for row in rows}

    today = timezone.localdate()
    return [
        {"date": today - timedelta(days=i), "count": counts_by_day.get(today - timedelta(days=i), 0)}
        for i in range(days - 1, -1, -1)
    ]


def _documents_recursive_count(category: Category) -> int:
    """Compte les documents d'une catégorie et de tous ses sous-dossiers —
    même principe que countDocumentsInNode() côté frontend."""
    total = category.documents.count()
    for child in category.children.all():
        total += _documents_recursive_count(child)
    return total


class TrackVisitView(APIView):
    """POST /api/analytics/track-visit/ — à appeler par le frontend à
    chaque chargement de la page d'accueil (AllowAny : c'est ce endpoint
    qui remplacera l'écriture directe dans .cache/analytics.json)."""

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = TrackVisitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        Visit.objects.create(
            path=serializer.validated_data.get("path", ""),
            ip_address=_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
        )
        return Response(status=status.HTTP_201_CREATED)


class DashboardView(APIView):
    """GET /api/analytics/dashboard/ — alimente la page Dashboard de
    l'espace gestionnaire du frontend (components/admin/DashboardOverview.tsx),
    réservé aux gestionnaires."""

    permission_classes = [IsManager]

    def get(self, request, *args, **kwargs):
        today = timezone.localdate()

        format_breakdown = [
            {"label": row["doc_type"], "value": row["value"]}
            for row in Document.objects.values("doc_type").annotate(value=Count("id")).order_by("-value")
            if row["doc_type"]
        ]

        category_breakdown = [
            {"label": category.name, "value": _documents_recursive_count(category)}
            for category in Category.objects.filter(parent__isnull=True).order_by("name")
        ]

        data = {
            "document_count": Document.objects.count(),
            "folder_count": Category.objects.count(),
            "today_visits": Visit.objects.filter(created_at__date=today).count(),
            "total_visits": Visit.objects.count(),
            "visits": _daily_visit_counts(VISITS_WINDOW_DAYS),
            "category_breakdown": category_breakdown,
            "format_breakdown": format_breakdown,
        }
        return Response(DashboardSerializer(data).data)
