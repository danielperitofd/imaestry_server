#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/var/www/imaestry_server"
SERVICE="gunicorn-imaestry"

cd "$APP_DIR"

# Pull latest code
sudo -u www-data git fetch --all
sudo -u www-data git checkout develop
sudo -u www-data git pull --ff-only origin develop

# Activate venv and install deps
source .venv/bin/activate
pip install -r requirements.txt --upgrade

# Django maintenance
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py check --deploy

# Restart service
sudo systemctl daemon-reload
sudo systemctl restart "$SERVICE"
sudo systemctl status "$SERVICE" --no-pager -l

# Nginx sanity
sudo nginx -t
sudo systemctl reload nginx

echo "Deploy finished."
