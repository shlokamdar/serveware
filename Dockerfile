FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY serveware/ /app/
COPY docker/entrypoint.sh /entrypoint.sh

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION} \
  SQLITE_PATH=/data/db.sqlite3 \
  MEDIA_ROOT=/app/media

# collectstatic at build time; the throwaway key is only valid for this RUN step
RUN DJANGO_SECRET_KEY=build-only-collectstatic python manage.py collectstatic --noinput \
  && useradd --create-home --uid 1000 appuser \
  && mkdir -p /data /app/media \
  && chown -R appuser:appuser /data /app/media \
  && chmod +x /entrypoint.sh

LABEL org.opencontainers.image.title="ServeWare" \
  org.opencontainers.image.source="https://github.com/shlokamdar/serveware" \
  org.opencontainers.image.version="${APP_VERSION}"
RUN python -m pip uninstall -y setuptools pip || true
USER appuser
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/healthz/', timeout=2).status == 200 else 1)"

ENTRYPOINT ["/entrypoint.sh"]
