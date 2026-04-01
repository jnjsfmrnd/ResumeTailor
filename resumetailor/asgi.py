"""ASGI config for ResumeTailor."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "resumetailor.settings.base")

application = get_asgi_application()
