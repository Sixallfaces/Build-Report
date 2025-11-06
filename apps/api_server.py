# api_server.py
import aiosqlite
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import json
import logging
from datetime import datetime
import traceback
import hashlib
import secrets
from datetime import datetime, timedelta
import openpyxl
from openpyxl import Workbook
import io
from fastapi import UploadFile, File
from fastapi.responses import StreamingResponse

# --- Настройки ---
DB_PATH = '/opt/stroykontrol/database/stroykontrol.db'
API_HOST = '127.0.0.1'
API_PORT = 8080

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('api_server')

# --- Приложение FastAPI ---
app = FastAPI(title="StroyKontrol API", version="1.0.0")

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://build-report.ru"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Хэш-функция для паролей
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# Таблица пользователей сайта
async def init_site_users_table():
    """Создает таблицу для пользователей сайта"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS site_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_date TEXT NOT NULL,
                last_login TEXT
            )
        ''')
        await db.commit()

# ========== ФУНКЦИИ ДЛЯ РАБОТ ==========
async def get_active_works_from_db():
    """Получает список активных работ из базы данных - ДЛЯ БОТА."""
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
                        'Проект': project_total,  # НОВОЕ ПОЛЕ
                        'is_active': bool(is_active)
                    })
                logger.info(f"🔍 Найдено активных работ в БД: {len(works)}")
                return works
    except Exception as e:
        logger.error(f"⚠️ Ошибка получения активных работ: {e}")
        return []

async def get_all_works_from_db():
    """Получает список ВСЕХ работ из базы данных - ДЛЯ САЙТА."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT id, name, category, unit, balance, project_total, is_active FROM works"
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
                        'Проект': project_total,  # НОВОЕ ПОЛЕ
                        'is_active': bool(is_active)
                    })
                logger.info(f"🔍 Найдено всех работ в БД: {len(works)}")
                return works
    except Exception as e:
        logger.error(f"⚠️ Ошибка получения всех работ: {e}")
        return []

async def get_work_by_id(work_id: int):
    """Получает конкретную работу по ID."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT id, name, category, unit, balance, project_total, is_active FROM works WHERE id = ?",
                (work_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    work_id, name, category, unit, balance, project_total, is_active = row
                    return {
                        'id': work_id,
                        'Название работы': name,
                        'Категория': category,
                        'Единица измерения': unit,
                        'На балансе': balance,
                        'Проект': project_total,  # НОВОЕ ПОЛЕ
                        'is_active': bool(is_active)
                    }
        return None
    except Exception as e:
        logger.error(f"⚠️ Ошибка получения работы по ID {work_id}: {e}")
        return None

async def insert_work_to_db(work_data: dict):
    """Добавляет новую работу в базу данных."""
    try:
        logger.info(f"DEBUG: insert_work_to_db пытается вставить: {work_data}")
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO works (name, category, unit, balance, project_total, is_active) VALUES (?, ?, ?, ?, ?, ?)",
                (work_data['name'], work_data['category'], work_data['unit'], 
                 work_data['balance'], work_data.get('project_total', 0), work_data['is_active'])
            )
            await db.commit()
            work_id = db.last_insert_rowid()
            logger.info(f"🏗️ Добавлена новая работа: {work_data['name']} (ID: {work_id})")
            return work_id
    except aiosqlite.IntegrityError as e:
        logger.error(f"❌ Ошибка целостности базы данных при вставке {work_data}: {e}")
        raise
    except Exception as e:
        logger.error(f"⚠️ Неожиданная ошибка добавления работы {work_data}: {e}")
        logger.error(traceback.format_exc())
        return None

async def update_work_in_db(work_id: int, work_data: dict):
    """Обновляет существующую работу в базе данных."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE works SET name = ?, category = ?, unit = ?, balance = ?, project_total = ?, is_active = ? WHERE id = ?",
                (work_data['name'], work_data['category'], work_data['unit'], 
                 work_data['balance'], work_data.get('project_total', 0), work_data['is_active'], work_id)
            )
            await db.commit()
            if db.rowcount > 0:
                logger.info(f"🏗️ Обновлена работа ID: {work_id}")
                return True
        return False
    except Exception as e:
        logger.error(f"⚠️ Ошибка обновления работы ID {work_id}: {e}")
        return False
    
async def add_balance_to_work_in_db(work_id: int, amount: float):
    """Увеличивает баланс работы на указанную величину."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            try:
                await db.execute("BEGIN")

                async with db.execute(
                    "SELECT balance FROM works WHERE id = ?",
                    (work_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        await db.rollback()
                        return None

                    current_balance = row[0] if row[0] is not None else 0

                new_balance = current_balance + amount

                await db.execute(
                    "UPDATE works SET balance = ? WHERE id = ?",
                    (new_balance, work_id)
                )
                await db.commit()
                logger.info(
                    f"🏗️ Баланс работы ID: {work_id} увеличен на {amount}. Новый баланс: {new_balance}"
                )
                return new_balance
            except Exception as inner_error:
                await db.rollback()
                logger.error(
                    f"⚠️ Ошибка при увеличении баланса работы ID {work_id}: {inner_error}"
                )
                return None
    except Exception as e:
        logger.error(f"⚠️ Ошибка соединения при увеличении баланса работы ID {work_id}: {e}")
        return None 

async def delete_work_from_db(work_id: int):
    """Удаляет работу из базы данных."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            try:
                await db.execute("BEGIN")
                await db.execute("DELETE FROM work_materials WHERE work_id = ?", (work_id,))
                await db.execute("DELETE FROM works WHERE id = ?", (work_id,))
                await db.commit()
                if db.total_changes > 0:
                    logger.info(f"🗑️ Удалена работа ID: {work_id}")
                    return True
            except Exception as inner_error:
                await db.rollback()
                logger.error(f"⚠️ Ошибка при удалении работы ID {work_id}: {inner_error}")
                return False
        return False
    except Exception as e:
        logger.error(f"⚠️ Ошибка удаления работы ID {work_id}: {e}")
        return False

# ========== ФУНКЦИИ ДЛЯ БРИГАДИРОВ ==========
async def get_foremen_from_db():
    """Получает список всех бригадиров из базы данных (и активных, и неактивных)."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT id, first_name, last_name, username, registration_date, is_active FROM foremen"
            ) as cursor:
                rows = await cursor.fetchall()
                foremen = []
                for row in rows:
                    foreman_id, full_name, position, username, reg_date, is_active = row
                    foremen.append({
                        'id': foreman_id,
                        'full_name': full_name,
                        'position': position or '',
                        'first_name': full_name,  # для обратной совместимости
                        'last_name': position or '',
                        'username': username,
                        'registration_date': reg_date,
                        'is_active': bool(is_active) if is_active is not None else True
                    })
                logger.info(f"👥 Найдено бригадиров в БД: {len(foremen)}")
                return foremen
    except Exception as e:
        logger.error(f"⚠️ Ошибка получения бригадиров: {e}")
        return []
    
async def get_foreman_display_name(db, foreman_id: Optional[int]) -> str:
    """Возвращает отображаемое имя бригадира"""
    if foreman_id is None:
        return 'Неизвестный бригадир'

    async with db.execute(
        "SELECT first_name, last_name FROM foremen WHERE id = ?",
        (foreman_id,)
    ) as cursor:
        row = await cursor.fetchone()
        if row:
            first_name, last_name = row
            parts = [part for part in [first_name, last_name] if part]
            if parts:
                return f"Бригадир {' '.join(parts)}"
    return f"Бригадир ID {foreman_id}"

async def create_foreman_in_db(foreman_data: dict):
    """Создает нового бригадира в базе данных."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO foremen (first_name, last_name, username, registration_date, is_active) VALUES (?, ?, ?, ?, ?)",
                (foreman_data['full_name'], foreman_data['position'],
                 foreman_data.get('username', ''), datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 1)  # is_active = 1 по умолчанию
            )
            await db.commit()
            foreman_id = db.last_insert_rowid()
            logger.info(f"👤 Добавлен новый бригадир: {foreman_data['full_name']} ({foreman_data['position']}) (ID: {foreman_id})")
            return foreman_id
    except Exception as e:
        logger.error(f"❌ Ошибка добавления бригадира: {e}")
        return None

