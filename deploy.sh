#!/usr/bin/env bash
# ==============================================================================
# StratzDrafter — Скрипт автоматического развертывания на Ubuntu
# ==============================================================================
set -e

echo "=== [1/5] Обновление пакетов и установка зависимостей ==="
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv nginx curl git

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Даем доступ Nginx к чтению папки static (если проект клонирован в /root)
chmod o+x "$HOME" 2>/dev/null || true
chmod -R o+r "$PROJECT_DIR/static" 2>/dev/null || true

echo "=== [2/5] Создание виртуального окружения Python ==="
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

echo "=== [3/5] Установка библиотек (Flask, Gunicorn, etc.) ==="
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt gunicorn

# Обеспечиваем наличие папки data/
mkdir -p data

echo "=== [4/5] Настройка службы systemd (автозапуск 24/7) ==="
SERVICE_FILE="/etc/systemd/system/stratzdrafter.service"
CURRENT_USER=$(whoami)

sudo bash -c "cat <<EOT > $SERVICE_FILE
[Unit]
Description=StratzDrafter Web Service
After=network.target

[Service]
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOT"

sudo systemctl daemon-reload
sudo systemctl enable stratzdrafter
sudo systemctl restart stratzdrafter

echo "=== [5/5] Настройка веб-сервера Nginx ==="
NGINX_CONF="/etc/nginx/sites-available/stratzdrafter"

sudo bash -c "cat <<EOT > $NGINX_CONF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }

    location /static/ {
        alias $PROJECT_DIR/static/;
        expires 7d;
        add_header Cache-Control \"public, max-age=604800\";
    }
}
EOT"

# Отключаем дефолтный сайт и активируем stratzdrafter
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/stratzdrafter

sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx

SERVER_IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')

echo ""
echo "=========================================================================="
echo "  ПОЗДРАВЛЯЕМ! StratzDrafter успешно установлен и запущен!"
echo "  Ваш сайт доступен по адресу: http://$SERVER_IP"
echo "=========================================================================="
echo "  Полезные команды:"
echo "    - Статус приложения: sudo systemctl status stratzdrafter"
echo "    - Перезапуск:        sudo systemctl restart stratzdrafter"
echo "    - Логи приложения:   journalctl -u stratzdrafter -f"
echo "=========================================================================="
