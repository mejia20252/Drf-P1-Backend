#!/bin/bash

# Run migrations
python manage.py migrate --no-input

# Collect static files
python manage.py collectstatic --no-input

# Start the Gunicorn server
gunicorn drf_p1_backend.wsgi:application --bind 0.0.0.0:8000