# Обновим функцию update_foreman_in_db для поддержки is_active
async def update_foreman_in_db(foreman_id: int, foreman_data: dict):
    """Обновляет данные бригадира в базе данных."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT first_name, last_name, username, is_active FROM foremen WHERE id = ?",
                (foreman_id,)
            ) as cursor:
                existing = await cursor.fetchone()

            if not existing:
                return False

            existing_first, existing_last, existing_username, existing_is_active = existing

            first_name = (
                foreman_data.get('full_name')
                or foreman_data.get('first_name')
                or existing_first
            )
            last_name = (
                foreman_data.get('position')
                or foreman_data.get('last_name')
                or existing_last
            )
            username = (
                foreman_data['username']
                if 'username' in foreman_data
                else (existing_username or '')
            )
            is_active = foreman_data.get('is_active', existing_is_active)

            await db.execute(
                "UPDATE foremen SET first_name = ?, last_name = ?, username = ?, is_active = ? WHERE id = ?",
                (first_name, last_name, username, is_active, foreman_id)

            )
            await db.commit()
            logger.info(
                f"👤 Обновлен бригадир ID: {foreman_id}, is_active: {is_active}"
            )
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка обновления бригадира ID {foreman_id}: {e}")
        return False

async def delete_foreman_from_db(foreman_id: int):
    """Удаляет бригадира из базы данных."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверяем, есть ли отчеты у бригадира
            async with db.execute(
                "SELECT COUNT(*) FROM work_reports WHERE foreman_id = ?", 
                (foreman_id,)
            ) as cursor:
                report_count = await cursor.fetchone()
                if report_count and report_count[0] > 0:
                    return False, "Нельзя удалить бригадира, у которого есть отчеты"
            
            cursor = await db.execute("DELETE FROM foremen WHERE id = ?", (foreman_id,))
            await db.commit()
            if cursor.rowcount and cursor.rowcount > 0:
                logger.info(f"🗑️ Удален бригадир ID: {foreman_id}")
                return True, "Бригадир успешно удален"
        return False, "Бригадир не найден"
    except Exception as e:
        logger.error(f"❌ Ошибка удаления бригадира ID {foreman_id}: {e}")
        return False, f"Ошибка удаления: {str(e)}"

# ========== ФУНКЦИИ ДЛЯ КАТЕГОРИЙ ==========
async def init_categories_table():
    """Создает таблицу для категорий"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_date TEXT NOT NULL
            )
        ''')
        await db.commit()

async def get_categories_from_db():
    """Получает список всех категорий из базы данных."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT id, name, created_date FROM categories ORDER BY name"
            ) as cursor:
                rows = await cursor.fetchall()
                categories = []
                for row in rows:
                    category_id, name, created_date = row
                    categories.append({
                        'id': category_id,
                        'name': name,
                        'created_date': created_date
                    })
                logger.info(f"📂 Найдено категорий в БД: {len(categories)}")
                return categories
    except Exception as e:
        logger.error(f"⚠️ Ошибка получения категорий: {e}")
        return []

async def create_category_in_db(category_data: dict):
    """Добавляет новую категорию в базу данных."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO categories (name, created_date) VALUES (?, ?)",
                (category_data['name'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            await db.commit()
            category_id = db.last_insert_rowid()
            logger.info(f"📂 Добавлена новая категория: {category_data['name']} (ID: {category_id})")
            return category_id
    except aiosqlite.IntegrityError:
        raise HTTPException(status_code=400, detail="Категория с таким названием уже существует")
    except Exception as e:
        logger.error(f"⚠️ Ошибка добавления категории: {e}")
        return None
    
    # ========== ФУНКЦИИ ДЛЯ МАТЕРИАЛОВ ==========
async def init_materials_table():
    """Создает таблицу для материалов склада"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                unit TEXT NOT NULL,
                quantity REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        ''')
        await db.commit()

async def init_work_materials_table():
    """Создает таблицу соответствия работ и материалов"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS work_materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_id INTEGER NOT NULL,
                material_id INTEGER NOT NULL,
                quantity_per_unit REAL NOT NULL DEFAULT 0,
                UNIQUE(work_id, material_id),
                FOREIGN KEY (work_id) REFERENCES works(id) ON DELETE CASCADE,
                FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE CASCADE
            )
        ''')
        await db.commit()

