"""API Router for Categories."""
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException

from apps.database import get_db
from apps.models.category import CategoryCreate, CategoryUpdate, CategoryResponse

logger = logging.getLogger('categories_router')
router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=List[CategoryResponse])
async def get_categories():
    """Get all categories."""
    async with get_db() as db:
        async with db.execute(
            "SELECT id, name, created_date FROM categories ORDER BY name"
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                CategoryResponse(
                    id=row['id'],
                    name=row['name'],
                    created_date=row['created_date']
                )
                for row in rows
            ]


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: int):
    """Get a specific category by ID."""
    async with get_db() as db:
        async with db.execute(
            "SELECT id, name, created_date FROM categories WHERE id = ?",
            (category_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(404, "Category not found")
            return CategoryResponse(
                id=row['id'],
                name=row['name'],
                created_date=row['created_date']
            )


@router.post("", response_model=CategoryResponse)
async def create_category(category: CategoryCreate):
    """Create a new category."""
    async with get_db() as db:
        try:
            cursor = await db.execute(
                "INSERT INTO categories (name, created_date) VALUES (?, ?)",
                (category.name.strip(), datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            await db.commit()
            category_id = cursor.lastrowid
            logger.info(f"Created category: {category.name} (ID: {category_id})")
            return await get_category(category_id)
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                raise HTTPException(400, "Category with this name already exists")
            raise HTTPException(500, str(e))


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(category_id: int, category: CategoryUpdate):
    """Update an existing category."""
    new_name = category.name.strip()

    async with get_db() as db:
        # Get current category
        async with db.execute(
            "SELECT name FROM categories WHERE id = ?",
            (category_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(404, "Category not found")
            current_name = row['name']

        if current_name == new_name:
            return await get_category(category_id)

        try:
            # Update category name
            await db.execute(
                "UPDATE categories SET name = ? WHERE id = ?",
                (new_name, category_id)
            )

            # Update references in works and materials
            await db.execute(
                "UPDATE works SET category = ? WHERE category = ?",
                (new_name, current_name)
            )
            await db.execute(
                "UPDATE materials SET category = ? WHERE category = ?",
                (new_name, current_name)
            )

            await db.commit()
            logger.info(f"Updated category ID {category_id}: '{current_name}' -> '{new_name}'")
            return await get_category(category_id)
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                raise HTTPException(400, "Category with this name already exists")
            raise HTTPException(500, str(e))


@router.delete("/{category_id}")
async def delete_category(category_id: int):
    """Delete a category."""
    async with get_db() as db:
        # Check if category is used
        async with db.execute(
            "SELECT COUNT(*) as cnt FROM works WHERE category = (SELECT name FROM categories WHERE id = ?)",
            (category_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row['cnt'] > 0:
                raise HTTPException(
                    400,
                    f"Cannot delete category: {row['cnt']} works are using this category"
                )

        # Delete foreman_sections references
        await db.execute("DELETE FROM foreman_sections WHERE category_id = ?", (category_id,))

        cursor = await db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        await db.commit()

        if cursor.rowcount == 0:
            raise HTTPException(404, "Category not found")

        logger.info(f"Deleted category ID: {category_id}")
        return {"message": "Category deleted successfully"}
