"""URL patterns for the review and edit workspace (D1)."""

from django.urls import path

from . import views

app_name = "resume_sessions"

urlpatterns = [
    path(
        "<uuid:session_id>/review/",
        views.review_workspace,
        name="review",
    ),
    path(
        "<uuid:session_id>/sections/<uuid:section_id>/edit/",
        views.section_edit,
        name="section-edit",
    ),
    path(
        "<uuid:session_id>/cover-letter/edit/",
        views.cover_letter_edit,
        name="cover-letter-edit",
    ),
]