async def init_material_history_table():
    """Создает таблицу истории движения материалов"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS material_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id INTEGER NOT NULL,
                change_type TEXT NOT NULL,
                change_amount REAL NOT NULL,
                resulting_quantity REAL,
                performed_by TEXT,
                description TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE CASCADE
            )
        ''')
        await db.commit()

async def log_material_history_entry(
    db,
    material_id: int,
    change_amount: float,
    change_type: str,
    performed_by: Optional[str] = None,
    description: Optional[str] = None
):
    """Добавляет запись в историю движения материалов"""
    performed_by_value = (performed_by or 'Неизвестно').strip() or 'Неизвестно'
    description_value = (description or '').strip()

    resulting_quantity = None
    async with db.execute(
        "SELECT quantity FROM materials WHERE id = ?",
        (material_id,)
    ) as cursor:
        row = await cursor.fetchone()
        if row is not None:
            resulting_quantity = row[0]

    await db.execute(
        '''INSERT INTO material_history
           (material_id, change_type, change_amount, resulting_quantity, performed_by, description, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (
            material_id,
            change_type,
            change_amount,
            resulting_quantity,
            performed_by_value,
            description_value,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
    )

async def get_material_history_from_db(limit: int = 500):
    """Возвращает историю движения материалов"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                '''SELECT mh.id, mh.material_id, m.name, m.unit, mh.change_type, mh.change_amount,
                          mh.resulting_quantity, mh.performed_by, mh.description, mh.created_at
                   FROM material_history mh
                   LEFT JOIN materials m ON m.id = mh.material_id
                   ORDER BY mh.created_at DESC, mh.id DESC
                   LIMIT ?''',
                (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                history = []
                for row in rows:
                    (entry_id, material_id, material_name, unit, change_type, change_amount,
                     resulting_quantity, performed_by, description, created_at) = row
                    history.append({
                        'id': entry_id,
                        'material_id': material_id,
                        'material_name': material_name,
                        'unit': unit,
                        'change_type': change_type,
                        'change_amount': change_amount,
                        'resulting_quantity': resulting_quantity,
                        'performed_by': performed_by,
                        'description': description,
                        'created_at': created_at
                    })
                return history
    except Exception as e:
        logger.error(f"⚠️ Ошибка получения истории материалов: {e}")
        return []        

async def get_all_materials_from_db():
    """Получает список всех материалов"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT id, category, name, unit, quantity, created_at FROM materials ORDER BY name"
            ) as cursor:
                rows = await cursor.fetchall()
                materials = []
                for row in rows:
                    material_id, category, name, unit, quantity, created_at = row
                    materials.append({
                        'id': material_id,
                        'category': category,
                        'name': name,
                        'unit': unit,
                        'quantity': quantity,
                        'created_at': created_at
                    })
                logger.info(f"📦 Найдено материалов в БД: {len(materials)}")
                return materials
    except Exception as e:
        logger.error(f"⚠️ Ошибка получения материалов: {e}")
        return []

async def get_material_by_id(material_id: int):
    """Получает материал по ID"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT id, category, name, unit, quantity, created_at FROM materials WHERE id = ?",
                (material_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    material_id, category, name, unit, quantity, created_at = row
                    return {
                        'id': material_id,
                        'category': category,
                        'name': name,
                        'unit': unit,
                        'quantity': quantity,
                        'created_at': created_at
                    }
        return None
    except Exception as e:
        logger.error(f"⚠️ Ошибка получения материала ID {material_id}: {e}")
        return None

async def fetch_work_materials_requirements(db, work_id: int):
    """Получает список материалов и норм расхода для указанной работы, используя существующее соединение"""
    async with db.execute('''
        SELECT wm.material_id, wm.quantity_per_unit, m.name, m.unit, m.category, m.quantity
        FROM work_materials wm
        JOIN materials m ON wm.material_id = m.id
        WHERE wm.work_id = ?
    ''', (work_id,)) as cursor:
        rows = await cursor.fetchall()
        materials = []
        for row in rows:
            material_id, quantity_per_unit, name, unit, category, available_quantity = row
            materials.append({
                'material_id': material_id,
                'quantity_per_unit': quantity_per_unit,
                'material_name': name,
                'unit': unit,
                'category': category,
                'available_quantity': available_quantity
            })
        return materials

async def get_work_materials_from_db(work_id: int):
    """Возвращает материалы, закрепленные за работой"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            return await fetch_work_materials_requirements(db, work_id)
    except Exception as e:
        logger.error(f"⚠️ Ошибка получения материалов для работы ID {work_id}: {e}")
        return []

async def replace_work_materials_for_work(work_id: int, materials_data: List[dict]):
    """Полностью заменяет набор материалов для работы"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            try:
                await db.execute("BEGIN")
                await db.execute("DELETE FROM work_materials WHERE work_id = ?", (work_id,))

                for item in materials_data:
                    await db.execute(
                        "INSERT INTO work_materials (work_id, material_id, quantity_per_unit) VALUES (?, ?, ?)",
                        (work_id, item['material_id'], item['quantity_per_unit'])
                    )

                await db.commit()
                logger.info(f"🔗 Обновлены материалы для работы ID: {work_id}")
                return True, None
            except aiosqlite.IntegrityError as e:
                await db.rollback()
                logger.error(f"❌ Ошибка целостности при обновлении материалов работы {work_id}: {e}")
                return False, "Невозможно сохранить материалы для работы"
            except Exception as e:
                await db.rollback()
                logger.error(f"⚠️ Ошибка обновления материалов для работы {work_id}: {e}")
                return False, str(e)
    except Exception as e:
        logger.error(f"⚠️ Не удалось установить соединение для обновления материалов работы {work_id}: {e}")
        return False, str(e)


async def insert_material_to_db(material_data: dict, performed_by: Optional[str] = None):
    """Добавляет новый материал"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "INSERT INTO materials (category, name, unit, quantity, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    material_data['category'],
                    material_data['name'],
                    material_data['unit'],
                    material_data['quantity'],
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
            )
            
            material_id = cursor.lastrowid
            logger.info(f"📦 Добавлен новый материал: {material_data['name']} (ID: {material_id})")
            await log_material_history_entry(
                db,
                material_id,
                material_data['quantity'],
                'Создание',
                performed_by or 'Система',
                'Создание материала'
            )
            await db.commit()
            return material_id
    except Exception as e:
        logger.error(f"⚠️ Ошибка добавления материала {material_data}: {e}")
        raise

async def update_material_in_db(material_id: int, material_data: dict, performed_by: Optional[str] = None):
    """Обновляет материал"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute(
                "SELECT quantity FROM materials WHERE id = ?",
                (material_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return False
                previous_quantity = row[0] if row[0] is not None else 0

            cursor = await db.execute(
                "UPDATE materials SET category = ?, name = ?, unit = ?, quantity = ? WHERE id = ?",
                (
                    material_data['category'],
                    material_data['name'],
                    material_data['unit'],
                    material_data['quantity'],
                    material_id
                )
            )
            row_updated = cursor.rowcount and cursor.rowcount > 0
            if row_updated:
                logger.info(f"📦 Обновлен материал ID: {material_id}")
                change_amount = material_data['quantity'] - previous_quantity
                if abs(change_amount) > 0:
                    await log_material_history_entry(
                        db,
                        material_id,
                        change_amount,
                        'Корректировка',
                        performed_by or 'Система',
                        'Обновление данных материала'
                    )
            await db.commit()
            if row_updated:
                return True
        return False
    except Exception as e:
        logger.error(f"⚠️ Ошибка обновления материала ID {material_id}: {e}")
        return False
    
async def add_quantity_to_material_in_db(
    material_id: int,
    amount: float,
    performed_by: Optional[str] = None,
    description: Optional[str] = None
):
        
    """Увеличивает количество материала на складе"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            try:
                await db.execute("BEGIN")

                async with db.execute(
                    "SELECT quantity FROM materials WHERE id = ?",
                    (material_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        await db.rollback()
                        return None

                    current_quantity = row[0] if row[0] is not None else 0

                new_quantity = current_quantity + amount

                await db.execute(
                    "UPDATE materials SET quantity = ? WHERE id = ?",
                    (new_quantity, material_id)
                )
                await log_material_history_entry(
                    db,
                    material_id,
                    amount,
                    'Пополнение',
                    performed_by or 'Система',
                    description or 'Пополнение запаса'
                )
                await db.commit()
                logger.info(
                    f"📦 Увеличено количество материала ID: {material_id} на {amount}. Новый остаток: {new_quantity}"
                )
                return new_quantity
            except Exception as inner_error:
                await db.rollback()
                logger.error(
                    f"⚠️ Ошибка при увеличении количества материала ID {material_id}: {inner_error}"
                )
                return None
    except Exception as e:
        logger.error(f"⚠️ Ошибка соединения при увеличении количества материала ID {material_id}: {e}")
        return None

async def delete_material_from_db(material_id: int):
    """Удаляет материал"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            try:
                await db.execute("BEGIN")
                await db.execute("DELETE FROM work_materials WHERE material_id = ?", (material_id,))
                cursor = await db.execute("DELETE FROM materials WHERE id = ?", (material_id,))
                await db.commit()
                if cursor.rowcount and cursor.rowcount > 0:
                    logger.info(f"🗑️ Удален материал ID: {material_id}")
                    return True
            except Exception as inner_error:
                await db.rollback()
                logger.error(f"⚠️ Ошибка при удалении материала ID {material_id}: {inner_error}")
                return False
        return False
    except Exception as e:
        logger.error(f"⚠️ Ошибка удаления материала ID {material_id}: {e}")
        return False

async def delete_category_from_db(category_id: int):
    """Удаляет категорию из базы данных."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверяем, используются ли категории в работах
            async with db.execute(
                "SELECT COUNT(*) FROM works WHERE category = (SELECT name FROM categories WHERE id = ?)", 
                (category_id,)
            ) as cursor:
                usage_count = await cursor.fetchone()
                if usage_count and usage_count[0] > 0:
                    return False, "Нельзя удалить категорию, которая используется в работах"
            
            await db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            await db.commit()
            if db.rowcount > 0:
                logger.info(f"🗑️ Удалена категория ID: {category_id}")
                return True, "Категория успешно удалена"
        return False, "Категория не найдена"
    except Exception as e:
        logger.error(f"⚠️ Ошибка удаления категории ID {category_id}: {e}")
        return False, f"Ошибка удаления: {str(e)}"

# ========== ФУНКЦИИ ДЛЯ ОТЧЕТОВ ==========
async def get_reports_for_date_from_db(target_date: str):
    """Получает отчеты за конкретную дату из базы данных."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('''
                SELECT wr.quantity, w.name, w.category, w.unit, f.first_name, f.last_name
                FROM work_reports wr
                JOIN works w ON wr.work_id = w.id
                JOIN foremen f ON wr.foreman_id = f.id
                WHERE wr.report_date = ?
            ''', (target_date,)) as cursor:
                rows = await cursor.fetchall()

            grouped_reports = {}
            for quantity, work_name, category, unit, full_name, position in rows:
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

            reports = []
            for foreman, info in grouped_reports.items():
                reports.append({
                    'foreman': foreman,
                    'position': info.get('position'),
                    'works': info['works']                })
            logger.info(f"📊 Найдено отчетов за {target_date}: {len(reports)} бригадиров")
            return reports
    except Exception as e:
        logger.error(f"❌ Ошибка получения отчетов за дату {target_date}: {e}")
        return []

async def get_all_reports_from_db(date_filter=None):
    """Получает все отчеты из базы данных с возможностью фильтрации по дате."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            query = '''
                SELECT wr.id, wr.foreman_id, wr.work_id, wr.quantity,
                       wr.report_date, wr.report_time, wr.photo_report_url,
                       f.first_name as foreman_full_name,
                       f.last_name as foreman_position,
                       w.name as work_name, w.unit
                FROM work_reports wr
                LEFT JOIN foremen f ON wr.foreman_id = f.id
                LEFT JOIN works w ON wr.work_id = w.id
            '''
            params = ()
            
            if date_filter:
                query += ' WHERE wr.report_date = ?'
                params = (date_filter,)
                
            query += ' ORDER BY wr.report_date DESC, wr.report_time DESC'
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                reports = []
                for row in rows:
                    (report_id, foreman_id, work_id, quantity, report_date,
                     report_time, photo_url, foreman_full_name, foreman_position, work_name, unit) = row
                    reports.append({
                        'id': report_id,
                        'foreman_id': foreman_id,
                        'work_id': work_id,
                        'quantity': quantity,
                        'report_date': report_date,
                        'report_time': report_time,
                        'photo_report_url': photo_url,
                        'foreman_name': foreman_full_name,
                        'foreman_position': foreman_position,
                        'work_name': work_name,
                        'unit': unit
                    })
                logger.info(f"📋 Загружено отчетов: {len(reports)}")
                return reports
    except Exception as e:
        logger.error(f"❌ Ошибка получения всех отчетов: {e}")
        return []

async def get_report_by_id(report_id: int):
    """Получает конкретный отчет по ID."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('''
                SELECT wr.id, wr.foreman_id, wr.work_id, wr.quantity,
                       wr.report_date, wr.report_time, wr.photo_report_url,
                       f.first_name as foreman_full_name,
                        f.last_name as foreman_position,
                       w.name as work_name, w.unit
                FROM work_reports wr
                LEFT JOIN foremen f ON wr.foreman_id = f.id
                LEFT JOIN works w ON wr.work_id = w.id
                WHERE wr.id = ?
            ''', (report_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    (report_id, foreman_id, work_id, quantity, report_date,
                     report_time, photo_url, foreman_full_name, foreman_position, work_name, unit) = row
                    return {
                        'id': report_id,
                        'foreman_id': foreman_id,
                        'work_id': work_id,
                        'quantity': quantity,
                        'report_date': report_date,
                        'report_time': report_time,
                        'photo_report_url': photo_url,
                        'foreman_name': foreman_full_name,
                        'foreman_position': foreman_position,
                        'work_name': work_name,
                        'unit': unit
                    }
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка получения отчета по ID {report_id}: {e}")
        return None

async def update_report_in_db(report_id: int, report_data: dict):
    """Обновляет отчет в базе данных."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Получаем старые данные отчета для восстановления баланса
            async with db.execute(
                "SELECT work_id, quantity FROM work_reports WHERE id = ?", 
                (report_id,)
            ) as cursor:
                old_row = await cursor.fetchone()
                if not old_row:
                    return False, "Отчет не найден"
                
                old_work_id, old_quantity = old_row
            
            # Восстанавливаем старый баланс
            await db.execute(
                "UPDATE works SET balance = balance + ? WHERE id = ?",
                (old_quantity, old_work_id)
            )
            
            # Проверяем новый баланс
            async with db.execute(
                "SELECT balance FROM works WHERE id = ?", 
                (report_data['work_id'],)
            ) as cursor:
                new_balance_row = await cursor.fetchone()
                if not new_balance_row:
                    await db.rollback()
                    return False, "Новая работа не найдена"
                
                new_balance = new_balance_row[0]
                if new_balance < report_data['quantity']:
                    await db.rollback()
                    return False, "Недостаточно материалов на балансе для новой работы"
            
            # Вычитаем новое количество из баланса
            await db.execute(
                "UPDATE works SET balance = balance - ? WHERE id = ?",
                (report_data['quantity'], report_data['work_id'])
            )
            
            # Обновляем отчет
            await db.execute(
                '''UPDATE work_reports 
                   SET work_id = ?, quantity = ?, report_date = ?, 
                       report_time = ?, photo_report_url = ? 
                   WHERE id = ?''',
                (report_data['work_id'], report_data['quantity'], 
                 report_data['report_date'], report_data['report_time'],
                 report_data.get('photo_report_url', ''), report_id)
            )
            
            await db.commit()
            logger.info(f"📝 Обновлен отчет ID: {report_id}")
            return True, "Отчет успешно обновлен"
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Ошибка обновления отчета ID {report_id}: {e}")
        return False, f"Ошибка обновления: {str(e)}"

async def delete_report_from_db(report_id: int):
    """Удаляет отчет из базы данных и восстанавливает баланс."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            try:
                await db.execute("BEGIN")

                # Получаем данные отчета для восстановления баланса
                async with db.execute(
                    "SELECT work_id, quantity, foreman_id FROM work_reports WHERE id = ?",
                    (report_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        return False, "Отчет не найден"

                    work_id, quantity, foreman_id = row

                foreman_display = await get_foreman_display_name(db, foreman_id)
                deletion_display = f"{foreman_display} (удаление отчета ID {report_id})"

                # Восстанавливаем баланс работы
                await db.execute(
                    "UPDATE works SET balance = balance + ? WHERE id = ?",
                    (quantity, work_id)
                )

                # Возвращаем материалы на склад
                requirements = await fetch_work_materials_requirements(db, work_id)
                for requirement in requirements:
                    total_to_restore = requirement['quantity_per_unit'] * quantity
                    if total_to_restore <= 0:
                        continue
                    await db.execute(
                        "UPDATE materials SET quantity = quantity + ? WHERE id = ?",
                        (total_to_restore, requirement['material_id'])
                    )
                    await log_material_history_entry(
                        db,
                        requirement['material_id'],
                        total_to_restore,
                        'Возврат',
                        deletion_display,
                        f"Возврат при удалении отчета работы ID {report_id}"
                    )

                # Удаляем отчет
                await db.execute("DELETE FROM work_reports WHERE id = ?", (report_id,))
                await db.commit()

                logger.info(f"🗑️ Удален отчет ID: {report_id}")
                return True, "Отчет успешно удален"
            except Exception as e:
                await db.rollback()
                raise e
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Ошибка удаления отчета ID {report_id}: {e}")
        return False, f"Ошибка удаления: {str(e)}"

async def get_all_work_reports_from_db():
    """Получает все отчеты о работах для вкладки отчетов."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('''
                SELECT id, foreman_id, work_id, quantity, report_date, report_time, photo_report_url
                FROM work_reports 
                ORDER BY report_date DESC, report_time DESC
            ''') as cursor:
                rows = await cursor.fetchall()
                reports = []
                for row in rows:
                    (report_id, foreman_id, work_id, quantity, report_date, 
                     report_time, photo_url) = row
                    reports.append({
                        'id': report_id,
                        'foreman_id': foreman_id,
                        'work_id': work_id,
                        'quantity': quantity,
                        'report_date': report_date,
                        'report_time': report_time,
                        'photo_report_url': photo_url
                    })
                return reports
    except Exception as e:
        logger.error(f"❌ Ошибка получения всех отчетов: {e}")
        return []

async def create_work_report_in_db(report_data: dict):
    """Создает новый отчет о работе."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            try:
                await db.execute("BEGIN")

                foreman_display = await get_foreman_display_name(db, report_data.get('foreman_id'))

                # Проверяем баланс работы
                async with db.execute(
                    "SELECT balance FROM works WHERE id = ?",
                    (report_data['work_id'],)
                ) as cursor:
                    balance_row = await cursor.fetchone()
                    if not balance_row:
                        await db.rollback()
                        return False, "Работа не найдена"

                    balance = balance_row[0]
                    if balance < report_data['quantity']:
                        await db.rollback()
                        return False, "Недостаточно материалов на балансе"

                # Проверяем наличие материалов на складе
                materials_requirements = await fetch_work_materials_requirements(db, report_data['work_id'])
                for requirement in materials_requirements:
                    total_required = requirement['quantity_per_unit'] * report_data['quantity']
                    if total_required <= 0:
                        continue
                    if requirement['available_quantity'] < total_required:
                        await db.rollback()
                        return False, (
                            f"Недостаточно материала \"{requirement['material_name']}\" на складе"
                        )

                # Создаем отчет и получаем его ID
                cursor = await db.execute(
                    '''INSERT INTO work_reports
                       (foreman_id, work_id, quantity, report_date, report_time, photo_report_url)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (report_data['foreman_id'], report_data['work_id'], report_data['quantity'],
                     report_data['report_date'], report_data['report_time'],
                     report_data.get('photo_report_url', ''))
                )
                report_id = cursor.lastrowid


                # Вычитаем из баланса работы
                await db.execute(
                    "UPDATE works SET balance = balance - ? WHERE id = ?",
                    (report_data['quantity'], report_data['work_id'])
                )

                # Вычитаем материалы со склада
                for requirement in materials_requirements:
                    total_required = requirement['quantity_per_unit'] * report_data['quantity']
                    if total_required <= 0:
                        continue
                    await db.execute(
                        "UPDATE materials SET quantity = quantity - ? WHERE id = ?",
                        (total_required, requirement['material_id'])
                    )

                    await log_material_history_entry(
                        db,
                        requirement['material_id'],
                        -total_required,
                        'Списание',
                        foreman_display,
                        f"Списание по отчету работы ID {report_id}"
                    )

                
                await db.commit()
                logger.info(f"📊 Создан отчет ID: {report_id}")
                return True, report_id
            except Exception as e:
                await db.rollback()
                raise e
    except Exception as e:
        logger.error(f"❌ Ошибка создания отчета: {e}")
        return False, f"Ошибка создания: {str(e)}"

