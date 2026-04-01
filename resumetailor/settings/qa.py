"""QA environment settings.

Extends base settings for the hosted QA environment in Azure (eastus).
Secrets are injected via environment variables backed by Azure Key Vault references.
"""

from .base import *  # noqa: F401, F403

DEBUG = False

# QA host is configured at deployment time via environment variable.
ALLOWED_HOSTS = os.environ["DJANGO_ALLOWED_HOSTS"].split()  # noqa: F405

# Storage: Azure Blob via django-storages
DEFAULT_FILE_STORAGE = "storages.backends.azure_storage.AzureStorage"
AZURE_ACCOUNT_NAME = os.environ["AZURE_STORAGE_ACCOUNT"]  # noqa: F405
AZURE_ACCOUNT_KEY = os.environ["AZURE_STORAGE_KEY"]  # noqa: F405
AZURE_CONTAINER = os.environ.get("AZURE_STORAGE_CONTAINER", "resumetailor-qa")  # noqa: F405

# Security
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
