import logging

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.permissions import IsManager

from .models import LoginEvent, User
from .serializers import (
    AvatarUploadSerializer,
    GoogleAuthSerializer,
    LoginEventSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
)

security_logger = logging.getLogger("apps.accounts")


def _client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _tokens_for_user(user: User, login_event: LoginEvent | None = None) -> dict:
    refresh = RefreshToken.for_user(user)
    if login_event is not None:
        # Permet à LogoutView de retrouver l'événement de connexion à clore
        # (date de déconnexion) sans dépendre d'une déduction heuristique.
        refresh["login_event_id"] = login_event.id
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class RegisterView(generics.CreateAPIView):
    """POST /api/accounts/register/ — inscription (AllowAny). Reprend les
    champs de SignupForm.tsx côté frontend."""

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        security_logger.info("Nouvelle inscription : %s", user.email)
        tokens = _tokens_for_user(user)
        return Response({"user": UserSerializer(user).data, **tokens}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """POST /api/accounts/login/ — connexion (AllowAny). Chaque tentative,
    réussie ou non, est journalisée dans LoginEvent pour l'historique des
    connexions consulté depuis l'espace gestionnaire du frontend."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        password = serializer.validated_data["password"]

        user = authenticate(request, username=email, password=password)

        login_event = LoginEvent.objects.create(
            user=user or None,
            email_attempted=email,
            success=bool(user),
            ip_address=_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
        )

        if not user:
            security_logger.warning("Échec de connexion pour %s", email)
            return Response({"detail": "Email ou mot de passe incorrect."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"detail": "Ce compte est désactivé."}, status=status.HTTP_403_FORBIDDEN)

        security_logger.info("Connexion réussie : %s", email)
        tokens = _tokens_for_user(user, login_event=login_event)
        return Response({"user": UserSerializer(user).data, **tokens})


class LogoutView(APIView):
    """POST /api/accounts/logout/ — révoque le refresh token fourni et
    referme l'événement de connexion associé (date de déconnexion) pour
    l'historique des connexions consulté depuis l'espace gestionnaire."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Le champ 'refresh' est requis."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            login_event_id = token.get("login_event_id")
            token.blacklist()
        except Exception:
            return Response({"detail": "Jeton invalide ou déjà révoqué."}, status=status.HTTP_400_BAD_REQUEST)

        if login_event_id is not None:
            LoginEvent.objects.filter(id=login_event_id, logout_at__isnull=True).update(logout_at=timezone.now())

        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/accounts/me/ — profil de l'utilisateur connecté."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self) -> User:
        return self.request.user


class AvatarUploadView(APIView):
    """POST /api/accounts/me/avatar/ — dépose ou remplace la photo de profil
    du compte connecté. DELETE la retire (retour aux initiales côté
    frontend)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = AvatarUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if user.avatar:
            user.avatar.delete(save=False)
        user.avatar = serializer.validated_data["avatar"]
        user.save(update_fields=["avatar"])
        return Response(UserSerializer(user, context={"request": request}).data)

    def delete(self, request, *args, **kwargs):
        user = request.user
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save(update_fields=["avatar"])
        return Response(UserSerializer(user, context={"request": request}).data)


class PasswordChangeView(APIView):
    """POST /api/accounts/me/password/ — modification du mot de passe depuis
    la page profil du gestionnaire (exige le mot de passe actuel)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data["current_password"]):
            return Response({"detail": "Mot de passe actuel incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        security_logger.info("Mot de passe modifié depuis le profil : %s", user.email)
        return Response({"detail": "Mot de passe mis à jour."})


class PasswordResetRequestView(APIView):
    """POST /api/accounts/password-reset/ — correspond au lien « Mot de
    passe oublié ? » du frontend. La réponse est identique que l'email
    corresponde ou non à un compte, pour ne pas permettre l'énumération de
    comptes existants."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()

        user = User.objects.filter(email__iexact=email).first()
        if user:
            token_generator = PasswordResetTokenGenerator()
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = token_generator.make_token(user)
            reset_url = f"{settings.FRONTEND_BASE_URL}/reinitialiser-mot-de-passe?uid={uid}&token={token}"
            send_mail(
                subject="Réinitialisation de votre mot de passe — Flores Gong Nota",
                message=(
                    "Vous avez demandé la réinitialisation de votre mot de passe.\n\n"
                    f"Cliquez sur ce lien pour en choisir un nouveau : {reset_url}\n\n"
                    "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
            security_logger.info("Demande de réinitialisation de mot de passe : %s", email)

        return Response({"detail": "Si un compte existe pour cette adresse, un email a été envoyé."})


class PasswordResetConfirmView(APIView):
    """POST /api/accounts/password-reset/confirm/ — dépose le nouveau mot
    de passe à partir du lien reçu par email."""

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            uid = force_str(urlsafe_base64_decode(data["uid"]))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response({"detail": "Lien de réinitialisation invalide."}, status=status.HTTP_400_BAD_REQUEST)

        if not PasswordResetTokenGenerator().check_token(user, data["token"]):
            return Response(
                {"detail": "Lien de réinitialisation invalide ou expiré."}, status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(data["new_password"])
        user.save(update_fields=["password"])
        security_logger.info("Mot de passe réinitialisé : %s", user.email)
        return Response({"detail": "Mot de passe mis à jour."})


class GoogleAuthView(APIView):
    """POST /api/accounts/google/ — bouton « Continuer avec Google » du
    frontend. Répond 501 tant que GOOGLE_OAUTH_CLIENT_ID n'est pas configuré
    plutôt que d'échouer de façon opaque : voir docs/api/accounts.md."""

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        if not settings.GOOGLE_OAUTH_CLIENT_ID:
            return Response(
                {"detail": "Connexion Google non configurée sur ce serveur (GOOGLE_OAUTH_CLIENT_ID manquant)."},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token as google_id_token
        except ImportError:
            return Response(
                {"detail": "La dépendance 'google-auth' n'est pas installée sur ce serveur."},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        try:
            payload = google_id_token.verify_oauth2_token(
                serializer.validated_data["id_token"],
                google_requests.Request(),
                settings.GOOGLE_OAUTH_CLIENT_ID,
            )
        except ValueError:
            return Response({"detail": "Jeton Google invalide."}, status=status.HTTP_401_UNAUTHORIZED)

        email = payload["email"].strip().lower()
        full_name = payload.get("name", "")

        user, created = User.objects.get_or_create(
            email=email, defaults={"full_name": full_name, "role": User.Role.USER}
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])

        login_event = LoginEvent.objects.create(
            user=user,
            email_attempted=email,
            success=True,
            ip_address=_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
        )
        security_logger.info("Connexion Google : %s (nouveau compte : %s)", email, created)

        tokens = _tokens_for_user(user, login_event=login_event)
        return Response({"user": UserSerializer(user).data, "created": created, **tokens})


class RegisteredAccountsCountView(APIView):
    """GET /api/accounts/count/ — nombre total de comptes utilisateurs
    (hors gestionnaires), pour la statistique publique « Comptes créés sur
    le site » du site vitrine (section Stats.tsx). Ne renvoie qu'un
    total agrégé, aucune donnée personnelle — safe en accès public."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        count = User.objects.filter(role=User.Role.USER).count()
        return Response({"count": count})


class RegistrationHistoryView(generics.ListAPIView):
    """GET /api/accounts/registrations/ — historique des inscriptions,
    réservé aux gestionnaires (section « Inscriptions » du frontend)."""

    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer
    permission_classes = [IsManager]


class RegistrationDetailView(generics.RetrieveDestroyAPIView):
    """GET /api/accounts/registrations/{id}/ — toutes les informations
    enregistrées pour un compte (jamais le mot de passe, déjà exclu de
    UserSerializer), pour le bouton « voir les informations » de la section
    Inscriptions. DELETE — supprime le compte ; volontairement limité aux
    comptes « utilisateur » pour ne jamais permettre de supprimer un compte
    gestionnaire (y compris le sien) depuis cet écran."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsManager]

    def perform_destroy(self, instance: User) -> None:
        if instance.role != User.Role.USER:
            raise PermissionDenied("Seuls les comptes utilisateurs peuvent être supprimés depuis cet écran.")
        instance.delete()


class LoginHistoryView(generics.ListAPIView):
    """GET /api/accounts/login-events/ — historique des connexions, réservé
    aux gestionnaires (section « Connexions » du frontend)."""

    queryset = LoginEvent.objects.select_related("user").all()
    serializer_class = LoginEventSerializer
    permission_classes = [IsManager]
