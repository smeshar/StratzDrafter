#!/usr/bin/env bash
# ==============================================================================
# StratzDrafter — Быстрое обновление проекта из Git и перезапуск службы
# ==============================================================================
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=== [1/3] Загрузка свежего кода из GitHub... ==="
git pull

echo "=== [2/3] Проверка и обновление библиотек... ==="
./venv/bin/pip install -r requirements.txt --quiet

echo "=== [3/3] Перезапуск службы StratzDrafter... ==="
sudo systemctl restart stratzdrafter

echo ""
echo "Успешно! Обновления применены, сервис перезапущен."
