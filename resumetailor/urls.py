"""URL configuration for ResumeTailor."""

from django.contrib import admin
from django.urls import path

from resumetailor.health import liveness, readiness

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", liveness, name="health-liveness"),
    path("health/ready/", readiness, name="health-readiness"),
]
