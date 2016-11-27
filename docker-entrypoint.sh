#!/bin/bash
python manage.py migrate                  # Apply database migrations
python manage.py collectstatic --noinput  # Collect static files
NUM_WORKERS=3
TIMEOUT=120

# Prepare log files and start outputting logs to stdout
mkdir -p /srv/logs
touch /srv/logs/gunicorn.log
touch /srv/logs/access.log
tail -n 0 -f /srv/logs/*.log &

# Start Gunicorn processes
echo Starting Gunicorn.
exec gunicorn AraGenoSite.wsgi:application \
    --name AraGeno \
    --bind 0.0.0.0:8000 \
    --workers $NUM_WORKERS \
    --timeout $TIMEOUT
    --log-level=info \
    --log-file=/srv/logs/gunicorn.log \
    --access-logfile=/srv/logs/access.log \
    "$@"
