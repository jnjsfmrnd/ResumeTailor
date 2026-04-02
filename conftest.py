def pytest_configure():
    import os
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "resumetailor.settings.test")
