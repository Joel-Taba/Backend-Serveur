import getpass

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User


class Command(BaseCommand):
    """Crée (ou promeut) un compte gestionnaire — équivalent, côté API, de
    l'accès à /admin sur le frontend. Utile en tout début de projet, avant
    qu'aucun gestionnaire n'existe encore.

    Usage : python manage.py create_manager --email=toi@exemple.com
    """

    help = "Crée un utilisateur avec le rôle gestionnaire, ou promeut un compte existant."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--full-name", default="")

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        full_name = options["full_name"]

        user, created = User.objects.get_or_create(email=email, defaults={"full_name": full_name})

        if created:
            password = getpass.getpass("Mot de passe du nouveau gestionnaire : ")
            if not password:
                raise CommandError("Un mot de passe est requis pour un nouveau compte.")
            user.set_password(password)

        user.role = User.Role.MANAGER
        user.is_staff = True
        if full_name:
            user.full_name = full_name
        user.save()

        verb = "créé" if created else "promu"
        self.stdout.write(self.style.SUCCESS(f"Compte gestionnaire {verb} : {user.email}"))
