"""URL configuration for ResumeTailor."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("document_ingestion.urls")),
]
