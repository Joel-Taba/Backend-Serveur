import mimetypes
import re

from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsManagerOrReadOnly

from .models import Category, Document
from .serializers import CategorySerializer, CategoryTreeSerializer, DocumentSerializer, DocumentTreeSerializer
from .thumbnails import get_thumbnail_path

RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")


class CategoryViewSet(viewsets.ModelViewSet):
    """/api/library/categories/ — dossiers de la bibliothèque.

    Lecture publique (comme la Bibliothèque du frontend, accessible sans
    compte) ; création/modification/suppression réservées aux gestionnaires
    (espace /admin du frontend, section « Bibliothèque »).
    """

    queryset = Category.objects.select_related("parent").all()
    serializer_class = CategorySerializer
    permission_classes = [IsManagerOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        parent_param = self.request.query_params.get("parent")
        if parent_param is not None:
            qs = qs.filter(parent_id=parent_param or None)
        return qs


class DocumentViewSet(viewsets.ModelViewSet):
    """/api/library/documents/ — documents de la bibliothèque.

    `?q=` filtre par titre OU par nom d'un dossier ancêtre (le « genre » de
    la recherche côté frontend). `?category=<id>` filtre par dossier direct
    (`?category=` sans valeur cible la racine, documents sans dossier).
    """

    queryset = Document.objects.select_related("category", "uploaded_by").all()
    serializer_class = DocumentSerializer
    permission_classes = [IsManagerOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()

        category_param = self.request.query_params.get("category")
        if category_param is not None:
            qs = qs.filter(category_id=category_param or None)

        query = self.request.query_params.get("q", "").strip().lower()
        if query:
            matching_ids = [doc.id for doc in qs if self._matches(doc, query)]
            qs = qs.filter(id__in=matching_ids)

        return qs

    @staticmethod
    def _matches(document: Document, query: str) -> bool:
        if query in document.title.lower():
            return True
        node = document.category
        while node is not None:
            if query in node.name.lower():
                return True
            node = node.parent
        return False


class LibraryTreeView(APIView):
    """GET /api/library/tree/ — arborescence complète (dossiers + documents),
    miroir direct de `getCatalogTree()` côté frontend : chaque nœud porte un
    champ `kind` ("folder" | "document")."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        root_categories = Category.objects.filter(parent__isnull=True).order_by("name")
        root_documents = Document.objects.filter(category__isnull=True).order_by("title")
        context = {"request": request}
        data = [
            *CategoryTreeSerializer(root_categories, many=True, context=context).data,
            *DocumentTreeSerializer(root_documents, many=True, context=context).data,
        ]
        return Response({"tree": data})


class DocumentResolveView(APIView):
    """GET /api/library/resolve/<chemin>/ — résout un document à partir de
    son chemin de segments (ex: primaire/algorithme-quantique), sans avoir à
    télécharger tout l'arbre. Miroir de getDocumentWithPath() côté
    frontend : c'est ce qu'utilisent le lecteur et les routes de
    téléchargement/miniature pour retrouver un document à partir de son URL."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, path, *args, **kwargs):
        segments = [s for s in path.split("/") if s]
        if not segments:
            raise Http404

        parent = None
        for segment in segments[:-1]:
            parent = get_object_or_404(Category, parent=parent, slug=segment)

        document = get_object_or_404(Document, category=parent, slug=segments[-1])
        return Response(DocumentSerializer(document, context={"request": request}).data)


class DocumentDownloadView(APIView):
    """GET /api/library/documents/{id}/download/ — sert le fichier en
    streaming avec prise en charge des requêtes Range, indispensable à
    pdf.js côté frontend (miroir de app/api/file/[...id]/route.ts).

    Réservé aux comptes connectés : la consultation du contenu réel d'un
    document exige une connexion, contrairement à sa découverte dans le
    catalogue (titre, miniature, arborescence — restés publics)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        document = get_object_or_404(Document, pk=pk)
        file_field = document.file
        total = file_field.size
        content_type = mimetypes.guess_type(file_field.name)[0] or "application/octet-stream"

        base_headers = {
            "Content-Type": content_type,
            # "inline" sans nom de fichier : pas de proposition d'enregistrement.
            "Content-Disposition": "inline",
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        }

        range_header = request.headers.get("Range", "")
        match = RANGE_RE.match(range_header) if range_header else None

        if match:
            start = int(match.group(1)) if match.group(1) else 0
            end = int(match.group(2)) if match.group(2) else total - 1
            end = min(end, total - 1)

            if 0 <= start <= end < total:
                with file_field.open("rb") as handle:
                    handle.seek(start)
                    chunk = handle.read(end - start + 1)
                response = HttpResponse(chunk, status=206)
                for key, value in base_headers.items():
                    response[key] = value
                response["Content-Range"] = f"bytes {start}-{end}/{total}"
                response["Content-Length"] = str(len(chunk))
                return response

        file_field.open("rb")
        response = FileResponse(file_field, status=200)
        for key, value in base_headers.items():
            response[key] = value
        response["Content-Length"] = str(total)
        return response


class DocumentThumbnailView(APIView):
    """GET /api/library/documents/{id}/thumbnail/?page=N — miroir de
    /api/thumbnail/[...id]/route.ts côté frontend."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, pk, *args, **kwargs):
        document = get_object_or_404(Document, pk=pk)
        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except (TypeError, ValueError):
            page = 1

        thumbnail_path = get_thumbnail_path(document, page)
        if not thumbnail_path:
            return Response({"detail": "Aucune miniature disponible."}, status=status.HTTP_404_NOT_FOUND)

        try:
            handle = open(thumbnail_path, "rb")
        except OSError as exc:
            raise Http404 from exc

        response = FileResponse(handle, content_type="image/png")
        response["Cache-Control"] = "public, max-age=31536000, immutable"
        return response
