"""API Router for Work Reports."""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from apps.database import get_db
from apps.config import settings
from apps.models.report import (
    ReportCreate, ReportUpdate, ReportResponse,
    ReportVerify, DailyReportSummary, AccumulativeStatementEntry
)
from apps.services.yandex_disk import yandex_disk_service

logger = logging.getLogger('reports_router')
router = APIRouter(prefix="/api", tags=["reports"])

VAT_MULTIPLIER = 1 + settings.VAT_RATE


def _report_row_to_response(row) -> dict:
    """Convert database row to response dict."""
    return {
        'id': row['id'],
        'foreman_id': row['foreman_id'],
        'work_id': row['work_id'],
        'quantity': row['quantity'],
        'report_date': row['report_date'],
        'report_time': row['report_time'],
        'photo_report_url': row['photo_report_url'],
        'is_verified': bool(row['is_verified']),
        'work_name': row.get('work_name') or row.get('wname'),
        'work_category': row.get('work_category') or row.get('wcategory'),
        'work_unit': row.get('work_unit') or row.get('wunit'),
        'foreman_name': row.get('foreman_name') or row.get('fname'),
        'foreman_position': row.get('foreman_position') or row.get('fposition'),
    }


@router.get("/reports/{date}", response_model=List[DailyReportSummary])
async def get_reports_for_date(date: str):
    """Get all reports for a specific date."""
    async with get_db() as db:
        async with db.execute("""
            SELECT wr.quantity, wr.photo_report_url, w.name as work_name,
                   w.category, w.unit, f.first_name, f.last_name
            FROM work_reports wr
            JOIN works w ON wr.work_id = w.id
            JOIN foremen f ON wr.foreman_id = f.id
            WHERE wr.report_date = ?
            ORDER BY f.first_name, w.name
        """, (date,)) as cursor:
            rows = await cursor.fetchall()

        # Group by foreman
        grouped = {}
        for row in rows:
            foreman_name = row['first_name']
            if foreman_name not in grouped:
                grouped[foreman_name] = {
                    'foreman': foreman_name,
                    'position': row['last_name'],
                    'works': []
                }
            grouped[foreman_name]['works'].append({
                'name': row['work_name'],
                'quantity': row['quantity'],
                'unit': row['unit']
            })

        return list(grouped.values())


@router.get("/all-reports", response_model=List[dict])
async def get_all_reports(
    foreman_id: Optional[int] = Query(None),
    work_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    verified_only: bool = Query(False),
    limit: int = Query(500, le=1000)
):
    """Get all reports with optional filters."""
    async with get_db() as db:
        query = """
            SELECT wr.id, wr.foreman_id, wr.work_id, wr.quantity,
                   wr.report_date, wr.report_time, wr.photo_report_url, wr.is_verified,
                   w.name as wname, w.category as wcategory, w.unit as wunit,
                   f.first_name as fname, f.last_name as fposition
            FROM work_reports wr
            JOIN works w ON wr.work_id = w.id
            JOIN foremen f ON wr.foreman_id = f.id
            WHERE 1=1
        """
        params = []

        if foreman_id is not None:
            query += " AND wr.foreman_id = ?"
            params.append(foreman_id)
        if work_id is not None:
            query += " AND wr.work_id = ?"
            params.append(work_id)
        if date_from:
            query += " AND wr.report_date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND wr.report_date <= ?"
            params.append(date_to)
        if verified_only:
            query += " AND wr.is_verified = 1"

        query += " ORDER BY wr.report_date DESC, wr.report_time DESC LIMIT ?"
        params.append(limit)

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [_report_row_to_response(row) for row in rows]


@router.get("/work-reports", response_model=List[dict])
async def get_work_reports(limit: int = Query(500, le=1000)):
    """Get all work reports."""
    return await get_all_reports(limit=limit)


