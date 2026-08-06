from rest_framework.routers import DefaultRouter

from . import views

app_name = "contact"

router = DefaultRouter()
router.register("messages", views.ContactMessageViewSet, basename="message")

urlpatterns = router.urls
