#!/bin/sh
set -e

host="db"
port=5432
timeout=30

echo "Ожидание PostgreSQL ($host:$port)..."


while ! nc -z $host $port; do
  sleep 1
  timeout=$((timeout - 1))

  if [ $timeout -eq 0 ]; then
    echo "Таймаут подключения к PostgreSQL!"
    exit 1
  fi
done
echo "PostgreSQL готов"


echo ", выполнение миграций..."
python manage.py migrate --noinput

echo "Запуск Gunicorn"
# python manage.py runserver
gunicorn --bind 0.0.0.0:8000 config.wsgi --log-level "debug" --enable-stdio-inheritance
