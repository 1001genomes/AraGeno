#!/bin/sh
set -e

if [ "$1" = 'manage.py' ]; then
  echo "Starting server..."
  python manage.py migrate                  # Apply database migrations
  python manage.py collectstatic --noinput  # Collect static files
  python manage.py loaddata initial
  exec gunicorn AraGenoSite.wsgi:application \
    --name AraGeno \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --threads 4 \
    --worker-class=gthread \
    --timeout 120 \
    --log-level=info \
    #--log-file=/srv/logs/gunicorn.log \
    #--access-logfile=/srv/logs/gunicorn-access.log \
    --worker-tmp-dir /dev/shm
fi
echo "Runing command..."
exec "$@"
