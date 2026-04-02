"""URL configuration for ResumeTailor."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("sessions/", include("resume_sessions.urls", namespace="resume_sessions")),
    path("sessions/", include("document_rendering.urls", namespace="document_rendering")),
]
