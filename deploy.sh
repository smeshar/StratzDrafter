#!/usr/bin/env bash
# ==============================================================================
# StratzDrafter — Скрипт автоматического развертывания на Ubuntu
# ==============================================================================
set -e

echo "=== [1/5] Проверка памяти (SWAP) и установка зависимостей ==="

# Создаем swap-файл 2GB, если swap отсутствует (защита от Out of Memory на бюджетных VPS)
if [ $(swapon --show | wc -l) -le 1 ]; then
    echo "Создание swap-файла 2GB..."
    sudo fallocate -l 2G /swapfile 2>/dev/null || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    if ! grep -q '/swapfile' /etc/fstab; then
        echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    fi
    echo "Swap-файл успешно подключен!"
fi

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

# Используем 1 worker с 4 потоками (threads) для экономии RAM:
# матрица героев загружается в память всего 1 раз вместо 3.
sudo tee "$SERVICE_FILE" > /dev/null <<EOT
[Unit]
Description=StratzDrafter Web Service
After=network.target

[Service]
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --workers 1 --threads 4 --bind 127.0.0.1:5000 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOT

sudo systemctl daemon-reload
sudo systemctl enable stratzdrafter
sudo systemctl restart stratzdrafter

echo "=== [5/5] Настройка веб-сервера Nginx ==="
NGINX_CONF="/etc/nginx/sites-available/stratzdrafter"

sudo tee "$NGINX_CONF" > /dev/null <<EOT
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
        add_header Cache-Control "public, max-age=604800";
    }
}
EOT

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
