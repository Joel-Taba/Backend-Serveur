import re

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Même algorithme que slugify() côté frontend (lib/catalog.ts) :
    minuscules, tout ce qui n'est pas alphanumérique devient un tiret,
    tirets de bord retirés. Les segments d'URL (id: string[] côté
    frontend, `path` ici) doivent être identiques des deux côtés — en
    particulier, Django's slugify() garde les underscores (comportement
    différent), d'où cette version dédiée plutôt que
    django.utils.text.slugify."""
    return _NON_ALNUM.sub("-", value.lower()).strip("-")
