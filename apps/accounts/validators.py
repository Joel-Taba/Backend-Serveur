import os

from django.core.exceptions import ValidationError

ALLOWED_AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_AVATAR_SIZE_MB = 5


def validate_avatar_extension(file) -> None:
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_AVATAR_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_AVATAR_EXTENSIONS))
        raise ValidationError(f'Format "{ext or "inconnu"}" non pris en charge. Formats autorisés : {allowed}.')


def validate_avatar_size(file) -> None:
    max_bytes = MAX_AVATAR_SIZE_MB * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError(f"L'image dépasse la taille maximale autorisée ({MAX_AVATAR_SIZE_MB} Mo).")
