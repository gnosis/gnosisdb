#!/bin/sh

set -euo pipefail

# DEBUG set in .env
if [ ${DEBUG:-False} = True ]; then
    log_level="debug"
else
    log_level="info"
fi

echo "==> Running Celery beat <=="
exec celery beat -A gnosisdb.taskapp -S django_celery_beat.schedulers:DatabaseScheduler --loglevel $log_level --pidfile=/tmp/celery_beat.pid
