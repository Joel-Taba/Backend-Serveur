from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Document
from .thumbnails import CACHE_DIR


@receiver(post_delete, sender=Document)
def delete_document_file(sender, instance: Document, **kwargs):
    """Supprime le fichier réel et ses miniatures en cache quand un document
    disparaît — suppression directe ou en cascade depuis son dossier parent
    (Category.on_delete=CASCADE) — pour ne jamais laisser de fichier
    orphelin dans media/."""
    if instance.file:
        instance.file.delete(save=False)
    for thumbnail in CACHE_DIR.glob(f"{instance.pk}-*.png"):
        thumbnail.unlink(missing_ok=True)
