#!/bin/bash

# Run migrations
python manage.py migrate --no-input

# Create superuser (will only run once)
python manage.py create_default_superuser

# Collect static files
python manage.py collectstatic --no-input

# Start the Gunicorn server
# ¡CAMBIO AQUÍ! Ahora enlaza con 0.0.0.0:8080
gunicorn drf_p1_backend.wsgi:application --bind 0.0.0.0:8080