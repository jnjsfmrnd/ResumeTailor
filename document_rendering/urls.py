"""URL patterns for the export service (D2)."""

from django.urls import path

from . import views

app_name = "document_rendering"

urlpatterns = [
    path(
        "<uuid:session_id>/export/resume/",
        views.export_resume,
        name="export-resume",
    ),
    path(
        "<uuid:session_id>/export/cover-letter/",
        views.export_cover_letter,
        name="export-cover-letter",
    ),
]
