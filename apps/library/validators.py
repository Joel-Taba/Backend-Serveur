import os

from django.conf import settings
from django.core.exceptions import ValidationError


def validate_document_extension(file) -> None:
    """N'accepte que les formats gérés par le lecteur du frontend
    (voir ALLOWED_DOCUMENT_EXTENSIONS dans config/settings/base.py, qui doit
    rester synchronisé avec lib/catalog.ts côté frontend)."""
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in settings.ALLOWED_DOCUMENT_EXTENSIONS:
        allowed = ", ".join(sorted(settings.ALLOWED_DOCUMENT_EXTENSIONS))
        raise ValidationError(f'Format "{ext or "inconnu"}" non pris en charge. Formats autorisés : {allowed}.')


def validate_document_size(file) -> None:
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError(f"Le fichier dépasse la taille maximale autorisée ({settings.MAX_UPLOAD_SIZE_MB} Mo).")
