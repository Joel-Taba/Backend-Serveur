import os

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel

from .slugs import slugify
from .validators import validate_document_extension, validate_document_size


def document_upload_path(instance: "Document", filename: str) -> str:
    """Reflète l'arborescence de catégories sur le disque, comme le dossier
    documents/ du frontend (documents/primaire/mon-fichier.pdf, etc)."""
    segments = instance.category.get_path_segments() if instance.category_id else []
    return os.path.join("documents", *segments, filename)


class Category(TimeStampedModel):
    """Un dossier de la bibliothèque — peut être imbriqué à volonté
    (primaire/, primaire/sous-dossier/, …), comme les dossiers créés depuis
    l'espace gestionnaire du frontend."""

    name = models.CharField("nom", max_length=150)
    slug = models.SlugField("slug", max_length=160, blank=True)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children", verbose_name="dossier parent"
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "catégorie"
        verbose_name_plural = "catégories"
        constraints = [
            models.UniqueConstraint(fields=["parent", "slug"], name="unique_category_slug_per_parent"),
        ]

    def __str__(self) -> str:
        return " / ".join(self.get_path_segments())

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name) or "dossier"
        super().save(*args, **kwargs)

    def get_path_segments(self) -> list[str]:
        """Slugs depuis la racine jusqu'à cette catégorie incluse — même
        principe que le tableau `id: string[]` utilisé côté frontend."""
        segments: list[str] = []
        node: Category | None = self
        while node is not None:
            segments.insert(0, node.slug)
            node = node.parent
        return segments

    def is_descendant_of(self, other: "Category") -> bool:
        """Utilisé pour empêcher de déplacer un dossier dans l'un de ses
        propres sous-dossiers (cycle dans l'arborescence)."""
        node = self.parent
        while node is not None:
            if node.pk == other.pk:
                return True
            node = node.parent
        return False


class Document(TimeStampedModel):
    class DocType(models.TextChoices):
        PDF = "pdf", "PDF"
        EPUB = "epub", "EPUB"
        IMAGE = "image", "Image"
        JSON = "json", "JSON"
        VIDEO = "video", "Vidéo"

    title = models.CharField("titre", max_length=255)
    slug = models.SlugField("slug", max_length=270, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, null=True, blank=True, related_name="documents", verbose_name="dossier"
    )
    file = models.FileField(
        "fichier", upload_to=document_upload_path, validators=[validate_document_extension, validate_document_size]
    )
    doc_type = models.CharField("type", max_length=10, choices=DocType.choices, editable=False, blank=True)
    size = models.PositiveBigIntegerField("taille (octets)", editable=False, default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
        verbose_name="ajouté par",
    )

    class Meta:
        ordering = ["title"]
        verbose_name = "document"
        verbose_name_plural = "documents"
        constraints = [
            models.UniqueConstraint(fields=["category", "slug"], name="unique_document_slug_per_category"),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title) or "document"
        ext = os.path.splitext(self.file.name)[1].lower() if self.file else ""
        self.doc_type = settings.ALLOWED_DOCUMENT_EXTENSIONS.get(ext, "")
        if self.file:
            self.size = self.file.size
        super().save(*args, **kwargs)

    def get_path_segments(self) -> list[str]:
        base = self.category.get_path_segments() if self.category_id else []
        return base + [self.slug]


class DocumentRating(TimeStampedModel):
    """Note (1 à 5 étoiles) laissée par un utilisateur sur un document —
    proposée à la sortie du lecteur (voir ReaderShell.tsx côté frontend),
    réservée aux comptes non-gestionnaires. Une seule note par personne et
    par document : une nouvelle notation remplace la précédente plutôt que
    d'en créer une autre (contrainte d'unicité ci-dessous)."""

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="ratings", verbose_name="document")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="document_ratings", verbose_name="utilisateur"
    )
    stars = models.PositiveSmallIntegerField(
        "note", validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "note de document"
        verbose_name_plural = "notes de documents"
        constraints = [
            models.UniqueConstraint(fields=["document", "user"], name="unique_rating_per_user_and_document"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} → {self.document_id} : {self.stars}★"