@router.get("/report/{report_id}", response_model=dict)
async def get_report(report_id: int):
    """Get a specific report by ID."""
    async with get_db() as db:
        async with db.execute("""
            SELECT wr.id, wr.foreman_id, wr.work_id, wr.quantity,
                   wr.report_date, wr.report_time, wr.photo_report_url, wr.is_verified,
                   w.name as wname, w.category as wcategory, w.unit as wunit,
                   f.first_name as fname, f.last_name as fposition
            FROM work_reports wr
            JOIN works w ON wr.work_id = w.id
            JOIN foremen f ON wr.foreman_id = f.id
            WHERE wr.id = ?
        """, (report_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(404, "Report not found")
            return _report_row_to_response(row)


@router.post("/work-reports", response_model=dict)
async def create_report(report: ReportCreate):
    """Create a new work report."""
    async with get_db() as db:
        # Validate foreman exists
        async with db.execute("SELECT id FROM foremen WHERE id = ?", (report.foreman_id,)) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(400, "Foreman not found")

        # Validate work exists
        async with db.execute("SELECT id FROM works WHERE id = ?", (report.work_id,)) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(400, "Work not found")

        now = datetime.now()
        cursor = await db.execute("""
            INSERT INTO work_reports (foreman_id, work_id, quantity, report_date, report_time, photo_report_url, is_verified)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (report.foreman_id, report.work_id, report.quantity,
              now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'),
              report.photo_report_url or ''))
        await db.commit()

        report_id = cursor.lastrowid
        logger.info(f"Created report ID: {report_id}")
        return await get_report(report_id)


@router.put("/report/{report_id}", response_model=dict)
@router.put("/work-reports/{report_id}", response_model=dict)
async def update_report(report_id: int, report: ReportUpdate):
    """Update an existing report."""
    async with get_db() as db:
        # Check if exists
        async with db.execute("SELECT id FROM work_reports WHERE id = ?", (report_id,)) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(404, "Report not found")

        update_fields = []
        values = []

        if report.quantity is not None:
            update_fields.append("quantity = ?")
            values.append(report.quantity)
        if report.photo_report_url is not None:
            update_fields.append("photo_report_url = ?")
            values.append(report.photo_report_url)
        if report.is_verified is not None:
            update_fields.append("is_verified = ?")
            values.append(int(report.is_verified))

        if not update_fields:
            raise HTTPException(400, "No fields to update")

        values.append(report_id)
        query = f"UPDATE work_reports SET {', '.join(update_fields)} WHERE id = ?"

        await db.execute(query, values)
        await db.commit()
        logger.info(f"Updated report ID: {report_id}")
        return await get_report(report_id)


@router.post("/report/{report_id}/verify", response_model=dict)
async def verify_report(report_id: int, data: ReportVerify):
    """Toggle report verification status."""
    async with get_db() as db:
        async with db.execute("SELECT id FROM work_reports WHERE id = ?", (report_id,)) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(404, "Report not found")

        await db.execute(
            "UPDATE work_reports SET is_verified = ? WHERE id = ?",
            (int(data.is_verified), report_id)
        )
        await db.commit()
        logger.info(f"Report {report_id} verification set to {data.is_verified}")
        return await get_report(report_id)


@router.delete("/report/{report_id}")
async def delete_report(report_id: int):
    """Delete a report."""
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM work_reports WHERE id = ?", (report_id,))
        await db.commit()

        if cursor.rowcount == 0:
            raise HTTPException(404, "Report not found")

        logger.info(f"Deleted report ID: {report_id}")
        return {"message": "Report deleted successfully"}


@router.get("/accumulative-statement", response_model=List[dict])
async def get_accumulative_statement(foreman_id: Optional[int] = Query(None)):
    """Get accumulative statement of verified works."""
    async with get_db() as db:
        query = """
            SELECT
                w.category AS category,
                w.name AS work_name,
                w.unit AS unit,
                COALESCE(w.unit_cost_without_vat, 0) AS unit_cost,
                SUM(wr.quantity) AS quantity,
                COALESCE(w.project_total, 0) AS project_total,
                CASE
                    WHEN COALESCE(w.project_total, 0) > 0
                    THEN ROUND((SUM(wr.quantity) / w.project_total) * 100, 2)
                    ELSE 0
                END AS completion_percentage,
                SUM(wr.quantity * COALESCE(w.unit_cost_without_vat, 0)) AS total_cost
            FROM work_reports wr
            JOIN works w ON wr.work_id = w.id
            WHERE wr.is_verified = 1
        """
        params = []

        if foreman_id is not None:
            query += " AND wr.foreman_id = ?"
            params.append(foreman_id)

        query += """
            GROUP BY w.category, w.name, w.unit, w.project_total, w.unit_cost_without_vat
            ORDER BY w.category, w.name
        """

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    'Раздел': row['category'],
                    'Работа': row['work_name'],
                    'Единица измерения': row['unit'],
                    'Стоимость за единицу': row['unit_cost'] or 0,
                    'Количество': row['quantity'],
                    'Проект': row['project_total'] or 0,
                    '%Выполнения': row['completion_percentage'] or 0,
                    'Сумма': round(row['total_cost'] or 0, 2),
                }
                for row in rows
            ]
