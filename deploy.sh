#!/usr/bin/env bash
# ==============================================================================
# StratzDrafter — Универсальный скрипт развертывания (Ubuntu / Debian / CentOS / Rocky / Alma)
# ==============================================================================
set -e

echo "=== [1/6] Определение ОС и установка системных зависимостей ==="

if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_ID=$ID
    OS_NAME=$PRETTY_NAME
else
    OS_ID="unknown"
    OS_NAME="Linux"
fi

echo "Обнаружена система: $OS_NAME ($OS_ID)"

if [[ "$OS_ID" == "ubuntu" || "$OS_ID" == "debian" ]]; then
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-pip python3-venv nginx curl git
elif [[ "$OS_ID" == "centos" || "$OS_ID" == "rhel" || "$OS_ID" == "almalinux" || "$OS_ID" == "rocky" ]]; then
    # Если это CentOS 8, репозитории mirror.centos.org отключены (EOL), чиним переключением на vault
    if [[ "$OS_ID" == "centos" && ("$VERSION_ID" =~ ^8 || "$VERSION" =~ ^8) ]]; then
        echo "ВНИМАНИЕ: Обнаружен CentOS 8 (EOL). Переключаем репозитории на vault.centos.org..."
        sudo sed -i 's/mirrorlist/#mirrorlist/g' /etc/yum.repos.d/CentOS-* 2>/dev/null || true
        sudo sed -i 's|#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|g' /etc/yum.repos.d/CentOS-* 2>/dev/null || true
    fi
    sudo dnf clean all || true
    sudo dnf makecache || true
    sudo dnf install -y python39 python39-pip nginx curl git policycoreutils-python-utils firewalld || sudo dnf install -y python3 python3-pip nginx curl git
    
    # Настройка SELinux (разрешить Nginx проксировать на 127.0.0.1:5000)
    if command -v setsebool &> /dev/null; then
        echo "Настройка SELinux для работы прокси Nginx..."
        sudo setsebool -P httpd_can_network_connect 1 2>/dev/null || true
    fi

    # Настройка фаервола CentOS (открываем порт 80)
    if systemctl is-active --quiet firewalld 2>/dev/null; then
        echo "Открытие порта 80 HTTP в firewalld..."
        sudo firewall-cmd --permanent --add-service=http 2>/dev/null || true
        sudo firewall-cmd --reload 2>/dev/null || true
    fi
else
    echo "Попытка универсальной установки пакетов..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update -y && sudo apt-get install -y python3 python3-pip python3-venv nginx curl git
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y python3 python3-pip nginx curl git
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3 python3-pip nginx curl git
    fi
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Даем доступ Nginx к чтению папки static (если проект в /root, веб-сервер иначе получит 403)
chmod o+x "$HOME" 2>/dev/null || true
chmod -R o+r "$PROJECT_DIR/static" 2>/dev/null || true

echo "=== [2/6] Создание виртуального окружения Python ==="
PYTHON_EXEC="python3"
if command -v python3.9 &> /dev/null; then
    PYTHON_EXEC="python3.9"
fi

if [ ! -d "venv" ]; then
    $PYTHON_EXEC -m venv venv
fi

echo "=== [3/6] Установка библиотек (Flask, Gunicorn, etc.) ==="
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt gunicorn

# Проверка .env файла
if [ ! -f ".env" ]; then
    echo "ВНИМАНИЕ: Файл .env не найден! Создаю шаблон..."
    cat <<EOT > .env
STRATZ_API=
SECRET_KEY=$(openssl rand -hex 24)
EOT
    echo "Создан файл .env. Не забудьте вписать ваш STRATZ_API токен при необходимости."
fi

# Обеспечиваем наличие папки data/
mkdir -p data

echo "=== [4/6] Настройка службы systemd (автозапуск 24/7) ==="
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
EnvironmentFile=$PROJECT_DIR/.env

[Install]
WantedBy=multi-user.target
EOT"

sudo systemctl daemon-reload
sudo systemctl enable stratzdrafter
sudo systemctl restart stratzdrafter

echo "=== [5/6] Настройка веб-сервера Nginx ==="

if [ -d "/etc/nginx/sites-available" ]; then
    # Debian / Ubuntu стиль
    NGINX_CONF="/etc/nginx/sites-available/stratzdrafter"
    sudo bash -c "cat <<EOT > $NGINX_CONF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
        proxy_read_timeout 120s;
    }

    location /static/ {
        alias $PROJECT_DIR/static/;
        expires 7d;
        add_header Cache-Control \"public, max-age=604800\";
    }
}
EOT"
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/stratzdrafter
else
    # CentOS / RHEL / Alma / Rocky стиль
    NGINX_CONF="/etc/nginx/conf.d/stratzdrafter.conf"
    sudo bash -c "cat <<EOT > $NGINX_CONF
server {
    listen 80;
    server_name _;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
        proxy_read_timeout 120s;
    }

    location /static/ {
        alias $PROJECT_DIR/static/;
        expires 7d;
        add_header Cache-Control \"public, max-age=604800\";
    }
}
EOT"
fi

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
