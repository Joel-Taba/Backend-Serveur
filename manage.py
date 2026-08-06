#!/usr/bin/env python
"""Utilitaire en ligne de commande de Django pour ce projet."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Impossible d'importer Django. Vérifiez qu'il est installé et "
            "disponible sur votre PYTHONPATH, et que votre environnement "
            "virtuel est activé (voir README.md)."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
