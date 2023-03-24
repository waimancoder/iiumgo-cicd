#!/bin/bash

# Apply migrations
npm install
python manage.py makemigrations
python manage.py migrate

# Start Gunicorn and Daphne
exec gunicorn mytaxi.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120 & \ 
     daphne -b 0.0.0.0 -p 9000 mytaxi.asgi:application --websocket_timeout 86400

