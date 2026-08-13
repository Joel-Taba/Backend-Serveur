from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """Utilisateur de la plateforme. Couvre le formulaire d'inscription du
    frontend (nom complet, email, mot de passe) et distingue les visiteurs
    des gestionnaires (espace /admin du frontend)."""

    class Role(models.TextChoices):
        USER = "user", "Utilisateur"
        MANAGER = "manager", "Gestionnaire"

    class Country(models.TextChoices):
        """Pays cibles de la plateforme — reprend exactement les options du
        formulaire d'inscription (SignupForm.tsx)."""

        CAMEROON = "cameroon", "Cameroun"
        CHAD = "chad", "Tchad"
        DRC = "drc", "RDC"
        SENEGAL = "senegal", "Sénégal"
        BURKINA_FASO = "burkina_faso", "Burkina Faso"
        NIGER = "niger", "Niger"
        ALL = "all", "Tous les pays"

    email = models.CharField("adresse email", max_length=254, unique=True)
    full_name = models.CharField("nom complet", max_length=150, blank=True)
    age = models.PositiveSmallIntegerField("âge", null=True, blank=True)
    country = models.CharField("pays", max_length=20, choices=Country.choices, blank=True)
    role = models.CharField("rôle", max_length=10, choices=Role.choices, default=Role.USER)
    avatar = models.ImageField("photo de profil", upload_to="avatars/", blank=True, null=True)

    is_active = models.BooleanField("actif", default=True)
    is_staff = models.BooleanField("accès admin Django", default=False)
    date_joined = models.DateTimeField("date d'inscription", default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return self.full_name or self.email

    @property
    def is_manager(self) -> bool:
        return self.role == self.Role.MANAGER or self.is_staff


class LoginEvent(models.Model):
    """Trace chaque tentative de connexion (réussie ou non), pour l'historique
    des connexions consulté depuis l'espace gestionnaire du frontend."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="login_events", null=True, blank=True
    )
    email_attempted = models.EmailField("email saisi", blank=True)
    success = models.BooleanField("réussie", default=True)
    ip_address = models.GenericIPAddressField("adresse IP", null=True, blank=True)
    user_agent = models.CharField("user agent", max_length=300, blank=True)
    created_at = models.DateTimeField("date de connexion", auto_now_add=True)
    logout_at = models.DateTimeField("date de déconnexion", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "connexion"
        verbose_name_plural = "historique des connexions"

    def __str__(self) -> str:
        who = self.user.email if self.user_id else self.email_attempted
        status = "réussie" if self.success else "échouée"
        return f"{who} — {status} — {self.created_at:%Y-%m-%d %H:%M}"
