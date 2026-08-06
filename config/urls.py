"""
Point d'entrée des URLs du projet.

Chaque app expose ses propres routes sous son préfixe : la liste ci-dessous
est volontairement une simple table de montage, sans logique — la logique
vit dans les apps.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health_check(request):
    """Sonde simple pour un load-balancer / une supervision externe."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/library/", include("apps.library.urls")),
    path("api/analytics/", include("apps.analytics.urls")),
    path("api/contact/", include("apps.contact.urls")),
    path("api/tools/", include("apps.tools.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
