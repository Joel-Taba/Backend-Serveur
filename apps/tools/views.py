from rest_framework import viewsets

from apps.common.permissions import IsManagerOrReadOnly

from .models import EcosystemTool
from .serializers import EcosystemToolSerializer


class EcosystemToolViewSet(viewsets.ModelViewSet):
    """/api/tools/ — vitrine « Nos Outils ». Lecture publique, écriture
    réservée aux gestionnaires."""

    queryset = EcosystemTool.objects.all()
    serializer_class = EcosystemToolSerializer
    permission_classes = [IsManagerOrReadOnly]
