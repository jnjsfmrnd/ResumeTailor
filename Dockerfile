FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed by psycopg2 and PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -m compileall -q .

ENV DJANGO_SETTINGS_MODULE=resumetailor.settings.qa
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "-m", "gunicorn", "resumetailor.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--timeout", "130", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
