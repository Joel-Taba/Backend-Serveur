import os

from django.urls import reverse
from rest_framework import serializers

from .models import Category, Document
from .slugs import slugify
from .validators import validate_document_extension, validate_document_size


class CategorySerializer(serializers.ModelSerializer):
    """Un dossier — `path` reprend le principe du tableau de segments
    (`id: string[]`) utilisé côté frontend pour construire les URLs."""

    path = serializers.SerializerMethodField()
    document_count = serializers.IntegerField(source="documents.count", read_only=True)
    subcategory_count = serializers.IntegerField(source="children.count", read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent", "path", "document_count", "subcategory_count", "created_at"]
        read_only_fields = ["id", "slug", "path", "document_count", "subcategory_count", "created_at"]

    def get_path(self, obj: Category) -> list[str]:
        return obj.get_path_segments()

    def validate(self, attrs: dict) -> dict:
        name = attrs.get("name", getattr(self.instance, "name", None))
        parent = attrs.get("parent", getattr(self.instance, "parent", None))
        if not name:
            return attrs

        slug = slugify(name) or "dossier"
        qs = Category.objects.filter(parent=parent, slug=slug)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Un dossier porte déjà ce nom à cet emplacement.")

        if self.instance and parent:
            if parent.pk == self.instance.pk:
                raise serializers.ValidationError("Un dossier ne peut pas être son propre parent.")
            if parent.is_descendant_of(self.instance):
                raise serializers.ValidationError("Impossible de déplacer un dossier dans l'un de ses sous-dossiers.")

        return attrs


class DocumentSerializer(serializers.ModelSerializer):
    """Métadonnées d'un document. `file` n'est accepté qu'à la création
    (upload) — la lecture se fait via `download_url`, jamais en exposant le
    chemin disque, comme côté frontend (/api/file/[...id])."""

    file = serializers.FileField(
        write_only=True, required=True, validators=[validate_document_extension, validate_document_size]
    )
    path = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    uploaded_by_email = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "slug",
            "category",
            "doc_type",
            "size",
            "file",
            "path",
            "download_url",
            "thumbnail_url",
            "uploaded_by_email",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "doc_type",
            "size",
            "path",
            "download_url",
            "thumbnail_url",
            "uploaded_by_email",
            "created_at",
        ]

    def get_path(self, obj: Document) -> list[str]:
        return obj.get_path_segments()

    def _absolute_url(self, view_name: str, pk) -> str:
        request = self.context.get("request")
        url = reverse(view_name, args=[pk])
        return request.build_absolute_uri(url) if request else url

    def get_download_url(self, obj: Document) -> str:
        return self._absolute_url("library:document-download", obj.pk)

    def get_thumbnail_url(self, obj: Document) -> str:
        return self._absolute_url("library:document-thumbnail", obj.pk)

    def get_uploaded_by_email(self, obj: Document) -> str | None:
        return obj.uploaded_by.email if obj.uploaded_by_id else None

    def validate(self, attrs: dict) -> dict:
        title = attrs.get("title")
        file = attrs.get("file")
        if not title and file:
            attrs["title"] = os.path.splitext(file.name)[0].replace("_", " ").replace("-", " ").strip().title()

        title = attrs.get("title", getattr(self.instance, "title", ""))
        category = attrs.get("category", getattr(self.instance, "category", None))
        slug = slugify(title) or "document"
        qs = Document.objects.filter(category=category, slug=slug)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Un document porte déjà ce nom dans ce dossier.")

        return attrs

    def create(self, validated_data: dict) -> Document:
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["uploaded_by"] = request.user
        return super().create(validated_data)


# --- Représentation en arbre, miroir de CatalogNode côté frontend ----------


class DocumentTreeSerializer(serializers.ModelSerializer):
    kind = serializers.SerializerMethodField()
    path = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ["kind", "id", "title", "doc_type", "size", "path", "download_url", "thumbnail_url"]

    def get_kind(self, obj: Document) -> str:
        return "document"

    def get_path(self, obj: Document) -> list[str]:
        return obj.get_path_segments()

    def _absolute_url(self, view_name: str, pk) -> str:
        request = self.context.get("request")
        url = reverse(view_name, args=[pk])
        return request.build_absolute_uri(url) if request else url

    def get_download_url(self, obj: Document) -> str:
        return self._absolute_url("library:document-download", obj.pk)

    def get_thumbnail_url(self, obj: Document) -> str:
        return self._absolute_url("library:document-thumbnail", obj.pk)


class CategoryTreeSerializer(serializers.ModelSerializer):
    kind = serializers.SerializerMethodField()
    path = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["kind", "id", "name", "path", "children"]

    def get_kind(self, obj: Category) -> str:
        return "folder"

    def get_path(self, obj: Category) -> list[str]:
        return obj.get_path_segments()

    def get_children(self, obj: Category) -> list[dict]:
        sub_categories = obj.children.all().order_by("name")
        sub_documents = obj.documents.all().order_by("title")
        context = self.context
        return [
            *CategoryTreeSerializer(sub_categories, many=True, context=context).data,
            *DocumentTreeSerializer(sub_documents, many=True, context=context).data,
        ]
