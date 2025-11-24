# Инструкция по деплою Build-Report

## Быстрый деплой

### 1. Клонируйте репозиторий на сервер
```bash
cd /opt
git clone https://github.com/Sixallfaces/Build-Report.git stroykontrol-repo
cd stroykontrol-repo
```

### 2. Создайте файл с секретами
```bash
sudo nano /opt/stroykontrol/.env
```

Содержимое файла:
```env
# Telegram Bot
BOT_TOKEN=ваш_токен_бота_из_BotFather

# Яндекс.Диск
YANDEX_DISK_TOKEN=ваш_OAuth_токен_яндекс_диска
YANDEX_DISK_BASE_FOLDER=StroyKontrol
YANDEX_DISK_PEOPLE_REPORTS_FOLDER=Фото отчеты (Люди)

# ID менеджеров (через запятую)
MANAGER_USER_IDS=5272575484,882521259,6075183361

# База данных
DATABASE_PATH=/opt/stroykontrol/database/stroykontrol.db

# Логирование
LOG_LEVEL=INFO
LOG_FILE=/var/log/stroykontrol.log

# API
API_HOST=127.0.0.1
API_PORT=8000
CORS_ORIGINS=https://build-report.ru

# Временная зона
TIMEZONE=Europe/Moscow
```

### 3. Запустите скрипт деплоя
```bash
chmod +x deploy.sh
sudo ./deploy.sh
```

---

## Ручной деплой

### Шаг 1: Подготовка директорий
```bash
sudo mkdir -p /opt/stroykontrol/{app,database,venv}
```

### Шаг 2: Копирование файлов
```bash
sudo cp -r apps/* /opt/stroykontrol/app/
sudo cp requirements.txt /opt/stroykontrol/app/
```

### Шаг 3: Виртуальное окружение
```bash
sudo python3 -m venv /opt/stroykontrol/venv
sudo /opt/stroykontrol/venv/bin/pip install --upgrade pip
sudo /opt/stroykontrol/venv/bin/pip install -r /opt/stroykontrol/app/requirements.txt
sudo /opt/stroykontrol/venv/bin/pip install python-dotenv
```

### Шаг 4: Systemd сервисы
```bash
sudo cp systemd/stroykontrol-api.service /etc/systemd/system/
sudo cp systemd/stroykontrol-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable stroykontrol-api stroykontrol-bot
sudo systemctl start stroykontrol-api stroykontrol-bot
```

---

## Проверка работоспособности

### Статус сервисов
```bash
sudo systemctl status stroykontrol-api
sudo systemctl status stroykontrol-bot
```

### Логи
```bash
# API сервер
sudo journalctl -u stroykontrol-api -f

# Telegram бот
sudo journalctl -u stroykontrol-bot -f
```

### Тест API
```bash
curl http://localhost:8000/health
# Ответ: {"status":"healthy"}
```

---

## Обновление

После обновления кода в репозитории:
```bash
cd /opt/stroykontrol-repo
git pull
sudo ./deploy.sh
```

---

## Устранение проблем

### Бот не запускается
1. Проверьте токен: `grep BOT_TOKEN /opt/stroykontrol/.env`
2. Проверьте логи: `sudo journalctl -u stroykontrol-bot -n 50`

### API не отвечает
1. Проверьте порт: `sudo netstat -tlnp | grep 8000`
2. Проверьте логи: `sudo journalctl -u stroykontrol-api -n 50`

### Фото не загружаются
1. Проверьте токен Яндекс.Диска в `.env`
2. Убедитесь, что токен имеет права на запись

---

## Безопасность

⚠️ **Важно:**
- Файл `/opt/stroykontrol/.env` содержит секретные токены
- Установите права: `sudo chmod 600 /opt/stroykontrol/.env`
- Не коммитьте `.env` в git (он в `.gitignore`)
