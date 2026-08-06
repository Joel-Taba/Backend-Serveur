import re
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from apps.library.models import Category, Document
from apps.library.slugs import slugify


def humanize_title(stem: str) -> str:
    """Même règle que humanizeTitle() côté frontend (lib/catalog.ts) : les
    titres importés doivent rester identiques à ceux déjà affichés sur le
    site pour ne pas changer les URLs existantes."""
    title = re.sub(r"[_-]+", " ", stem).strip()
    words = [w for w in re.split(r"\s+", title) if w]
    return " ".join(w[:1].upper() + w[1:] if w == w.lower() else w for w in words)


class Command(BaseCommand):
    """Importe le dossier documents/ existant (partagé jusqu'ici avec le
    frontend, qui le lisait directement sur disque) dans la base de
    données : un dossier par Category, un fichier par Document. Idempotent
    — relancer la commande n'importe rien en double."""

    help = "Importe le dossier documents/ existant dans la base de données."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default=str(Path(settings.BASE_DIR).parent / "documents"),
            help="Dossier à importer (par défaut : documents/, frère de Backend/).",
        )

    def handle(self, *args, **options):
        source = Path(options["source"]).resolve()
        if not source.is_dir():
            self.stderr.write(self.style.ERROR(f"Dossier introuvable : {source}"))
            return

        self.created_categories = 0
        self.created_documents = 0
        self.skipped = 0

        self._import_dir(source, None)

        self.stdout.write(
            self.style.SUCCESS(
                f"Import terminé : {self.created_categories} dossier(s) et "
                f"{self.created_documents} document(s) créés, {self.skipped} fichier(s) "
                "ignoré(s) (format non pris en charge ou déjà importé)."
            )
        )

    def _import_dir(self, disk_path: Path, parent: Category | None) -> None:
        for entry in sorted(disk_path.iterdir(), key=lambda p: p.name.lower()):
            if entry.is_dir():
                slug = slugify(entry.name) or "dossier"
                category, created = Category.objects.get_or_create(
                    parent=parent, slug=slug, defaults={"name": entry.name}
                )
                if created:
                    self.created_categories += 1
                    self.stdout.write(f"Dossier créé : {' / '.join(category.get_path_segments())}")
                self._import_dir(entry, category)
            elif entry.is_file():
                self._import_file(entry, parent)

    def _import_file(self, entry: Path, parent: Category | None) -> None:
        ext = entry.suffix.lower()
        if ext not in settings.ALLOWED_DOCUMENT_EXTENSIONS:
            self.skipped += 1
            return

        slug = slugify(entry.stem) or "document"
        if Document.objects.filter(category=parent, slug=slug).exists():
            self.skipped += 1
            return

        with entry.open("rb") as file_handle:
            document = Document(title=humanize_title(entry.stem), category=parent)
            document.file.save(entry.name, File(file_handle), save=False)
            document.slug = slug
            document.save()

        self.created_documents += 1
        self.stdout.write(f"Document importé : {' / '.join(document.get_path_segments())}")
