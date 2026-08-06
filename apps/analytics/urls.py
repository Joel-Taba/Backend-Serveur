from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("track-visit/", views.TrackVisitView.as_view(), name="track-visit"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
]
