from rest_framework.routers import DefaultRouter

from . import views

app_name = "tools"

router = DefaultRouter()
router.register("", views.EcosystemToolViewSet, basename="tool")

urlpatterns = router.urls
