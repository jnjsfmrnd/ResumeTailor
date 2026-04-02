"""URL routing for the document ingestion lane."""

from django.urls import path

from .views import UploadView

app_name = "document_ingestion"

urlpatterns = [
    path("upload/", UploadView.as_view(), name="upload"),
]
