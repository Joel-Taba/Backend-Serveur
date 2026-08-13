from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "library"

router = DefaultRouter()
router.register("categories", views.CategoryViewSet, basename="category")
router.register("documents", views.DocumentViewSet, basename="document")

urlpatterns = [
    path("tree/", views.LibraryTreeView.as_view(), name="tree"),
    path("resolve/<path:path>/", views.DocumentResolveView.as_view(), name="resolve"),
    path("documents/<int:pk>/download/", views.DocumentDownloadView.as_view(), name="document-download"),
    path("documents/<int:pk>/thumbnail/", views.DocumentThumbnailView.as_view(), name="document-thumbnail"),
    path("documents/<int:pk>/rate/", views.DocumentRateView.as_view(), name="document-rate"),
    path("", include(router.urls)),
]
