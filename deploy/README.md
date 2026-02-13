# Deploy (Nginx + Gunicorn + Postgres)

Paths below assume the app lives at `/var/www/imaestry_server`.
Adjust if your server uses another path or service name.

## One-time server setup

```bash
# Create app dir and clone
sudo mkdir -p /var/www/imaestry_server
sudo chown -R $USER:www-data /var/www/imaestry_server
cd /var/www/imaestry_server

git clone https://github.com/danielperitofd/imaestry_server .
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip wheel
pip install -r requirements.txt

# Environment
cp .env.example .env  # then edit values

# Django prep
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Systemd unit
sudo cp deploy/systemd/gunicorn-imaestry.service /etc/systemd/system/gunicorn-imaestry.service
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn-imaestry
sudo systemctl status gunicorn-imaestry --no-pager -l

# Nginx site
sudo cp deploy/nginx/imaestry.conf /etc/nginx/sites-available/imaestry.conf
sudo ln -sfn /etc/nginx/sites-available/imaestry.conf /etc/nginx/sites-enabled/imaestry.conf
sudo nginx -t
sudo systemctl reload nginx
```

## Routine deploys

```bash
sudo bash scripts/deploy.sh
```

## Logs and troubleshooting

```bash
# App logs
sudo journalctl -u gunicorn-imaestry -n 200 -xe

# Nginx logs
sudo tail -n 200 /var/log/nginx/error.log
sudo tail -n 200 /var/log/nginx/access.log

# Service health
sudo systemctl status gunicorn-imaestry --no-pager -l
sudo nginx -t
```
