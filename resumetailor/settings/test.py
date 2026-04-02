"""Test settings — overrides base to use in-memory SQLite, no external services."""

from .base import *  # noqa: F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable Celery tasks running synchronously in tests
CELERY_TASK_ALWAYS_EAGER = True

# Use local file storage for tests
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
