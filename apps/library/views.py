import mimetypes
import re
from collections import defaultdict

from django.core.cache import cache
from django.db.models import Avg, Count
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsManagerOrReadOnly, IsRegularUser

from .models import Category, Document, DocumentRating
from .serializers import (
    CategorySerializer,
    DocumentRatingSerializer,
    DocumentSerializer,
)
from .thumbnails import get_thumbnail_path

RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")

# Arborescence complète : lue à chaque chargement de la page Bibliothèque du
# site public (LibraryTreeView, AllowAny), mais ne change qu'à chaque action
# du gestionnaire (ajout/suppression/déplacement). Mise en cache courte,
# invalidée explicitement dès qu'une catégorie ou un document est modifié
# (voir perform_create/update/destroy ci-dessous) plutôt que de se reposer
# uniquement sur le délai d'expiration — un gestionnaire qui vient d'ajouter
# un document doit le voir apparaître immédiatement, pas jusqu'à 30 s plus
# tard.
CACHE_KEY_TREE = "library:tree"
CACHE_TTL_TREE = 30


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

    def perform_create(self, serializer):
        super().perform_create(serializer)
        cache.delete(CACHE_KEY_TREE)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        cache.delete(CACHE_KEY_TREE)

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        cache.delete(CACHE_KEY_TREE)


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

    def perform_create(self, serializer):
        super().perform_create(serializer)
        cache.delete(CACHE_KEY_TREE)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        cache.delete(CACHE_KEY_TREE)

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        cache.delete(CACHE_KEY_TREE)


def _build_library_tree(request) -> list[dict]:
    """Construit l'arborescence complète en un nombre de requêtes SQL borné
    (3, quelle que soit la taille de la bibliothèque), plutôt que l'ancienne
    version — un serializer DRF récursif qui interrogeait la base à chaque
    nœud (sous-dossiers, documents, note moyenne, nombre de votes, remontée
    jusqu'à la racine pour le chemin). Mesuré à plusieurs secondes par
    requête avec seulement 110 dossiers et 949 documents, et largement
    responsable de la latence observée sous charge concurrente (voir
    deploy/benchmark.py) — un classique problème N+1, invisible sur une
    bibliothèque de test à quelques éléments. Le format JSON produit reste
    strictement identique à l'ancien (CategoryTreeSerializer et
    DocumentTreeSerializer ont été retirés) : c'est un contrat partagé avec
    le frontend (type CatalogNode, lib/catalog.ts)."""
    categories = list(Category.objects.all())
    documents = list(Document.objects.all())

    categories_by_id = {c.id: c for c in categories}

    children_by_parent: dict[int | None, list[Category]] = defaultdict(list)
    for c in categories:
        children_by_parent[c.parent_id].append(c)
    for siblings in children_by_parent.values():
        siblings.sort(key=lambda c: c.name)

    documents_by_category: dict[int | None, list[Document]] = defaultdict(list)
    for d in documents:
        documents_by_category[d.category_id].append(d)
    for siblings in documents_by_category.values():
        siblings.sort(key=lambda d: d.title)

    # Une seule requête d'agrégation pour TOUS les documents plutôt qu'un
    # aggregate() par document (voir RatingFieldsMixin, qui reste utilisé
    # ailleurs pour un objet unique — pertinent seulement hors boucle).
    rating_stats = {
        row["document_id"]: (round(row["avg"], 1) if row["avg"] is not None else None, row["count"])
        for row in DocumentRating.objects.values("document_id").annotate(avg=Avg("stars"), count=Count("id"))
    }

    path_cache: dict[int, list[str]] = {}

    def category_path(category: Category) -> list[str]:
        if category.id not in path_cache:
            segments: list[str] = []
            node: Category | None = category
            while node is not None:
                segments.insert(0, node.slug)
                node = categories_by_id.get(node.parent_id)
            path_cache[category.id] = segments
        return path_cache[category.id]

    def absolute_url(view_name: str, pk: int) -> str:
        return request.build_absolute_uri(reverse(view_name, args=[pk]))

    def document_node(document: Document) -> dict:
        parent = categories_by_id.get(document.category_id)
        path = (category_path(parent) if parent else []) + [document.slug]
        avg_rating, ratings_count = rating_stats.get(document.id, (None, 0))
        return {
            "kind": "document",
            "id": document.id,
            "title": document.title,
            "doc_type": document.doc_type,
            "size": document.size,
            "path": path,
            "download_url": absolute_url("library:document-download", document.id),
            "thumbnail_url": absolute_url("library:document-thumbnail", document.id),
            "average_rating": avg_rating,
            "ratings_count": ratings_count,
        }

    def category_node(category: Category) -> dict:
        children = [
            *(category_node(c) for c in children_by_parent.get(category.id, [])),
            *(document_node(d) for d in documents_by_category.get(category.id, [])),
        ]
        return {
            "kind": "folder",
            "id": category.id,
            "name": category.name,
            "path": category_path(category),
            "children": children,
        }

    return [
        *(category_node(c) for c in children_by_parent.get(None, [])),
        *(document_node(d) for d in documents_by_category.get(None, [])),
    ]


class LibraryTreeView(APIView):
    """GET /api/library/tree/ — arborescence complète (dossiers + documents),
    miroir direct de `getCatalogTree()` côté frontend : chaque nœud porte un
    champ `kind` ("folder" | "document"). Mise en cache courte (voir
    CACHE_KEY_TREE) : c'est la vue la plus consultée du site public, et son
    contenu ne change qu'à l'initiative du gestionnaire."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        data = cache.get(CACHE_KEY_TREE)
        if data is None:
            data = _build_library_tree(request)
            cache.set(CACHE_KEY_TREE, data, CACHE_TTL_TREE)
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


class DocumentRateView(APIView):
    """POST /api/library/documents/{id}/rate/ — dépose (ou remplace) la note
    de l'utilisateur connecté sur ce document (pop-up à la sortie du
    lecteur, voir ReaderShell.tsx). Réservé aux comptes non-gestionnaires."""

    permission_classes = [IsRegularUser]

    def post(self, request, pk, *args, **kwargs):
        document = get_object_or_404(Document, pk=pk)
        serializer = DocumentRatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        DocumentRating.objects.update_or_create(
            document=document, user=request.user, defaults={"stars": serializer.validated_data["stars"]}
        )
        return Response(DocumentSerializer(document, context={"request": request}).data)


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
