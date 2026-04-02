"""URL configuration for ResumeTailor."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView

from resumetailor.health import liveness, readiness

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="document_ingestion:upload", permanent=False), name="home"),
    path("admin/", admin.site.urls),
    path("", include("document_ingestion.urls")),
    path("health/", liveness, name="health-liveness"),
    path("health/ready/", readiness, name="health-readiness"),
    path("sessions/", include("resume_sessions.urls", namespace="resume_sessions")),
    path("sessions/", include("document_rendering.urls", namespace="document_rendering")),
]
