"""URL configuration for ResumeTailor."""

from django.contrib import admin
from django.urls import include, path

from resumetailor.health import liveness, readiness

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("document_ingestion.urls")),
    path("health/", liveness, name="health-liveness"),
    path("health/ready/", readiness, name="health-readiness"),
]
