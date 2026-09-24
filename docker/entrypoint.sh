#!/bin/sh
set -e

python manage.py migrate --noinput

if [ "$SEED_DEMO" = "true" ]; then
  python manage.py seed_demo
fi

# 1 worker keeps Prometheus metrics consistent (django-prometheus counts per process);
# threads give concurrency.
exec gunicorn serveware.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 1 --threads 4 \
  --access-logfile - --error-logfile -
