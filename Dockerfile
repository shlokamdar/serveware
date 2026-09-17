# syntax=docker/dockerfile:1

# --- Builder stage: resolve and install Python dependencies only ---
FROM python:3.12-slim AS builder

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# --- Runtime stage: slim image with just the venv + app code ---
FROM python:3.12-slim

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=serveware.settings

RUN groupadd -r serveware && useradd -r -g serveware -d /app serveware

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY serveware/ ./serveware/

WORKDIR /app/serveware

# Bakes static assets into the image at build time. DJANGO_SECRET_KEY/
# DEBUG/ALLOWED_HOSTS use the safe local-dev defaults from settings.py
# here since collectstatic never touches the database or real secrets;
# real values are supplied as env vars when the container runs.
RUN python manage.py collectstatic --noinput

RUN chown -R serveware:serveware /app
USER serveware

EXPOSE 8000

CMD ["gunicorn", "serveware.wsgi:application", "--bind", "0.0.0.0:8000"]
