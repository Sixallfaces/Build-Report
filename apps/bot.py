import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from datetime import datetime
import json
import re
import os
import tempfile
import requests
import logging
import traceback
import urllib.parse
import aiosqlite # Импортируем aiosqlite

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/telegram-bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('telegram_bot')

# Настройки
BOT_TOKEN = '8311513221:AAEO5oV-EnidielOmTI6fOUigaoRT4Z3OrQ'
GOOGLE_SHEETS_CREDENTIALS = '/root/telegram-bot/buildreport-472507-3fcd421ee5fc.json'
SPREADSHEET_ID = '13phAhf4kwXS8WeFnw0EhyiOC23mVZclm8Kz91-b8mh4'

# Настройки Яндекс.Диска
YANDEX_DISK_TOKEN = 'y0__xCK3sK_CBi_mDsg-J_i9BQLL_HZkMb3fig6Whe7-Yke5FYqDQ'
YANDEX_DISK_BASE_FOLDER = 'StroyKontrol'
YANDEX_DISK_PEOPLE_REPORTS_FOLDER = 'Фото отчеты (Люди)'

# ID руководителей (замените на реальные)
MANAGER_USER_IDS = {5272575484, 882521259, 6075183361}

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Состояния FSM
class Form(StatesGroup):
    waiting_full_name = State()
    waiting_position = State()
    selecting_action = State()
    selecting_work = State()
    entering_work_quantity = State()
    waiting_photo = State()
    adding_more_works = State()
    waiting_people_photo = State()
    # Новые состояния для руководителя
    manager_selecting_report_type = State()
    manager_entering_custom_date = State()

# Путь к файлу базы данных SQLite
DB_PATH = '/opt/stroykontrol/database/stroykontrol.db'

# === ФУНКЦИИ РАБОТЫ С БАЗОЙ ДАННЫХ ===

async def init_db():
    """Инициализирует базу данных и создает таблицы при необходимости."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица бригадиров
        await db.execute('''
            CREATE TABLE IF NOT EXISTS foremen (
                id INTEGER PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                username TEXT,
                registration_date TEXT NOT NULL,
                yandex_folder_path TEXT
            )
        ''')
        # Таблица работ
        await db.execute('''
            CREATE TABLE IF NOT EXISTS works (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                unit TEXT NOT NULL,
                balance REAL NOT NULL DEFAULT 0,
                project_total REAL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1 -- 1 для активной, 0 для неактивной
            )
        ''')
        # Таблица отчетов о работах
        await db.execute('''
            CREATE TABLE IF NOT EXISTS work_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                foreman_id INTEGER NOT NULL,
                work_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                report_date TEXT NOT NULL,
                report_time TEXT NOT NULL,
                photo_report_url TEXT,
                FOREIGN KEY (foreman_id) REFERENCES foremen (id),
                FOREIGN KEY (work_id) REFERENCES works (id)
            )
        ''')
        await db.commit()
        logger.info("✅ База данных инициализирована.")

async def upgrade_database():
    """Добавляет новые столбцы в базу данных при необходимости"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверяем существование столбца project_total
            async with db.execute("PRAGMA table_info(works)") as cursor:
                columns = [column[1] for column in await cursor.fetchall()]
                
            if 'project_total' not in columns:
                await db.execute('ALTER TABLE works ADD COLUMN project_total REAL DEFAULT 0;')
                await db.commit()
                logger.info("✅ Добавлен столбец project_total в таблицу works")
            else:
                logger.info("✅ Столбец project_total уже существует")
                
    except Exception as e:
        logger.error(f"❌ Ошибка обновления базы данных: {e}")

async def get_foreman_info(user_id: int):
    """Получает информацию о бригадире из базы данных."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT first_name, last_name FROM foremen WHERE id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    full_name, position = row
                    return {
                        'full_name': full_name,
                        'position': position,
                    }
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка получения информации о бригадире: {e}")
        logger.error(traceback.format_exc())
        return None

async def is_user_registered(user_id: int):
    """Проверяет, зарегистрирован ли пользователь и активен."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT 1 FROM foremen WHERE id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row is not None
    except Exception as e:
        logger.warning(f"⚠️ Ошибка проверки регистрации: {e}")
        return False

async def register_foreman(user_id: int, full_name: str, position: str, username: str):
    """Регистрирует нового бригадира в базе данных."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO foremen (id, first_name, last_name, username, registration_date, is_active) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, full_name, position, username, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 1)  # is_active = 1 - сразу активен
            )
            await db.commit()
            logger.info(f"👤 Зарегистрирован новый бригадир: {first_name} {position} (ID: {user_id})")
            return True
    except Exception as e:
        logger.error(f"⚠️ Ошибка регистрации пользователя: {e}")
        logger.error(traceback.format_exc())
        return False

async def check_access(user_id: int):
    """Проверяет, имеет ли пользователь доступ к боту."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT is_active FROM foremen WHERE id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return False, "❌ Вы не зарегистрированы в системе. Используйте /start для регистрации."
                
                is_active = row[0]
                # УБИРАЕМ ПРОВЕРКУ НА АКТИВНОСТЬ, чтобы новые пользователи могли работать
                # if not is_active:
                #     return False, "❌ Доступ ограничен. Обратитесь к руководителю."
                
                return True, None
    except Exception as e:
        logger.error(f"⚠️ Ошибка проверки доступа: {e}")
        return False, "❌ Ошибка проверки доступа. Попробуйте позже."