async def update_work_report_in_db(report_id: int, report_data: dict):
    """Обновляет отчет о работе."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            try:
                await db.execute("BEGIN")

                # Получаем старые данные
                async with db.execute(
                    "SELECT work_id, quantity, foreman_id FROM work_reports WHERE id = ?",
                    (report_id,)
                ) as cursor:
                    old_row = await cursor.fetchone()
                    if not old_row:
                        await db.rollback()
                        return False, "Отчет не найден"

                    old_work_id, old_quantity, old_foreman_id = old_row

                new_foreman_display = await get_foreman_display_name(db, report_data.get('foreman_id'))
                old_foreman_display = await get_foreman_display_name(db, old_foreman_id)
                correction_display = f"{old_foreman_display} (коррекция отчета ID {report_id})"

                # Восстанавливаем старый баланс работы
                await db.execute(
                    "UPDATE works SET balance = balance + ? WHERE id = ?",
                    (old_quantity, old_work_id)
                )

                # Восстанавливаем материалы на складе
                old_requirements = await fetch_work_materials_requirements(db, old_work_id)
                for requirement in old_requirements:
                    total_to_restore = requirement['quantity_per_unit'] * old_quantity
                    if total_to_restore <= 0:
                        continue
                    await db.execute(
                        "UPDATE materials SET quantity = quantity + ? WHERE id = ?",
                        (total_to_restore, requirement['material_id'])
                    )
                    await log_material_history_entry(
                        db,
                        requirement['material_id'],
                        total_to_restore,
                        'Возврат',
                        correction_display,
                        f"Возврат при редактировании отчета работы ID {report_id}"
                    )

                # Проверяем новый баланс работы
                async with db.execute(
                    "SELECT balance FROM works WHERE id = ?",
                    (report_data['work_id'],)
                ) as cursor:
                    new_balance_row = await cursor.fetchone()
                    if not new_balance_row:
                        await db.rollback()
                        return False, "Новая работа не найдена"

                    new_balance = new_balance_row[0]
                    if new_balance < report_data['quantity']:
                        await db.rollback()
                        return False, "Недостаточно материалов на балансе для новой работы"

                # Проверяем наличие материалов на складе для новой работы
                new_requirements = await fetch_work_materials_requirements(db, report_data['work_id'])
                for requirement in new_requirements:
                    total_required = requirement['quantity_per_unit'] * report_data['quantity']
                    if total_required <= 0:
                        continue
                    if requirement['available_quantity'] < total_required:
                        await db.rollback()
                        return False, (
                            f"Недостаточно материала \"{requirement['material_name']}\" на складе"
                        )

                # Вычитаем новое количество из баланса работы
                await db.execute(
                    "UPDATE works SET balance = balance - ? WHERE id = ?",
                    (report_data['quantity'], report_data['work_id'])
                )

                # Вычитаем материалы со склада
                for requirement in new_requirements:
                    total_required = requirement['quantity_per_unit'] * report_data['quantity']
                    if total_required <= 0:
                        continue
                    await db.execute(
                        "UPDATE materials SET quantity = quantity - ? WHERE id = ?",
                        (total_required, requirement['material_id'])
                    )
                    await log_material_history_entry(
                        db,
                        requirement['material_id'],
                        -total_required,
                        'Списание',
                        new_foreman_display,
                        f"Списание по обновленному отчету работы ID {report_id}"
                    )

                # Обновляем отчет
                await db.execute(
                    '''UPDATE work_reports
                       SET foreman_id = ?, work_id = ?, quantity = ?,
                           report_date = ?, report_time = ?, photo_report_url = ?
                       WHERE id = ?''',
                    (report_data['foreman_id'], report_data['work_id'], report_data['quantity'],
                     report_data['report_date'], report_data['report_time'],
                     report_data.get('photo_report_url', ''), report_id)
                )

                await db.commit()
                logger.info(f"📊 Обновлен отчет ID: {report_id}")
                return True, "Отчет успешно обновлен"
            except Exception as e:
                await db.rollback()
                raise e
    except Exception as e:
        logger.error(f"❌ Ошибка обновления отчета ID {report_id}: {e}")
        return False, f"Ошибка обновления: {str(e)}"

# ========== ЭНДПОИНТЫ API ==========
@app.get("/")
def read_root():
    return {"message": "StroyKontrol API", "version": "1.0.0"}

# Таблица пользователей сайта
async def init_site_users_table():
    """Создает таблицу для пользователей сайта"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS site_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_date TEXT NOT NULL,
                last_login TEXT
            )
        ''')
        await db.commit()

# Инициализируем таблицу при запуске
@app.on_event("startup")
async def startup_event():
    await init_site_users_table()
    await init_categories_table()
    await init_materials_table()
    await init_work_materials_table()
    await init_material_history_table()


@app.get("/api/works/export")
async def export_works():
    """Экспорт работ в Excel файл"""
    try:
        works = await get_all_works_from_db()
        
        # Создаем новую книгу Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "Работы"
        
        # Заголовки
        headers = ["ID", "Название работы", "Категория", "Единица измерения", "На балансе", "Проект", "Активна"]
        ws.append(headers)
        
        # Данные
        for work in works:
            row = [
                work['id'],
                work['Название работы'],
                work['Категория'],
                work['Единица измерения'],
                work['На балансе'],
                work['Проект'],
                "Да" if work['is_active'] else "Нет"
            ]
            ws.append(row)
        
        # Сохраняем в байтовый поток
        file_stream = io.BytesIO()
        wb.save(file_stream)
        file_stream.seek(0)
        
        # Возвращаем файл
        return StreamingResponse(
            file_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=works_export.xlsx"}
        )
    except Exception as e:
        logger.error(f"❌ Ошибка экспорта работ: {e}")
        raise HTTPException(status_code=500, detail="Ошибка экспорта работ")

# Импорт/экспорт       

@app.post("/api/works/import")
async def import_works(file: UploadFile = File(...)):
    """Импорт работ из Excel файла"""
    try:
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Поддерживаются только файлы Excel (.xlsx, .xls)")
        
        # Читаем файл
        contents = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(contents))
        ws = wb.active
        
        imported_count = 0
        updated_count = 0
        errors = []
        
        # Пропускаем заголовок (первая строка)
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not any(row):  # Пропускаем пустые строки
                continue
                
            try:
                work_id, name, category, unit, balance, project_total, is_active_str = row
                
                # Валидация обязательных полей
                if not name or not category or not unit:
                    errors.append(f"Пропущены обязательные поля в строке: {row}")
                    continue
                
                # Преобразуем данные
                work_data = {
                    'name': str(name).strip(),
                    'category': str(category).strip(),
                    'unit': str(unit).strip(),
                    'balance': float(balance) if balance else 0,
                    'project_total': float(project_total) if project_total else 0,
                    'is_active': 1 if str(is_active_str).lower() in ['да', 'yes', 'true', '1'] else 0
                }
                
                if work_id and await get_work_by_id(int(work_id)):
                    # Обновляем существующую работу
                    success = await update_work_in_db(int(work_id), work_data)
                    if success:
                        updated_count += 1
                    else:
                        errors.append(f"Ошибка обновления работы ID {work_id}")
                else:
                    # Создаем новую работу
                    new_id = await insert_work_to_db(work_data)
                    if new_id:
                        imported_count += 1
                    else:
                        errors.append(f"Ошибка создания работы: {work_data['name']}")
                        
            except Exception as e:
                errors.append(f"Ошибка обработки строки {row}: {str(e)}")
        
        return {
            "success": True,
            "message": f"Импорт завершен. Добавлено: {imported_count}, обновлено: {updated_count}",
            "errors": errors,
            "imported_count": imported_count,
            "updated_count": updated_count,
            "error_count": len(errors)
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка импорта работ: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка импорта работ: {str(e)}")


@app.get("/api/materials/export")
async def export_materials():
    """Экспорт материалов в Excel файл"""
    try:
        materials = await get_all_materials_from_db()

        wb = Workbook()
        ws = wb.active
        ws.title = "Материалы"

        headers = ["ID", "Категория", "Название материала", "Единица измерения", "Количество"]
        ws.append(headers)

        for material in materials:
            row = [
                material['id'],
                material['category'],
                material['name'],
                material['unit'],
                material['quantity']
            ]
            ws.append(row)

        file_stream = io.BytesIO()
        wb.save(file_stream)
        file_stream.seek(0)

        return StreamingResponse(
            file_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=materials_export.xlsx"}
        )
    except Exception as e:
        logger.error(f"❌ Ошибка экспорта материалов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка экспорта материалов")


@app.get("/api/materials/template")
async def download_materials_template():
    """Скачивание шаблона Excel для материалов"""
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Материалы"

        headers = ["ID", "Категория", "Название материала", "Единица измерения", "Количество"]
        ws.append(headers)
        ws.append(["", "Категория", "Пример материала", "шт", 0])

        file_stream = io.BytesIO()
        wb.save(file_stream)
        file_stream.seek(0)

        return StreamingResponse(
            file_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=materials_template.xlsx"}
        )
    except Exception as e:
        logger.error(f"❌ Ошибка формирования шаблона материалов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка формирования шаблона")


@app.post("/api/materials/import")
async def import_materials(file: UploadFile = File(...)):
    """Импорт материалов из Excel"""
    try:
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Поддерживаются только файлы Excel (.xlsx, .xls)")

        contents = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(contents))
        ws = wb.active

        imported_count = 0
        updated_count = 0
        errors = []

        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not any(row):
                continue

            try:
                material_id, category, name, unit, quantity = row

                if not category or not name or not unit:
                    errors.append(f"Пропущены обязательные поля в строке: {row}")
                    continue

                material_payload = {
                    'category': str(category).strip(),
                    'name': str(name).strip(),
                    'unit': str(unit).strip(),
                    'quantity': float(quantity) if quantity is not None else 0
                }

                if material_id:
                    existing_material = await get_material_by_id(int(material_id))
                    if existing_material:
                        success = await update_material_in_db(int(material_id), material_payload)
                        if success:
                            updated_count += 1
                        else:
                            errors.append(f"Ошибка обновления материала ID {material_id}")
                        continue

                await insert_material_to_db(material_payload)
                imported_count += 1

            except Exception as exc:
                errors.append(f"Ошибка обработки строки {row}: {str(exc)}")

        return {
            "success": True,
            "message": f"Импорт завершен. Добавлено: {imported_count}, обновлено: {updated_count}",
            "errors": errors,
            "imported_count": imported_count,
            "updated_count": updated_count,
            "error_count": len(errors)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка импорта материалов: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка импорта материалов: {str(e)}")

# Эндпоинты аутентификации

@app.post("/api/site-login")
@app.post("//api/site-login")
async def login_site_user(request: Request):
    """Аутентификация пользователя сайта"""
    try:
        login_data = await request.json()
        logger.info(f"🔐 Попытка входа: username={login_data.get('username')}")
        
        required_fields = ["username", "password"]
        for field in required_fields:
            if field not in login_data:
                logger.error(f"❌ Отсутствует поле: {field}")
                raise HTTPException(status_code=400, detail=f"Отсутствует поле: {field}")
        
        password_hash = hash_password(login_data['password'])
        logger.info(f"🔐 Хэш пароля: {password_hash}")
        
        async with aiosqlite.connect(DB_PATH) as db:
            logger.info(f"🔍 Поиск пользователя в БД: {login_data['username']}")
            
            async with db.execute(
                "SELECT id, username, role, is_active FROM site_users WHERE username = ? AND password_hash = ? AND is_active = 1",
                (login_data['username'], password_hash)
            ) as cursor:
                user = await cursor.fetchone()
                logger.info(f"🔍 Результат запроса: {user}")
                
                if user:
                    user_id, username, role, is_active = user
                    logger.info(f"✅ Успешный вход: {username} (id={user_id})")
                    
                    # Обновляем время последнего входа
                    await db.execute(
                        "UPDATE site_users SET last_login = ? WHERE id = ?",
                        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id)
                    )
                    await db.commit()
                    
                    return {
                        "success": True, 
                        "message": "Успешный вход",
                        "user": {
                            "id": user_id,
                            "username": username,
                            "role": role
                        }
                    }
                else:
                    logger.error(f"❌ Неверные учетные данные: username={login_data['username']}")
                    raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")
                    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка входа: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Ошибка входа")
                    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка входа: {e}")
        raise HTTPException(status_code=500, detail="Ошибка входа")

# ========== ЭНДПОИНТЫ ДЛЯ КАТЕГОРИЙ ==========
@app.get("/api/categories")
async def get_categories():
    """Получает все категории."""
    categories = await get_categories_from_db()
    return {"success": True, "data": categories}

@app.post("/api/categories")
async def create_category(request: Request):
    """Создает новую категорию."""
    try:
        category_data = await request.json()
        
        if 'name' not in category_data or not category_data['name'].strip():
            raise HTTPException(status_code=400, detail="Отсутствует название категории")
        
        category_id = await create_category_in_db(category_data)
        if category_id is not None:
            return {"success": True, "message": "Категория успешно добавлена", "data": {"id": category_id}}
        else:
            raise HTTPException(status_code=500, detail="Ошибка при добавлении категории в БД")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка при создании категории: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@app.delete("/api/categories/{category_id}")
async def delete_category(category_id: int):
    """Удаляет категорию."""
    success, message = await delete_category_from_db(category_id)
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)

# Обновляем функцию startup_event для инициализации таблицы категорий
@app.on_event("startup")
async def startup_event():
    await init_site_users_table()
    await init_categories_table()
    await init_materials_table()
    await init_work_materials_table()


# Эндпоинты для работ

@app.get("/api/all-works")
async def get_all_works():
    """Получает ВСЕ работы (для сайта)."""
    works = await get_all_works_from_db()
    return {"success": True, "data": works}

@app.get("/api/works")
async def get_works():
    works = await get_active_works_from_db()
    return {"success": True, "data": works}

@app.get("/api/works/{work_id}")
async def get_work(work_id: int):
    work = await get_work_by_id(work_id)
    if work is None:
        raise HTTPException(status_code=404, detail="Работа не найдена")
    return {"success": True, "data": work}

@app.post("/api/works")
async def create_work(request: Request):
    try:
        work_data = await request.json()
        logger.info(f"DEBUG: create_work получил данные: {work_data}")

        # Валидация данных
        required_fields = ["name", "category", "unit", "balance", "is_active"]
        for field in required_fields:
            if field not in work_data:
                raise HTTPException(status_code=400, detail=f"Отсутствует поле: {field}")
        if not isinstance(work_data['is_active'], int) or work_data['is_active'] not in [0, 1]:
             raise HTTPException(status_code=400, detail="is_active должно быть 0 или 1")
        if not isinstance(work_data['balance'], int) or work_data['balance'] < 0:
             raise HTTPException(status_code=400, detail="balance должно быть числом >= 0")

        # Добавляем project_total по умолчанию, если не указан
        if 'project_total' not in work_data:
            work_data['project_total'] = 0

        work_id = await insert_work_to_db(work_data)
        if work_id is not None:
            created_work = await get_work_by_id(work_id)
            return {"success": True, "message": "Работа успешно добавлена", "data": created_work}
        else:
            raise HTTPException(status_code=500, detail="Ошибка при добавлении работы в БД")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Неверный формат JSON")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка при создании работы: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@app.put("/api/works/{work_id}")
async def update_work(work_id: int, request: Request):
     # Проверяем, существует ли работа
    existing_work = await get_work_by_id(work_id)
    if existing_work is None:
        raise HTTPException(status_code=404, detail="Работа не найдена для обновления")
    try:
        work_data = await request.json()
        # Валидация данных
        required_fields = ["name", "category", "unit", "balance", "is_active"]
        for field in required_fields:
            if field not in work_data:
                raise HTTPException(status_code=400, detail=f"Отсутствует поле: {field}")
        if not isinstance(work_data['is_active'], int) or work_data['is_active'] not in [0, 1]:
             raise HTTPException(status_code=400, detail="is_active должно быть 0 или 1")
        if not isinstance(work_data['balance'], (int, float)) or work_data['balance'] < 0:
             raise HTTPException(status_code=400, detail="balance должно быть числом >= 0")

        # Добавляем project_total по умолчанию, если не указан
        if 'project_total' not in work_data:
            work_data['project_total'] = 0

        success = await update_work_in_db(work_id, work_data)
        if success:
            updated_work = await get_work_by_id(work_id)
            return {"success": True, "message": "Работа успешно обновлена", "data": updated_work}
        else:
            raise HTTPException(status_code=500, detail="Ошибка при обновлении работы в БД")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Неверный формат JSON")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении работы ID {work_id}: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@app.put("/api/works/{work_id}/add-balance")
async def add_work_balance(work_id: int, request: Request):
    existing_work = await get_work_by_id(work_id)
    if existing_work is None:
        raise HTTPException(status_code=404, detail="Работа не найдена")

    try:
        payload = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Неверный формат JSON")

    if 'amount' not in payload:
        raise HTTPException(status_code=400, detail="Отсутствует поле: amount")

    try:
        amount = float(payload['amount'])
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="amount должно быть числом")

    if amount <= 0:
        raise HTTPException(status_code=400, detail="amount должно быть больше 0")

    new_balance = await add_balance_to_work_in_db(work_id, amount)
    if new_balance is None:
        raise HTTPException(status_code=500, detail="Не удалось обновить баланс работы")

    existing_work['На балансе'] = new_balance
    existing_work['balance'] = new_balance

    return {
        "success": True,
        "message": "Баланс работы успешно обновлен",
        "data": existing_work
    }

@app.delete("/api/works/{work_id}")
async def delete_work(work_id: int):
    # Проверяем, существует ли работа
    existing_work = await get_work_by_id(work_id)
    if existing_work is None:
        raise HTTPException(status_code=404, detail="Работа не найдена для удаления")

    success = await delete_work_from_db(work_id)
    if success:
        return {"success": True, "message": "Работа успешно удалена"}
    else:
        raise HTTPException(status_code=500, detail="Ошибка при удалении работы из БД")


@app.get("/api/works/{work_id}/materials")
async def get_work_materials(work_id: int):
    work = await get_work_by_id(work_id)
    if work is None:
        raise HTTPException(status_code=404, detail="Работа не найдена")

    materials_for_work = await get_work_materials_from_db(work_id)
    return {"success": True, "data": materials_for_work}

@app.put("/api/works/{work_id}/materials")
async def update_work_materials(work_id: int, request: Request):
    work = await get_work_by_id(work_id)
    if work is None:
        raise HTTPException(status_code=404, detail="Работа не найдена")

    try:
        payload = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Неверный формат JSON")

    if isinstance(payload, dict) and 'materials' in payload:
        materials_list = payload['materials']
    elif isinstance(payload, list):
        materials_list = payload
    elif payload is None:
        materials_list = []
    else:
        raise HTTPException(status_code=400, detail="Некорректный формат данных")

    normalized_materials = []
    seen_ids = set()

    for item in materials_list:
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail="Элемент материалов должен быть объектом")
        if 'material_id' not in item or 'quantity_per_unit' not in item:
            raise HTTPException(status_code=400, detail="Отсутствуют обязательные поля")

        try:
            material_id = int(item['material_id'])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="material_id должен быть целым числом")

        try:
            quantity_per_unit = float(item['quantity_per_unit'])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="quantity_per_unit должен быть числом")

        if material_id <= 0:
            raise HTTPException(status_code=400, detail="material_id должен быть положительным")
        if quantity_per_unit < 0:
            raise HTTPException(status_code=400, detail="Количество не может быть отрицательным")
        if material_id in seen_ids:
            raise HTTPException(status_code=400, detail="Материал не может повторяться")

        material = await get_material_by_id(material_id)
        if material is None:
            raise HTTPException(status_code=404, detail=f"Материал ID {material_id} не найден")

        seen_ids.add(material_id)

        if quantity_per_unit == 0:
            continue

        normalized_materials.append({
            'material_id': material_id,
            'quantity_per_unit': quantity_per_unit
        })

    success, error_message = await replace_work_materials_for_work(work_id, normalized_materials)
    if not success:
        raise HTTPException(status_code=400, detail=error_message or "Не удалось сохранить материалы")

    updated_materials = await get_work_materials_from_db(work_id)
    return {
        "success": True,
        "message": "Материалы для работы обновлены",
        "data": updated_materials
    }

# Эндпоинты для материалов склада
@app.get("/api/materials")
async def get_materials():
    materials = await get_all_materials_from_db()
    return {"success": True, "data": materials}

@app.get("/api/materials/history")
async def get_material_history(limit: int = 500):
    history = await get_material_history_from_db(limit)
    return {"success": True, "data": history}

@app.get("/api/materials/{material_id}")
async def get_material(material_id: int):
    material = await get_material_by_id(material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Материал не найден")
    return {"success": True, "data": material}


@app.post("/api/materials")
async def create_material(request: Request):
    try:
        material_data = await request.json()
        performed_by = material_data.pop('performed_by', None)
        performed_by = material_data.pop('performed_by', None)

        required_fields = ["name", "category", "unit", "quantity"]
        for field in required_fields:
            if field not in material_data or (isinstance(material_data[field], str) and not material_data[field].strip()):
                raise HTTPException(status_code=400, detail=f"Отсутствует поле: {field}")

        try:
            material_data['quantity'] = float(material_data['quantity'])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="quantity должно быть числом")

        if material_data['quantity'] < 0:
            raise HTTPException(status_code=400, detail="quantity должно быть >= 0")

        material_id = await insert_material_to_db(material_data, performed_by or 'Система')
        created_material = await get_material_by_id(material_id)
        return {"success": True, "message": "Материал успешно добавлен", "data": created_material}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка при создании материала: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@app.put("/api/materials/{material_id}/add-quantity")
async def add_material_quantity_endpoint(material_id: int, request: Request):
    material = await get_material_by_id(material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Материал не найден")

    try:
        payload = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Неверный формат JSON")

    if 'amount' not in payload:
        raise HTTPException(status_code=400, detail="Отсутствует поле: amount")

    try:
        amount = float(payload['amount'])
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="amount должно быть числом")

    if amount <= 0:
        raise HTTPException(status_code=400, detail="amount должно быть больше 0")

    performed_by = payload.get('performed_by')
    description = payload.get('description')

    new_quantity = await add_quantity_to_material_in_db(
        material_id,
        amount,
        performed_by or 'Система',
        description
    )
    if new_quantity is None:
        raise HTTPException(status_code=500, detail="Не удалось обновить количество материала")

    material['quantity'] = new_quantity

    return {
        "success": True,
        "message": "Количество материала успешно обновлено",
        "data": material
    }

@app.put("/api/materials/{material_id}")
async def update_material(material_id: int, request: Request):
    existing_material = await get_material_by_id(material_id)
    if existing_material is None:
        raise HTTPException(status_code=404, detail="Материал не найден для обновления")

    try:
        material_data = await request.json()

        required_fields = ["name", "category", "unit", "quantity"]
        for field in required_fields:
            if field not in material_data or (isinstance(material_data[field], str) and not material_data[field].strip()):
                raise HTTPException(status_code=400, detail=f"Отсутствует поле: {field}")

        try:
            material_data['quantity'] = float(material_data['quantity'])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="quantity должно быть числом")

        if material_data['quantity'] < 0:
            raise HTTPException(status_code=400, detail="quantity должно быть >= 0")

        success = await update_material_in_db(material_id, material_data, performed_by or 'Система')
        if success:
            updated_material = await get_material_by_id(material_id)
            return {"success": True, "message": "Материал успешно обновлен", "data": updated_material}
        else:
            raise HTTPException(status_code=500, detail="Ошибка при обновлении материала в БД")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении материала ID {material_id}: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@app.delete("/api/materials/{material_id}")
async def delete_material(material_id: int):
    existing_material = await get_material_by_id(material_id)
    if existing_material is None:
        raise HTTPException(status_code=404, detail="Материал не найден для удаления")

    success = await delete_material_from_db(material_id)
    if success:
        return {"success": True, "message": "Материал успешно удален"}
    else:
        raise HTTPException(status_code=500, detail="Ошибка при удалении материала из БД")

# Эндпоинты для бригадиров
@app.get("/api/foremen")
async def get_foremen():
    foremen = await get_foremen_from_db()
    return {"success": True, "data": foremen}

@app.post("/api/foremen")
async def create_foreman(request: Request):
    """Создает нового бригадира."""
    try:
        foreman_data = await request.json()

        # Поддержка старых названий полей
        if 'full_name' not in foreman_data and 'first_name' in foreman_data:
            foreman_data['full_name'] = foreman_data['first_name']
        if 'position' not in foreman_data and 'last_name' in foreman_data:
            foreman_data['position'] = foreman_data['last_name']
        
        # Валидация
        required_fields = ["full_name", "position"]
        for field in required_fields:
            if field not in foreman_data:
                raise HTTPException(status_code=400, detail=f"Отсутствует поле: {field}")
        
        foreman_id = await create_foreman_in_db(foreman_data)
        if foreman_id is not None:
            return {"success": True, "message": "Бригадир успешно добавлен", "data": {"id": foreman_id}}
        else:
            raise HTTPException(status_code=500, detail="Ошибка при добавлении бригадира в БД")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Неверный формат JSON")
    except Exception as e:
        logger.error(f"❌ Ошибка при создании бригадира: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

# В эндпоинте update_foreman добавим поддержку is_active
@app.put("/api/foremen/{foreman_id}")
async def update_foreman(foreman_id: int, request: Request):
    """Обновляет данные бригадира."""
    try:
        foreman_data = await request.json()

        # Поддержка старых названий полей
        if 'full_name' not in foreman_data and 'first_name' in foreman_data:
            foreman_data['full_name'] = foreman_data['first_name']
        if 'position' not in foreman_data and 'last_name' in foreman_data:
            foreman_data['position'] = foreman_data['last_name']
        
        # Валидация
        required_fields = ["full_name", "position"]
        for field in required_fields:
            if field not in foreman_data:
                raise HTTPException(status_code=400, detail=f"Отсутствует поле: {field}")
        
        if 'is_active' in foreman_data:
            is_active_value = foreman_data['is_active']
            if isinstance(is_active_value, bool):
                is_active_value = int(is_active_value)
            if not isinstance(is_active_value, int):
                raise HTTPException(status_code=400, detail="is_active должно быть числом 0 или 1")
            if is_active_value not in [0, 1]:
                raise HTTPException(status_code=400, detail="is_active должно быть 0 или 1")
            foreman_data['is_active'] = is_active_value
        
        success = await update_foreman_in_db(foreman_id, foreman_data)
        if success:
            return {"success": True, "message": "Бригадир успешно обновлен"}
        else:
            raise HTTPException(status_code=500, detail="Ошибка при обновлении бригадира в БД")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Неверный формат JSON")
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении бригадира: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@app.delete("/api/foremen/{foreman_id}")
async def delete_foreman(foreman_id: int):
    """Удаляет бригадира."""
    success, message = await delete_foreman_from_db(foreman_id)
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)

# Эндпоинты для отчетов
@app.get("/api/reports/{date}")
async def get_reports(date: str):
    # Проверка формата даты
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты. Ожидается YYYY-MM-DD")

    reports = await get_reports_for_date_from_db(date)
    return {"success": True, "data": reports}

@app.get("/api/all-reports")
async def get_all_reports(date: Optional[str] = None):
    """Получает все отчеты с возможностью фильтрации по дате."""
    reports = await get_all_reports_from_db(date)
    return {"success": True, "data": reports}

@app.get("/api/report/{report_id}")
async def get_report(report_id: int):
    """Получает конкретный отчет по ID."""
    report = await get_report_by_id(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Отчет не найден")
    return {"success": True, "data": report}

@app.put("/api/report/{report_id}")
async def update_report(report_id: int, request: Request):
    """Обновляет существующий отчет."""
    # Проверяем, существует ли отчет
    existing_report = await get_report_by_id(report_id)
    if existing_report is None:
        raise HTTPException(status_code=404, detail="Отчет не найден")
    
    try:
        report_data = await request.json()
        
        # Валидация данных
        required_fields = ["work_id", "quantity", "report_date", "report_time"]
        for field in required_fields:
            if field not in report_data:
                raise HTTPException(status_code=400, detail=f"Отсутствует поле: {field}")
        
        if not isinstance(report_data['work_id'], int) or report_data['work_id'] <= 0:
            raise HTTPException(status_code=400, detail="work_id должен быть положительным целым числом")
        
        if not isinstance(report_data['quantity'], (int, float)) or report_data['quantity'] <= 0:
            raise HTTPException(status_code=400, detail="quantity должен быть положительным числом")
        
        success, message = await update_report_in_db(report_id, report_data)
        if success:
            updated_report = await get_report_by_id(report_id)
            return {"success": True, "message": message, "data": updated_report}
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Неверный формат JSON")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении отчета ID {report_id}: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@app.delete("/api/report/{report_id}")
async def delete_report(report_id: int):
    """Удаляет отчет."""
    # Проверяем, существует ли отчет
    existing_report = await get_report_by_id(report_id)
    if existing_report is None:
        raise HTTPException(status_code=404, detail="Отчет не найден")
    
    success, message = await delete_report_from_db(report_id)
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)


# Накопительная ведомость
@app.get("/api/accumulative-statement")
async def get_accumulative_statement():
    """Получает накопительную ведомость выполненных работ."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Суммируем все выполненные работы из отчетов
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
                return {"success": True, "data": accumulative_data}
    except Exception as e:
        logger.error(f"❌ Ошибка получения накопительной ведомости: {e}")
        return {"success": False, "error": str(e)}

# Новые эндпоинты для работы с отчетами (work-reports)
@app.get("/api/work-reports")
async def get_work_reports():
    """Получает все отчеты о работах."""
    reports = await get_all_work_reports_from_db()
    return {"success": True, "data": reports}

@app.post("/api/work-reports")
async def create_work_report(request: Request):
    """Создает новый отчет о работе."""
    try:
        report_data = await request.json()
        
        # Валидация
        required_fields = ["foreman_id", "work_id", "quantity", "report_date", "report_time"]
        for field in required_fields:
            if field not in report_data:
                raise HTTPException(status_code=400, detail=f"Отсутствует поле: {field}")
        
        success, result = await create_work_report_in_db(report_data)
        if success:
            return {"success": True, "message": "Отчет успешно создан", "data": {"id": result}}
        else:
            raise HTTPException(status_code=400, detail=result)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Неверный формат JSON")
    except Exception as e:
        logger.error(f"❌ Ошибка при создании отчета: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@app.put("/api/work-reports/{report_id}")
async def update_work_report(report_id: int, request: Request):
    """Обновляет отчет о работе."""
    try:
        report_data = await request.json()
        
        # Валидация
        required_fields = ["foreman_id", "work_id", "quantity", "report_date", "report_time"]
        for field in required_fields:
            if field not in report_data:
                raise HTTPException(status_code=400, detail=f"Отсутствует поле: {field}")
        
        success, message = await update_work_report_in_db(report_id, report_data)
        if success:
            return {"success": True, "message": message}
        else:
            raise HTTPException(status_code=400, detail=message)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Неверный формат JSON")
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении отчета: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

# ========== ЗАПУСК СЕРВЕРА ==========
if __name__ == "__main__":
    import uvicorn
    logger.info(f"🚀 Запуск API сервера на {API_HOST}:{API_PORT}")
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info")