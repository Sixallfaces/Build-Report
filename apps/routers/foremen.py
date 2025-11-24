"""API Router for Foremen."""
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException

from apps.database import get_db
from apps.models.foreman import (
    ForemanCreate, ForemanUpdate, ForemanResponse,
    ForemanSectionUpdate, ForemanSectionResponse
)

logger = logging.getLogger('foremen_router')
router = APIRouter(prefix="/api/foremen", tags=["foremen"])


def _foreman_row_to_response(row) -> dict:
    """Convert database row to response dict."""
    return {
        'id': row['id'],
        'full_name': row['first_name'],
        'position': row['last_name'] or '',
        'first_name': row['first_name'],
        'last_name': row['last_name'] or '',
        'username': row['username'],
        'registration_date': row['registration_date'],
        'is_active': bool(row['is_active']) if 'is_active' in row.keys() else True,
    }


@router.get("", response_model=List[dict])
async def get_foremen():
    """Get all foremen."""
    async with get_db() as db:
        async with db.execute("""
            SELECT id, first_name, last_name, username, registration_date, is_active
            FROM foremen
            ORDER BY first_name
        """) as cursor:
            rows = await cursor.fetchall()
            return [_foreman_row_to_response(row) for row in rows]


@router.get("/{foreman_id}", response_model=dict)
async def get_foreman(foreman_id: int):
    """Get a specific foreman by ID."""
    async with get_db() as db:
        async with db.execute("""
            SELECT id, first_name, last_name, username, registration_date, is_active
            FROM foremen WHERE id = ?
        """, (foreman_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(404, "Foreman not found")
            return _foreman_row_to_response(row)


@router.post("", response_model=dict)
async def create_foreman(foreman: ForemanCreate):
    """Create a new foreman."""
    async with get_db() as db:
        cursor = await db.execute("""
            INSERT INTO foremen (first_name, last_name, username, registration_date, is_active)
            VALUES (?, ?, ?, ?, ?)
        """, (foreman.full_name, foreman.position, foreman.username or '',
              datetime.now().strftime('%Y-%m-%d %H:%M:%S'), int(foreman.is_active)))
        await db.commit()

        foreman_id = cursor.lastrowid
        logger.info(f"Created foreman: {foreman.full_name} (ID: {foreman_id})")
        return await get_foreman(foreman_id)


@router.put("/{foreman_id}", response_model=dict)
async def update_foreman(foreman_id: int, foreman: ForemanUpdate):
    """Update an existing foreman."""
    async with get_db() as db:
        # Check if exists
        async with db.execute(
            "SELECT first_name, last_name, username, is_active FROM foremen WHERE id = ?",
            (foreman_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(404, "Foreman not found")

        update_fields = []
        values = []

        if foreman.full_name is not None:
            update_fields.append("first_name = ?")
            values.append(foreman.full_name)
        if foreman.position is not None:
            update_fields.append("last_name = ?")
            values.append(foreman.position)
        if foreman.username is not None:
            update_fields.append("username = ?")
            values.append(foreman.username)
        if foreman.is_active is not None:
            update_fields.append("is_active = ?")
            values.append(int(foreman.is_active))

        if not update_fields:
            raise HTTPException(400, "No fields to update")

        values.append(foreman_id)
        query = f"UPDATE foremen SET {', '.join(update_fields)} WHERE id = ?"

        await db.execute(query, values)
        await db.commit()
        logger.info(f"Updated foreman ID: {foreman_id}")
        return await get_foreman(foreman_id)


@router.delete("/{foreman_id}")
async def delete_foreman(foreman_id: int):
    """Delete a foreman."""
    async with get_db() as db:
        # Check if foreman has reports
        async with db.execute(
            "SELECT COUNT(*) as cnt FROM work_reports WHERE foreman_id = ?",
            (foreman_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row['cnt'] > 0:
                raise HTTPException(
                    400,
                    f"Cannot delete foreman: {row['cnt']} reports are linked to this foreman"
                )

        # Delete from foreman_sections
        await db.execute("DELETE FROM foreman_sections WHERE foreman_id = ?", (foreman_id,))

        cursor = await db.execute("DELETE FROM foremen WHERE id = ?", (foreman_id,))
        await db.commit()

        if cursor.rowcount == 0:
            raise HTTPException(404, "Foreman not found")

        logger.info(f"Deleted foreman ID: {foreman_id}")
        return {"message": "Foreman deleted successfully"}


@router.get("/{foreman_id}/sections", response_model=List[ForemanSectionResponse])
async def get_foreman_sections(foreman_id: int):
    """Get sections assigned to a foreman."""
    async with get_db() as db:
        # Check if foreman exists
        async with db.execute("SELECT id FROM foremen WHERE id = ?", (foreman_id,)) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(404, "Foreman not found")

        async with db.execute("""
            SELECT c.id, c.name
            FROM foreman_sections fs
            JOIN categories c ON fs.category_id = c.id
            WHERE fs.foreman_id = ?
            ORDER BY c.name
        """, (foreman_id,)) as cursor:
            rows = await cursor.fetchall()
            return [
                ForemanSectionResponse(id=row['id'], name=row['name'])
                for row in rows
            ]


@router.put("/{foreman_id}/sections", response_model=List[ForemanSectionResponse])
async def update_foreman_sections(foreman_id: int, data: ForemanSectionUpdate):
    """Update sections assigned to a foreman."""
    async with get_db() as db:
        # Check if foreman exists
        async with db.execute("SELECT id FROM foremen WHERE id = ?", (foreman_id,)) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(404, "Foreman not found")

        # Validate category IDs
        if data.category_ids:
            placeholders = ",".join(["?"] * len(data.category_ids))
            async with db.execute(
                f"SELECT id FROM categories WHERE id IN ({placeholders})",
                data.category_ids
            ) as cursor:
                existing = {row['id'] for row in await cursor.fetchall()}
                missing = [cid for cid in data.category_ids if cid not in existing]
                if missing:
                    raise HTTPException(
                        400,
                        f"Categories not found: {', '.join(map(str, missing))}"
                    )

        # Replace all sections
        await db.execute("DELETE FROM foreman_sections WHERE foreman_id = ?", (foreman_id,))

        for category_id in set(data.category_ids):  # Remove duplicates
            await db.execute(
                "INSERT INTO foreman_sections (foreman_id, category_id) VALUES (?, ?)",
                (foreman_id, category_id)
            )

        await db.commit()
        logger.info(f"Updated sections for foreman {foreman_id}")
        return await get_foreman_sections(foreman_id)
