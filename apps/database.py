"""
Database module for Build-Report application.
Provides async SQLite connection and initialization functions.
"""
import aiosqlite
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from apps.config import settings

logger = logging.getLogger('database')


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    Async context manager for database connections.

    Usage:
        async with get_db() as db:
            async with db.execute("SELECT * FROM works") as cursor:
                rows = await cursor.fetchall()
    """
    db = await aiosqlite.connect(settings.DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_database():
    """Initialize all database tables."""
    async with get_db() as db:
        # Site users table
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

        # Foremen table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS foremen (
                id INTEGER PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                username TEXT,
                registration_date TEXT NOT NULL,
                yandex_folder_path TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            )
        ''')

        # Categories table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_date TEXT NOT NULL
            )
        ''')

        # Works table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS works (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                unit TEXT NOT NULL,
                balance REAL NOT NULL DEFAULT 0,
                project_total REAL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                unit_cost_without_vat REAL NOT NULL DEFAULT 0,
                total_cost_without_vat REAL NOT NULL DEFAULT 0
            )
        ''')

        # Work reports table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS work_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                foreman_id INTEGER NOT NULL,
                work_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                report_date TEXT NOT NULL,
                report_time TEXT NOT NULL,
                photo_report_url TEXT,
                is_verified INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (foreman_id) REFERENCES foremen (id),
                FOREIGN KEY (work_id) REFERENCES works (id)
            )
        ''')

        # Materials table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                unit TEXT NOT NULL,
                quantity REAL NOT NULL DEFAULT 0,
                unit_cost_without_vat REAL NOT NULL DEFAULT 0,
                total_cost_without_vat REAL NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
        ''')

        # Work materials (many-to-many relationship)
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

        # Material history table
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

        # Foreman sections (many-to-many relationship)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS foreman_sections (
                foreman_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                PRIMARY KEY (foreman_id, category_id),
                FOREIGN KEY (foreman_id) REFERENCES foremen(id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            )
        ''')

        await db.commit()
        logger.info("Database initialized successfully")


async def upgrade_database():
    """Add new columns to existing tables if needed."""
    async with get_db() as db:
        # Check and add columns to works table
        async with db.execute("PRAGMA table_info(works)") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]

        if 'project_total' not in columns:
            await db.execute('ALTER TABLE works ADD COLUMN project_total REAL DEFAULT 0')
            logger.info("Added project_total column to works table")

        if 'unit_cost_without_vat' not in columns:
            await db.execute('ALTER TABLE works ADD COLUMN unit_cost_without_vat REAL NOT NULL DEFAULT 0')
            logger.info("Added unit_cost_without_vat column to works table")

        if 'total_cost_without_vat' not in columns:
            await db.execute('ALTER TABLE works ADD COLUMN total_cost_without_vat REAL NOT NULL DEFAULT 0')
            logger.info("Added total_cost_without_vat column to works table")

        # Check and add columns to materials table
        async with db.execute("PRAGMA table_info(materials)") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]

        if 'is_active' not in columns:
            await db.execute('ALTER TABLE materials ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1')
            logger.info("Added is_active column to materials table")

        # Check and add columns to work_reports table
        async with db.execute("PRAGMA table_info(work_reports)") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]

        if 'is_verified' not in columns:
            await db.execute('ALTER TABLE work_reports ADD COLUMN is_verified INTEGER NOT NULL DEFAULT 0')
            logger.info("Added is_verified column to work_reports table")

        # Check and add columns to foremen table
        async with db.execute("PRAGMA table_info(foremen)") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]

        if 'is_active' not in columns:
            await db.execute('ALTER TABLE foremen ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1')
            logger.info("Added is_active column to foremen table")

        await db.commit()
        logger.info("Database upgrade completed")
