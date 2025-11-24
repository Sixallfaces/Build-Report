"""API Router for Authentication."""
import logging
import hashlib
from datetime import datetime

from fastapi import APIRouter, HTTPException

from apps.database import get_db
from apps.models.auth import LoginRequest, LoginResponse, UserResponse

logger = logging.getLogger('auth_router')
router = APIRouter(prefix="/api", tags=["auth"])


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


@router.post("/site-login", response_model=LoginResponse)
async def site_login(credentials: LoginRequest):
    """Authenticate a user for the web panel."""
    async with get_db() as db:
        async with db.execute(
            """SELECT id, username, password_hash, role, is_active, created_date, last_login
               FROM site_users WHERE username = ?""",
            (credentials.username,)
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            logger.warning(f"Login attempt for non-existent user: {credentials.username}")
            return LoginResponse(
                success=False,
                message="Неверное имя пользователя или пароль",
                user=None
            )

        if not row['is_active']:
            logger.warning(f"Login attempt for inactive user: {credentials.username}")
            return LoginResponse(
                success=False,
                message="Учетная запись деактивирована",
                user=None
            )

        password_hash = hash_password(credentials.password)
        if password_hash != row['password_hash']:
            logger.warning(f"Invalid password for user: {credentials.username}")
            return LoginResponse(
                success=False,
                message="Неверное имя пользователя или пароль",
                user=None
            )

        # Update last login
        await db.execute(
            "UPDATE site_users SET last_login = ? WHERE id = ?",
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), row['id'])
        )
        await db.commit()

        logger.info(f"User logged in: {credentials.username}")

        return LoginResponse(
            success=True,
            message="Успешный вход",
            user=UserResponse(
                id=row['id'],
                username=row['username'],
                role=row['role'],
                is_active=bool(row['is_active']),
                created_date=row['created_date'],
                last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
        )


@router.post("/create-admin")
async def create_admin(username: str, password: str):
    """Create an admin user (for initial setup only)."""
    async with get_db() as db:
        # Check if any admin exists
        async with db.execute(
            "SELECT COUNT(*) as cnt FROM site_users WHERE role = 'admin'"
        ) as cursor:
            row = await cursor.fetchone()
            if row and row['cnt'] > 0:
                raise HTTPException(400, "Admin user already exists")

        try:
            cursor = await db.execute(
                """INSERT INTO site_users (username, password_hash, role, is_active, created_date)
                   VALUES (?, ?, 'admin', 1, ?)""",
                (username, hash_password(password), datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            await db.commit()
            logger.info(f"Created admin user: {username}")
            return {"message": f"Admin user '{username}' created successfully"}
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                raise HTTPException(400, "Username already exists")
            raise HTTPException(500, str(e))
