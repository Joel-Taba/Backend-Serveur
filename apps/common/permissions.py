from rest_framework.permissions import SAFE_METHODS, BasePermission


def _is_manager(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "manager"))


class IsManager(BasePermission):
    """Accès réservé aux gestionnaires (rôle « manager » ou is_staff) —
    utilisé sur tout ce qui touche à l'espace gestionnaire du frontend :
    ajout de documents/dossiers, historique des inscriptions/connexions,
    tableau de bord, gestion des outils de l'écosystème."""

    message = "Cette action est réservée aux gestionnaires de la plateforme."

    def has_permission(self, request, view) -> bool:
        return _is_manager(request.user)


class IsManagerOrReadOnly(BasePermission):
    """Lecture ouverte à tous (la bibliothèque publique du frontend n'exige
    aucun compte), écriture réservée aux gestionnaires."""

    message = "Seuls les gestionnaires peuvent modifier ce contenu."

    def has_permission(self, request, view) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return _is_manager(request.user)
