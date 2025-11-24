#!/bin/bash
# ===========================================
# Скрипт деплоя Build-Report на сервер
# ===========================================

set -e  # Остановить при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Деплой Build-Report (Стройконтроль)  ${NC}"
echo -e "${GREEN}========================================${NC}"

# Пути
APP_DIR="/opt/stroykontrol/app"
VENV_DIR="/opt/stroykontrol/venv"
ENV_FILE="/opt/stroykontrol/.env"
DB_DIR="/opt/stroykontrol/database"

# 1. Проверка .env файла
echo -e "\n${YELLOW}[1/6] Проверка конфигурации...${NC}"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}ОШИБКА: Файл $ENV_FILE не найден!${NC}"
    echo -e "Создайте файл с вашими токенами:"
    echo -e "  sudo nano $ENV_FILE"
    echo -e "\nПример содержимого:"
    echo "BOT_TOKEN=ваш_токен_бота"
    echo "YANDEX_DISK_TOKEN=ваш_токен_яндекс_диска"
    echo "MANAGER_USER_IDS=123456789,987654321"
    echo "DATABASE_PATH=/opt/stroykontrol/database/stroykontrol.db"
    exit 1
fi
echo -e "${GREEN}✓ Файл .env найден${NC}"

# 2. Создание директорий
echo -e "\n${YELLOW}[2/6] Создание директорий...${NC}"
sudo mkdir -p "$APP_DIR"
sudo mkdir -p "$DB_DIR"
echo -e "${GREEN}✓ Директории созданы${NC}"

# 3. Сборка фронтенда
echo -e "\n${YELLOW}[3/7] Сборка фронтенда (минификация)...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/build.sh" ]; then
    cd "$SCRIPT_DIR"
    bash build.sh
    echo -e "${GREEN}✓ Фронтенд собран${NC}"
else
    echo -e "${YELLOW}⚠ build.sh не найден, пропускаем сборку${NC}"
fi

# 4. Копирование файлов
echo -e "\n${YELLOW}[4/7] Копирование файлов приложения...${NC}"
sudo cp -r "$SCRIPT_DIR/apps/"* "$APP_DIR/"
sudo cp "$SCRIPT_DIR/requirements.txt" "$APP_DIR/"
echo -e "${GREEN}✓ Файлы скопированы${NC}"

# 5. Установка зависимостей
echo -e "\n${YELLOW}[5/7] Установка зависимостей...${NC}"
if [ ! -d "$VENV_DIR" ]; then
    echo "Создание виртуального окружения..."
    sudo python3 -m venv "$VENV_DIR"
fi
sudo "$VENV_DIR/bin/pip" install --upgrade pip
sudo "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"
sudo "$VENV_DIR/bin/pip" install python-dotenv
echo -e "${GREEN}✓ Зависимости установлены${NC}"

# 6. Установка systemd сервисов
echo -e "\n${YELLOW}[6/7] Установка systemd сервисов...${NC}"
sudo cp "$SCRIPT_DIR/systemd/stroykontrol-api.service" /etc/systemd/system/
sudo cp "$SCRIPT_DIR/systemd/stroykontrol-bot.service" /etc/systemd/system/
sudo systemctl daemon-reload
echo -e "${GREEN}✓ Systemd сервисы установлены${NC}"

# 7. Перезапуск сервисов
echo -e "\n${YELLOW}[7/7] Перезапуск сервисов...${NC}"
sudo systemctl restart stroykontrol-api
sudo systemctl restart stroykontrol-bot
sudo systemctl enable stroykontrol-api
sudo systemctl enable stroykontrol-bot
echo -e "${GREEN}✓ Сервисы перезапущены${NC}"

# Проверка статуса
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  Деплой завершен успешно!  ${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\nСтатус сервисов:"
sudo systemctl status stroykontrol-api --no-pager -l | head -5
echo ""
sudo systemctl status stroykontrol-bot --no-pager -l | head -5

echo -e "\n${YELLOW}Полезные команды:${NC}"
echo "  Логи API:  sudo journalctl -u stroykontrol-api -f"
echo "  Логи бота: sudo journalctl -u stroykontrol-bot -f"
echo "  Статус:    sudo systemctl status stroykontrol-api stroykontrol-bot"