async def get_active_works():
    """Получает список активных работ из базы данных."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT id, name, category, unit, balance, project_total, is_active FROM works WHERE is_active = 1"
            ) as cursor:
                rows = await cursor.fetchall()
                works = []
                for row in rows:
                    work_id, name, category, unit, balance, project_total, is_active = row
                    works.append({
                        'id': work_id,
                        'Название работы': name,
                        'Категория': category,
                        'Единица измерения': unit,
                        'На балансе': balance,
                        'Проект': project_total,
                        'is_active': is_active
                    })
                logger.info(f"🔍 Найдено активных работ: {len(works)}")
                return works
    except Exception as e:
        logger.error(f"⚠️ Ошибка получения работ: {e}")
        logger.error(traceback.format_exc())
        return []

async def _fetch_work_materials_requirements(db, work_id: int):
    """Получает список материалов и норм расхода для указанной работы."""
    async with db.execute('''
        SELECT wm.material_id, wm.quantity_per_unit, m.name, m.quantity
        FROM work_materials wm
        JOIN materials m ON wm.material_id = m.id
        WHERE wm.work_id = ?
    ''', (work_id,)) as cursor:
        rows = await cursor.fetchall()
        materials = []
        for row in rows:
            material_id, quantity_per_unit, material_name, available_quantity = row
            materials.append({
                'material_id': material_id,
                'quantity_per_unit': quantity_per_unit,
                'material_name': material_name,
                'available_quantity': available_quantity
            })
        return materials

async def update_work_balance(work_id: int, quantity_used: float):
    """Обновляет баланс работы и списывает материалы на складе."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            try:
                await db.execute("BEGIN")

                # Получаем текущий баланс
                async with db.execute(
                    "SELECT balance FROM works WHERE id = ?", (work_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        await db.rollback()
                        return False, "❌ Работа не найдена!"
                    current_balance = row[0]

                new_balance = current_balance - quantity_used
                if new_balance < 0:
                    await db.rollback()                  
                    return False, "❌ Недостаточно материалов на балансе!"
                
                # Проверяем доступность материалов на складе
                materials_requirements = await _fetch_work_materials_requirements(db, work_id)
                for requirement in materials_requirements:
                    total_required = requirement['quantity_per_unit'] * quantity_used
                    if total_required <= 0:
                        continue
                    if requirement['available_quantity'] < total_required:
                        await db.rollback()
                        return False, (
                            f"❌ Недостаточно материала \"{requirement['material_name']}\" на складе!"
                        )

                # Обновляем баланс работы

                await db.execute(
                    "UPDATE works SET balance = ? WHERE id = ?",
                    (new_balance, work_id)
                )

                # Списываем материалы со склада
                for requirement in materials_requirements:
                    total_required = requirement['quantity_per_unit'] * quantity_used
                    if total_required <= 0:
                        continue
                    await db.execute(
                        "UPDATE materials SET quantity = quantity - ? WHERE id = ?",
                        (total_required, requirement['material_id'])
                    )

                await db.commit()
                return True, new_balance
            except Exception as inner_error:
                await db.rollback()
                raise inner_error
    except Exception as e:
        logger.error(f"⚠️ Ошибка обновления баланса: {e}")
        logger.error(traceback.format_exc())
        return False, f"❌ Ошибка обновления баланса: {e}"

async def save_work_report(user_id: int, work_id: int, quantity: float, photo_report_url: str = ""):
    """Сохраняет отчет о выполненной работе в базе данных."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO work_reports (foreman_id, work_id, quantity, report_date, report_time, photo_report_url) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, work_id, quantity,
                 datetime.now().strftime('%Y-%m-%d'),
                 datetime.now().strftime('%H:%M:%S'),
                 photo_report_url)
            )
            await db.commit()
            logger.info(f"✅ Отчет сохранен для работы ID: {work_id}")
            return True
    except Exception as e:
        logger.error(f"⚠️ Ошибка сохранения отчета о работе: {e}")
        logger.error(traceback.format_exc())
        return False

async def get_reports_for_date(target_date: str):
    """Получает отчеты за конкретную дату."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Получаем все отчеты за дату
            async with db.execute('''
                SELECT wr.quantity, wr.photo_report_url, w.name, w.category, w.unit, f.first_name, f.last_name
                FROM work_reports wr
                JOIN works w ON wr.work_id = w.id
                JOIN foremen f ON wr.foreman_id = f.id
                WHERE wr.report_date = ?
            ''', (target_date,)) as cursor:
                rows = await cursor.fetchall()

            # Группируем по бригадирам
            grouped_reports = {}
            for quantity, photo_url, work_name, category, unit, full_name, position in rows:
                if full_name not in grouped_reports:
                    grouped_reports[full_name] = {
                        'position': position,
                        'works': []
                    }
                grouped_reports[full_name]['works'].append({
                    'name': work_name,
                    'quantity': quantity,
                    'unit': unit
                })

            # Формируем результат
            reports = []
            for foreman, info in grouped_reports.items():
                reports.append({
                    'foreman': foreman,
                    'position': info.get('position'),
                    'works': info['works']
                })

            logger.info(f"🔍 Найдено отчетов за {target_date}: {len(reports)} бригадиров")
            return reports
    except Exception as e:
        logger.error(f"❌ Ошибка получения отчетов за дату {target_date}: {e}")
        logger.error(traceback.format_exc())
        return []

async def get_accumulative_statement():
    """Получает накопительную ведомость выполненных работ."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Суммируем все выполненные работы из отчетов и добавляем проектное количество
            async with db.execute('''
                SELECT 
                    w.category AS Категория,
                    w.name AS Работа,
                    w.unit AS Единица_измерения,
                    SUM(wr.quantity) AS Количество,
                    w.project_total AS Проект,
                    CASE 
                        WHEN w.project_total > 0 THEN ROUND((SUM(wr.quantity) / w.project_total) * 100, 2)
                        ELSE 0 
                    END AS Процент_выполнения
                FROM work_reports wr
                JOIN works w ON wr.work_id = w.id
                GROUP BY w.category, w.name, w.unit, w.project_total
                ORDER BY w.category, w.name
            ''') as cursor:
                rows = await cursor.fetchall()
                accumulative_data = []
                for row in rows:
                    category, work, unit, quantity, project_total, percentage = row
                    accumulative_data.append({
                        'Категория': category,
                        'Работа': work,
                        'Единица измерения': unit,
                        'Количество': quantity,
                        'Проект': project_total,
                        '%Выполнения': percentage
                    })
                logger.info(f"📦 Загружена накопительная ведомость: {len(accumulative_data)} записей")
                return accumulative_data
    except Exception as e:
        logger.error(f"❌ Ошибка получения накопительной ведомости: {e}")
        return []

# Настройка Google Sheets (оставлено для совместимости, но не используется)
def setup_google_sheets():
    logger.warning("⚠️ Используется база данных. Функция setup_google_sheets больше не нужна.")
    # Возвращаем фиктивный объект, чтобы избежать ошибок, если он где-то используется
    class DummySpreadsheet:
        def worksheet(self, name):
            raise NotImplementedError("Google Sheets больше не используется")
    return DummySpreadsheet()

# Настройка Яндекс.Диска
def setup_yandex_disk():
    try:
        headers = {
            'Authorization': f'OAuth {YANDEX_DISK_TOKEN}',
            'Content-Type': 'application/json'
        }
        response = requests.get('https://cloud-api.yandex.net/v1/disk/', headers=headers)
        if response.status_code == 200:
            logger.info("✅ Яндекс.Диск настроен успешно!")
            return True
        else:
            logger.error(f"❌ Ошибка настройки Яндекс.Диска: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка настройки Яндекс.Диска: {e}")
        logger.error(traceback.format_exc())
        return False

# Создание папки на Яндекс.Диске
def create_yandex_folder(folder_path):
    try:
        if not folder_path.startswith('/'):
            folder_path = '/' + folder_path
        headers = {
            'Authorization': f'OAuth {YANDEX_DISK_TOKEN}',
            'Content-Type': 'application/json'
        }
        logger.info(f"🔍 Создание папки: {folder_path}")
        url = 'https://cloud-api.yandex.net/v1/disk/resources'
        params = {'path': folder_path}
        response = requests.put(url, headers=headers, params=params)
        if response.status_code in [200, 201]:
            logger.info(f"✅ Папка создана успешно: {folder_path}")
            return True
        elif response.status_code == 409:
            logger.info(f"✅ Папка уже существует: {folder_path}")
            return True
        else:
            logger.error(f"❌ Ошибка создания папки: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка создания папки на Яндекс.Диске: {e}")
        return False

# Публикация папки на Яндекс.Диске и получение публичной ссылки
def publish_yandex_folder(folder_path: str) -> str | None:
    """
    Публикует папку и возвращает публичную ссылку вида https://disk.yandex.ru/d/...
    folder_path — относительный путь, например: 'StroyKontrol/2025-09-26'
    """
    try:
        headers = {
            'Authorization': f'OAuth {YANDEX_DISK_TOKEN}',
            'Content-Type': 'application/json'
        }
        if folder_path.startswith('/'):
            folder_path = folder_path[1:]
        # 1. Публикуем папку
        publish_url = 'https://cloud-api.yandex.net/v1/disk/resources/publish'
        response = requests.put(publish_url, headers=headers, params={'path': folder_path})
        if response.status_code != 200:
            logger.error(f"❌ Не удалось опубликовать папку {folder_path}: {response.status_code} - {response.text}")
            return None
        # 2. Получаем публичную ссылку через GET-запрос с fields=public_url
        info_url = 'https://cloud-api.yandex.net/v1/disk/resources'
        info_response = requests.get(
            info_url,
            headers=headers,
            params={'path': folder_path, 'fields': 'public_url'}
        )
        if info_response.status_code == 200:
            public_url = info_response.json().get('public_url')
            if public_url:
                logger.info(f"🔗 Получена публичная ссылка: {public_url}")
                return public_url
            else:
                logger.warning("⚠️ Папка опубликована, но public_url отсутствует в ответе")
                return None
        else:
            logger.error(f"❌ Ошибка получения public_url: {info_response.status_code} - {info_response.text}")
            return None
    except Exception as e:
        logger.error(f"❌ Исключение при публикации папки: {e}")
        logger.error(traceback.format_exc())
        return None

# Создание папки с датой (для обычных отчетов)
def create_date_folder():
    try:
        current_date = datetime.now().strftime('%Y-%m-%d')
        date_folder_path = f"{YANDEX_DISK_BASE_FOLDER}/{current_date}"
        if not date_folder_path.startswith('/'):
            date_folder_path = '/' + date_folder_path
        logger.info(f"🔍 Создаем папку с датой: {date_folder_path}")
        success = create_yandex_folder(date_folder_path)
        if success:
            logger.info(f"✅ Папка с датой создана! Путь: {date_folder_path}")
            return date_folder_path
        else:
            logger.error(f"❌ Не удалось создать папку с датой")
            return None
    except Exception as e:
        logger.error(f"❌ Ошибка создания папки с датой: {e}")
        logger.error(traceback.format_exc())
        return None

# Создание папки для бригадира внутри папки с датой
def create_foreman_folder(date_folder_path, foreman_name, foreman_id):
    try:
        logger.info(f"🔍 Создание папки для бригадира: {foreman_name}, ID: {foreman_id}")
        safe_foreman_name = re.sub(r'[^\w\-]', '_', foreman_name)
        foreman_folder_path = f"{date_folder_path}/{safe_foreman_name}_ID_{foreman_id}"
        logger.info(f"🔍 Создаем папку бригадира по пути: {foreman_folder_path}")
        success = create_yandex_folder(foreman_folder_path)
        if success:
            logger.info(f"✅ Папка бригадира создана успешно: {foreman_folder_path}")
            return foreman_folder_path
        else:
            logger.error(f"❌ Не удалось создать папку бригадира: {foreman_folder_path}")
            return None
    except Exception as e:
        logger.error(f"❌ Ошибка создания папки для бригадира: {e}")
        logger.error(traceback.format_exc())
        return None

# Загрузка фото на Яндекс.Диск
async def upload_photo_to_yandex(photo_file, folder_path, filename):
    try:
        logger.info(f"🔍 Начало загрузки фото: {filename}")
        file_info = await bot.get_file(photo_file.file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        response = requests.get(file_url, timeout=30)
        if response.status_code != 200:
            logger.error(f"❌ Ошибка скачивания фото: статус {response.status_code}")
            return None

        headers = {
            'Authorization': f'OAuth {YANDEX_DISK_TOKEN}',
            'Content-Type': 'application/json'
        }
        upload_url = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
        file_path = f"{folder_path}/{filename}"
        params = {'path': file_path, 'overwrite': 'true'}

        response_upload = requests.get(upload_url, headers=headers, params=params)
        if response_upload.status_code != 200:
            logger.error(f"❌ Ошибка получения URL для загрузки: {response_upload.status_code} - {response_upload.text}")
            return None

        href = response_upload.json().get('href')
        if not href:
            logger.error("❌ Не получен URL для загрузки")
            return None

        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name

        try:
            with open(temp_file_path, 'rb') as file:
                upload_response = requests.put(href, data=file)

            if upload_response.status_code == 201:
                # Публикуем файл
                public_url_response = requests.put(
                    'https://cloud-api.yandex.net/v1/disk/resources/publish',
                    headers=headers,
                    params={'path': file_path}
                )
                if public_url_response.status_code == 200:
                    # Если публикация прошла успешно, получаем публичную ссылку
                    info_response = requests.get(
                        'https://cloud-api.yandex.net/v1/disk/resources',
                        headers=headers,
                        params={'path': file_path, 'fields': 'public_url'}
                    )
                    if info_response.status_code == 200:
                        return info_response.json().get('public_url')
                    else:
                        logger.error(f"❌ Ошибка получения public_url после публикации: {info_response.status_code}")
                        # Возвращаем путь к файлу как резервный вариант
                        return f"uploaded_file_path: {file_path}"
                else:
                    # Если публикация не удалась, пробуем получить прямую ссылку на файл
                    file_info_response = requests.get(
                        'https://cloud-api.yandex.net/v1/disk/resources',
                        headers=headers,
                        params={'path': file_path}
                    )
                    if file_info_response.status_code == 200:
                        return file_info_response.json().get('file')
                    else:
                        logger.error(f"❌ Ошибка получения ссылки на файл: {file_info_response.status_code}")
                        return f"uploaded_file_path: {file_path}"
            else:
                logger.error(f"❌ Ошибка загрузки фото: {upload_response.status_code}")
                return None
        finally:
            os.unlink(temp_file_path)
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки фото на Яндекс.Диск: {e}")
        logger.error(traceback.format_exc())
        return None

# Загрузка фотоотчета с людьми на Яндекс.Диск
async def upload_people_photo_to_yandex(photo_file, folder_path, filename):
    return await upload_photo_to_yandex(photo_file, folder_path, filename) # переиспользуем ту же логику

# Проверка валидности имени
def is_valid_full_name(full_name: str) -> bool:
    full_name = (full_name or '').strip()
    if len(full_name) < 3 or len(full_name) > 60:
        return False
    return bool(re.match(r'^[a-zA-Zа-яА-ЯёЁ\-\s]+$', full_name))


def is_valid_position(position: str) -> bool:
    position = (position or '').strip()
    if len(position) < 2 or len(position) > 40:
        return False
    return bool(re.match(r'^[a-zA-Zа-яА-ЯёЁ0-9\-.,\s]+$', position))

# === КЛАВИАТУРЫ ===
def get_main_keyboard(user_id: int):
    keyboard = [
        [KeyboardButton(text='📊 Сформировать отчет')],
        [KeyboardButton(text='👥 Отправить фото отчет (Люди)')],
        [KeyboardButton(text='📋 Актуальные задачи')],
        [KeyboardButton(text='ℹ️ Помощь')]
    ]
    if user_id in MANAGER_USER_IDS:
        keyboard.insert(0, [KeyboardButton(text='📥 Выгрузить отчет')])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_photo_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📸 Прикрепить фото')],
            [KeyboardButton(text='➡️ Пропустить фото')],
            [KeyboardButton(text='↩️ Назад')]
        ],
        resize_keyboard=True
    )

def get_add_more_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='✅ Добавить еще работу')],
            [KeyboardButton(text='📤 Завершить отчет')]
        ],
        resize_keyboard=True
    )

def get_people_photo_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📸 Сделать фото')],
            [KeyboardButton(text='📁 Прикрепить фото')],
            [KeyboardButton(text='↩️ Назад')]
        ],
        resize_keyboard=True
    )

def get_back_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='↩️ Назад')]],
        resize_keyboard=True
    )

# НОВЫЕ КЛАВИАТУРЫ ДЛЯ РУКОВОДИТЕЛЯ
def get_manager_report_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📅 За сегодня')],
            [KeyboardButton(text='📆 Ввести дату')],
            [KeyboardButton(text='↩️ Назад')]
        ],
        resize_keyboard=True
    )

def get_manager_back_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='↩️ Назад')]],
        resize_keyboard=True
    )

# === ОБРАБОТЧИКИ ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    # Инициализация базы данных происходит при запуске
    user_id = message.from_user.id
    logger.info(f"👤 Пользователь {user_id} запустил бота")

    # Сначала проверяем, зарегистрирован ли пользователь
    if await is_user_registered(user_id):
        # Если зарегистрирован, проверяем доступ
        has_access, error_msg = await check_access(user_id)
        if not has_access:
            await message.answer(error_msg)
            return
            
        foreman_info = await get_foreman_info(user_id)
        if foreman_info:
            await message.answer(
                f"👷 Добро пожаловать, {foreman_info['full_name']}!\nВыберите действие:",
                reply_markup=get_main_keyboard(user_id)
            )
            await state.set_state(Form.selecting_action)
        else:
            await message.answer("❌ Ошибка получения данных пользователя. Обратитесь к администратору.")
    else:
        # Если не зарегистрирован, начинаем регистрацию
        await message.answer(
            "👋 Добро пожаловать! Похоже, вы здесь впервые.\n"
            "Для начала работы необходимо зарегистрироваться.\n"
            "📝 Пожалуйста, введите ваше Имя:",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(Form.waiting_name)

@dp.message(Form.waiting_full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    full_name = message.text.strip()
    logger.info(f"👤 Пользователь {message.from_user.id} ввел ФИО: {full_name}")
    if not is_valid_full_name(full_name):
        await message.answer(
            "❌ Неверный формат ФИО.\n"
            "Фамилия и Имя должны:\n"
            "• Содержать только буквы и дефисы\n"
            "• Быть длиной от 3 до 60 символов\n"
            "• Не содержать цифры и специальные символы\n"
            "📝 Пожалуйста, введите ваше ФИО еще раз:"
        )
        return
    await state.update_data(first_name=name)
    await message.answer("📝 Теперь введите вашу Должность:", reply_markup=get_back_keyboard())
    await state.set_state(Form.waiting_position)

@dp.message(Form.waiting_position)
async def process_position(message: types.Message, state: FSMContext):
    if message.text == '↩️ Назад':
        await message.answer("📝 Пожалуйста, введите вашу Фамилию и Имя:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(Form.waiting_full_name)
        return
    position = message.text.strip()
    logger.info(f"👤 Пользователь {message.from_user.id} ввел должность: {position}")
    if not is_valid_position(position):
        await message.answer(
            "❌ Неверный формат должности.\n"
            "Должность должна:\n"
            "• Быть длиной от 2 до 40 символов\n"
            "• Содержать только буквы, цифры, пробелы и базовые знаки пунктуации\n"
            "📝 Пожалуйста, введите вашу должность еще раз:",
            reply_markup=get_back_keyboard()
        )
        return
    user_data = await state.get_data()
    full_name = user_data['full_name']
    success = await register_foreman(
        message.from_user.id,
        full_name,
        position,
        message.from_user.username
    )
    if success:
        await message.answer(
            f"✅ Регистрация в программе Стройконтроль завершена!\n"
            f"👷 Добро пожаловать, {full_name}!\n"
            f"💼 Должность: {position}\n"
            f"Теперь вы можете работать с системой отчетности.",
            reply_markup=get_main_keyboard(message.from_user.id)
        )
        await state.set_state(Form.selecting_action)
    else:
        await message.answer("❌ Ошибка при регистрации. Попробуйте еще раз позже.", reply_markup=ReplyKeyboardRemove())
        await state.clear()

@dp.message(Form.selecting_action)
async def handle_main_menu(message: types.Message, state: FSMContext):
    text = message.text
    user_id = message.from_user.id

    has_access, error_msg = await check_access(user_id)
    if not has_access:
        await message.answer(error_msg)
        return

    logger.info(f"👤 Пользователь {user_id} выбрал: {text}")

    if text == '📥 Выгрузить отчет':
        if user_id in MANAGER_USER_IDS:
            await message.answer("Выберите период отчета:", reply_markup=get_manager_report_keyboard())
            await state.set_state(Form.manager_selecting_report_type)
        else:
            await message.answer("❌ У вас нет доступа к этой функции.")
    elif text == '📊 Сформировать отчет':
        await state.update_data(works_list=[])
        works = await get_active_works()
        if not works:
            await message.answer("📝 Нет доступных работ для отчета. Обратитесь к администратору.")
            return
        keyboard = [[KeyboardButton(text=work['Название работы'])] for work in works]
        keyboard.append([KeyboardButton(text='📤 Завершить отчет')])
        keyboard.append([KeyboardButton(text='↩️ Назад')])
        await state.update_data(works=works)
        reply_markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
        await message.answer("Выберите выполненную работу:", reply_markup=reply_markup)
        await state.set_state(Form.selecting_work)
    elif text == '👥 Отправить фото отчет (Люди)':
        await message.answer(
            "👥 Вы выбрали отправку фотоотчета с людьми.\n"
            "Вы можете:\n"
            "• 📸 Сделать фото прямо сейчас\n"
            "• 📁 Прикрепить уже готовое фото\n"
            "Выберите действие:",
            reply_markup=get_people_photo_keyboard()
        )
        await state.set_state(Form.waiting_people_photo)
    elif text == '📋 Актуальные задачи':
        works = await get_active_works()
        if works:
            works_list = "\n".join([
                f"• {work['Название работы']} ({work.get('Категория', 'N/A')}) - "
                f"{work.get('На балансе', 0)} {work.get('Единица измерения', 'шт')} | "
                f"Проект: {work.get('Проект', 0)} {work.get('Единица измерения', 'шт')}"
                for work in works
            ])
            await message.answer(f"📋 Доступные работы:\n{works_list}")
        else:
            await message.answer("📝 Нет доступных работ.")
    elif text == 'ℹ️ Помощь':
        help_text = """
        📊 Сформировать отчет - добавить информацию о выполненной работе с фотоотчетом
        👥 Отправить фото отчет (Люди) - отправить фотоотчет с сотрудниками
        📋 Актуальные задачи - просмотреть доступные работы с кол-вом материала
        🔧 По всем вопросам обращайтесь к администратору.
        """
        await message.answer(help_text)

# НОВЫЕ ОБРАБОТЧИКИ ДЛЯ РУКОВОДИТЕЛЯ
@dp.message(Form.manager_selecting_report_type)
async def handle_manager_report_type(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if message.text == '↩️ Назад':
        await message.answer("Главное меню:", reply_markup=get_main_keyboard(message.from_user.id))
        await state.set_state(Form.selecting_action)
        return
    if message.text == '📅 За сегодня':
        target_date = datetime.now().strftime('%Y-%m-%d')
        await generate_manager_report(message, state, target_date)
    elif message.text == '📆 Ввести дату':
        await message.answer("Введите дату в формате ДД.ММ.ГГГГ:", reply_markup=get_manager_back_keyboard())
        await state.set_state(Form.manager_entering_custom_date)

@dp.message(Form.manager_entering_custom_date)
async def handle_manager_custom_date(message: types.Message, state: FSMContext):
    if message.text == '↩️ Назад':
        await message.answer("Выберите период отчета:", reply_markup=get_manager_report_keyboard())
        await state.set_state(Form.manager_selecting_report_type)
        return
    try:
        input_date = datetime.strptime(message.text.strip(), '%d.%m.%Y')
        target_date = input_date.strftime('%Y-%m-%d')
        await generate_manager_report(message, state, target_date)
    except ValueError:
        await message.answer(
            "❌ Неверный формат даты.\nПожалуйста, введите дату в формате ДД.ММ.ГГГГ:",
            reply_markup=get_manager_back_keyboard()
        )

async def generate_manager_report(message: types.Message, state: FSMContext, target_date: str):
    try:
        reports = await get_reports_for_date(target_date)
        if not reports:
            await message.answer(
                f"📭 Нет отчетов за {target_date.replace('-', '.')}",
                reply_markup=get_main_keyboard(message.from_user.id)
            )
            await state.set_state(Form.selecting_action)
            return

        display_date = target_date.replace('-', '.')
        report_lines = [f"Дата: {display_date}\n"]

        for report_data in reports:
            foreman = report_data['foreman']
            position = report_data.get('position')
            works = report_data['works']
            header_line = f"Бригадир: {foreman}"
            if position:
                header_line += f" ({position})"
            report_lines.append(header_line)
            for w in works:
                work_name = w.get('name', '—')
                quantity = w.get('quantity', '—')
                unit = w.get('unit', '')
                line = f"• {work_name} — {quantity} {unit}".strip()
                report_lines.append(line)
            report_lines.append("")

        report_text = "\n".join(report_lines).strip()

        # === Создаём папку с датой и публикуем её ===
        folder_relative_path = f"{YANDEX_DISK_BASE_FOLDER}/{target_date}"
        # Убеждаемся, что папка существует
        create_yandex_folder('/' + folder_relative_path)
        # Получаем публичную ссылку
        yandex_link = publish_yandex_folder(folder_relative_path)
        if not yandex_link:
            yandex_link = f"📁 Не удалось опубликовать папку. Путь: {folder_relative_path}"

        full_message = f"{report_text}\n📁 Фотоотчёты за эту дату:\n{yandex_link}"
        if len(full_message) > 4096:
            await message.answer(report_text[:4096])
            await message.answer(f"...\n📁 Фотоотчёты: {yandex_link}")
        else:
            await message.answer(full_message, reply_markup=get_main_keyboard(message.from_user.id))

        await state.set_state(Form.selecting_action)

    except Exception as e:
        logger.error(f"❌ Ошибка генерации отчёта: {e}")
        logger.error(traceback.format_exc())
        await message.answer(
            "❌ Ошибка при формировании отчёта. Обратитесь к администратору.",
            reply_markup=get_main_keyboard(message.from_user.id)
        )
        await state.set_state(Form.selecting_action)

@dp.message(Form.waiting_people_photo)
async def handle_people_photo(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text == '↩️ Назад':
        await message.answer("Главное меню:", reply_markup=get_main_keyboard(message.from_user.id))
        await state.set_state(Form.selecting_action)
        return
    if message.text in ['📸 Сделать фото', '📁 Прикрепить фото']:
        await message.answer("📸 Отправьте фото:", reply_markup=get_back_keyboard())
        return
    if message.photo:
        try:
            user_id = message.from_user.id
            foreman_info = await get_foreman_info(user_id)
            if not foreman_info:
                await message.answer("❌ Ошибка получения данных пользователя.")
                await state.set_state(Form.selecting_action)
                return
            if not setup_yandex_disk():
                await message.answer("❌ Ошибка подключения к Яндекс.Диску.")
                await state.set_state(Form.selecting_action)
                return

            has_access, error_msg = await check_access(user_id)
            if not has_access:
                await message.answer(error_msg)
                await state.set_state(Form.selecting_action)
                return

            create_yandex_folder(YANDEX_DISK_BASE_FOLDER)
            create_yandex_folder(f"{YANDEX_DISK_BASE_FOLDER}/{YANDEX_DISK_PEOPLE_REPORTS_FOLDER}")
            current_date = datetime.now().strftime('%Y-%m-%d')
            people_date_folder_path = f"/{YANDEX_DISK_BASE_FOLDER}/{YANDEX_DISK_PEOPLE_REPORTS_FOLDER}/{current_date}"
            create_yandex_folder(people_date_folder_path)

            photo = message.photo[-1]
            timestamp = datetime.now().strftime('%H-%M-%S')
            filename = f"{foreman_info['full_name']}_{foreman_info.get('position', '')}_{current_date}_{timestamp}.jpg"            
            filename = re.sub(r'[^\w\-_.]', '_', filename)

            photo_url = await upload_people_photo_to_yandex(photo, people_date_folder_path, filename)

            position_text = foreman_info.get('position') or '—'
            await message.answer(
                f"✅ Фотоотчет с людьми успешно загружен!\n"
                f"👷 Бригадир: {foreman_info['full_name']}\n"
                f"💼 Должность: {position_text}\n"
                f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                f"Фото сохранено в папке: {YANDEX_DISK_PEOPLE_REPORTS_FOLDER}",
                reply_markup=get_main_keyboard(user_id)
            )
            await state.set_state(Form.selecting_action)
        except Exception as e:
            logger.error(f"❌ Ошибка обработки фотоотчета с людьми: {e}")
            await message.answer("❌ Ошибка обработки фотоотчета. Попробуйте еще раз.", reply_markup=get_main_keyboard(message.from_user.id))
            await state.set_state(Form.selecting_action)

    # Проверяем доступ
    has_access, error_msg = await check_access(user_id)
    if not has_access:
        await message.answer(error_msg)
        await state.set_state(Form.selecting_action)
        return

@dp.message(Form.selecting_work)
async def handle_work_selection(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text == '↩️ Назад':
        await message.answer("Главное меню:", reply_markup=get_main_keyboard(message.from_user.id))
        await state.set_state(Form.selecting_action)
        return
    if message.text == '📤 Завершить отчет':
        data = await state.get_data()
        works_list = data.get('works_list', [])
        count = len(works_list)
        msg = f"✅ Отчет завершен! Количество: {count}" if works_list else "📝 Отчет завершен без добавления работ."
        await message.answer(msg, reply_markup=get_main_keyboard(message.from_user.id))
        await state.set_state(Form.selecting_action)
        return
    
    has_access, error_msg = await check_access(user_id)
    if not has_access:
        await message.answer(error_msg)
        await state.set_state(Form.selecting_action)
        return

    data = await state.get_data()
    works = data.get('works', [])
    selected_work = next((w for w in works if w['Название работы'].strip().lower() == message.text.strip().lower()), None)

    if selected_work:
        work_id = selected_work['id'] # Получаем ID из БД
        await state.update_data(selected_work_id=work_id, selected_work_name=selected_work['Название работы']) # Сохраняем ID
        unit = selected_work.get('Единица измерения', 'шт')
        balance = selected_work.get('На балансе', 0)
        category = selected_work.get('Категория', '')
        await message.answer(
            f"🏗 Выбрана работа: {selected_work['Название работы']}\n"
            f"📁 Категория: {category}\n"
            f"📊 Доступно: {balance} {unit}\n"
            f"Введите количество ({unit}):",
            reply_markup=get_back_keyboard()
        )
        await state.set_state(Form.entering_work_quantity)
    else:
        available = "\n".join([f"• {w['Название работы']} ({w.get('Категория', '')})" for w in works])
        await message.answer(f"❌ Работа '{message.text}' не найдена.\nДоступные работы:\n{available}")

@dp.message(Form.entering_work_quantity)
async def handle_work_quantity(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text == '↩️ Назад':
        data = await state.get_data()
        works = data.get('works', [])
        keyboard = [[KeyboardButton(text=w['Название работы'])] for w in works]
        keyboard += [[KeyboardButton(text='📤 Завершить отчет')], [KeyboardButton(text='↩️ Назад')]]
        await message.answer("Выберите выполненную работу:", reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True))
        await state.set_state(Form.selecting_work)
        return

    has_access, error_msg = await check_access(user_id)
    if not has_access:
        await message.answer(error_msg)
        await state.set_state(Form.selecting_action)
        return

    try:
        quantity = float(message.text)
        data = await state.get_data()
        work_id = data['selected_work_id'] # Получаем ID из состояния
        work_name = data['selected_work_name'] # Получаем имя для отображения
        await state.update_data(work_id=work_id, work_name=work_name, quantity=quantity) # Сохраняем ID и имя
        await message.answer("📸 Хотите прикрепить фотоотчет к выполненной работе?", reply_markup=get_photo_keyboard())
        await state.set_state(Form.waiting_photo)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число:", reply_markup=get_back_keyboard())

@dp.message(Form.waiting_photo)
async def handle_photo_choice(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text == '↩️ Назад':
        data = await state.get_data()
        work_id = data.get('work_id', 0) # Получаем ID
        work_name = data.get('work_name', 'Неизвестная работа') # Получаем имя
        # Нужно получить unit и category заново из БД, так как они не сохранены в FSM
        works = await get_active_works()
        selected_work = next((w for w in works if w['id'] == work_id), None)
        unit = selected_work.get('Единица измерения', 'шт') if selected_work else 'шт'
        await message.answer(f"Введите количество ({unit}):", reply_markup=get_back_keyboard())
        await state.set_state(Form.entering_work_quantity)
        return
    if message.text == '➡️ Пропустить фото':
        await save_report_with_photo(message, state, photo_url="")
        return
    if message.text == '📸 Прикрепить фото':
        await message.answer("📸 Пожалуйста, отправьте фотографию выполненной работы:", reply_markup=get_back_keyboard())
        return
    if message.photo:
        try:
            data = await state.get_data()
            work_id = data.get('work_id', 0) # Получаем ID
            work_name = data.get('work_name', 'Неизвестная работа') # Получаем имя
            quantity = data.get('quantity', 0)
            user_id = message.from_user.id

            if not setup_yandex_disk():
                await message.answer("❌ Ошибка подключения к Яндекс.Диску. Отчет сохранен без фото.")
                await save_report_with_photo(message, state, photo_url="")
                return

            create_yandex_folder(YANDEX_DISK_BASE_FOLDER)
            date_folder = create_date_folder()
            if not date_folder:
                await message.answer("❌ Ошибка создания папки с датой. Отчет сохранен без фото.")
                await save_report_with_photo(message, state, photo_url="")
                return

            foreman_info = await get_foreman_info(user_id)
            if not foreman_info:
                await message.answer("❌ Ошибка получения данных. Отчет сохранен без фото.")
                await save_report_with_photo(message, state, photo_url="")
                return

            foreman_folder = create_foreman_folder(date_folder, foreman_info['full_name'], user_id)
            if not foreman_folder:
                await message.answer("❌ Ошибка создания папки бригадира. Отчет сохранен без фото.")
                await save_report_with_photo(message, state, photo_url="")
                return

            photo = message.photo[-1]
            timestamp = datetime.now().strftime('%H-%M-%S')
            filename = f"{work_name}_{timestamp}.jpg" # Используем имя работы
            filename = re.sub(r'[^\w\-_.]', '_', filename)

            photo_url = await upload_photo_to_yandex(photo, foreman_folder, filename)

            if photo_url:
                await message.answer("✅ Фото успешно загружено!")
            else:
                await message.answer("❌ Ошибка загрузки фото. Отчет сохранен без фото.")

            await save_report_with_photo(message, state, photo_url or "")
        except Exception as e:
            logger.error(f"❌ Ошибка обработки фото: {e}")
            await message.answer("❌ Ошибка обработки фото. Отчет сохранен без фото.")
            await save_report_with_photo(message, state, "")

    has_access, error_msg = await check_access(user_id)
    if not has_access:
        await message.answer(error_msg)
        await state.set_state(Form.selecting_action)
        return

async def save_report_with_photo(message: types.Message, state: FSMContext, photo_url: str):
    try:
        data = await state.get_data()
        work_id = data.get('work_id', 0) # Получаем ID
        work_name = data.get('work_name', 'Неизвестная работа') # Получаем имя
        quantity = data.get('quantity', 0)
        works_list = data.get('works_list', [])

        success, result = await update_work_balance(work_id, quantity) # Передаем ID
        if not success:
            await message.answer(result, reply_markup=get_main_keyboard(message.from_user.id))
            await state.set_state(Form.selecting_action)
            return

        report_success = await save_work_report(
            message.from_user.id,
            work_id, # Передаем ID
            quantity,
            photo_url
        )

        if report_success:
            # Нужно получить unit заново из БД
            works = await get_active_works()
            selected_work = next((w for w in works if w['id'] == work_id), None)
            unit = selected_work.get('Единица измерения', 'шт') if selected_work else 'шт'

            foreman_info = await get_foreman_info(message.from_user.id)
            photo_text = " с фотоотчетом" if photo_url else ""
            works_list.append({'work_name': work_name, 'quantity': quantity, 'unit': unit, 'photo': photo_text})
            await state.update_data(works_list=works_list)
            count = len(works_list)
            await message.answer(
                f"✅ Работа добавлена в отчет{photo_text}!\n"
                f"👷 Бригадир: {foreman_info['full_name']}\n"
                f"💼 Должность: {foreman_info.get('position') or '—'}\n"
                f"🏗 Работа: {work_name}\n" # Используем имя
                f"📊 Количество: {quantity} {unit}\n"
                f"💰 Остаток: {result} {unit}\n"
                f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                f"📋 В отчете уже {count} шт\n"
                f"Хотите добавить еще работу в отчет?",
                reply_markup=get_add_more_keyboard()
            )
            await state.set_state(Form.adding_more_works)
        else:
            await message.answer("❌ Ошибка при сохранении отчета. Попробуйте еще раз.")
            await state.set_state(Form.selecting_action)
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения отчета: {e}")
        await message.answer("❌ Ошибка при сохранении отчета. Попробуйте еще раз.")
        await state.set_state(Form.selecting_action)

@dp.message(Form.adding_more_works)
async def handle_add_more_works(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if message.text == '✅ Добавить еще работу':
        data = await state.get_data()
        works = data.get('works', [])
        keyboard = [[KeyboardButton(text=w['Название работы'])] for w in works]
        keyboard += [[KeyboardButton(text='📤 Завершить отчет')], [KeyboardButton(text='↩️ Назад')]]
        await message.answer("Выберите выполненную работу:", reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True))
        await state.set_state(Form.selecting_work)
    elif message.text == '📤 Завершить отчет':
        data = await state.get_data()
        works_list = data.get('works_list', [])
        count = len(works_list)
        await message.answer(
            f"✅ Отчет завершен! Всего добавлено работ: {count}\nВыберите действия:",
            reply_markup=get_main_keyboard(message.from_user.id)
        )
        await state.set_state(Form.selecting_action)
    else:
        await message.answer("Пожалуйста, выберите действие:", reply_markup=get_add_more_keyboard())

        has_access, error_msg = await check_access(user_id)
    if not has_access:
        await message.answer(error_msg)
        await state.set_state(Form.selecting_action)
        return

# Запуск бота
async def main():
    logger.info("🚀 Запуск строительного бота...")

    # Инициализируем базу данных
    await init_db()
    
    # Обновляем структуру базы данных при необходимости
    await upgrade_database()

    if setup_yandex_disk():
        create_yandex_folder(YANDEX_DISK_BASE_FOLDER)
        create_yandex_folder(f"{YANDEX_DISK_BASE_FOLDER}/{YANDEX_DISK_PEOPLE_REPORTS_FOLDER}")

    logger.info("✅ Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())