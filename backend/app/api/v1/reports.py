import os
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.models import Report, ReportExport, ReportHistory
from app.schemas.schemas import ReportGenerateRequest, ReportResponse
from app.services.report_generator import (
    fetch_report_data,
    generate_csv_report,
    generate_excel_report,
    generate_pdf_report
)
from app.api.v1.ws import ws_manager

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("", response_model=List[ReportResponse])
async def list_reports(db: AsyncSession = Depends(get_db)):
    stmt = select(Report).order_by(Report.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/generate", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(req: ReportGenerateRequest, db: AsyncSession = Depends(get_db)):
    filters_json = json.dumps(req.filters) if req.filters else None

    # Initial Report Record
    db_report = Report(
        name=req.name,
        report_type=req.report_type,
        generated_by="usr_admin",
        date_range=req.date_range,
        filters=filters_json,
        export_format=req.export_format,
        status="processing",
        schedule=req.schedule
    )
    db.add(db_report)
    await db.commit()
    await db.refresh(db_report)

    # Broadcast websocket start
    await ws_manager.broadcast({
        "event": "report_started",
        "data": {"report_id": db_report.id, "name": db_report.name, "status": "processing"}
    })

    try:
        # Fetch analytics strictly from PostgreSQL
        data = await fetch_report_data(req.report_type, req.date_range, req.filters or {}, db)

        filename = f"report_{db_report.id}_{req.export_format.lower()}"
        file_path = None

        if req.export_format.upper() == "CSV":
            file_path = generate_csv_report(filename, req.name, data)
        elif req.export_format.upper() in ["EXCEL", "XLSX"]:
            file_path = generate_excel_report(filename, req.name, data)
        else:  # Default PDF
            file_path = generate_pdf_report(filename, req.name, data)

        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

        # Update Report Record
        db_report.status = "completed"
        db_report.file_location = file_path

        # Add Export & History records
        export_rec = ReportExport(
            report_id=db_report.id,
            export_format=req.export_format,
            file_path=file_path,
            file_size=file_size
        )
        history_rec = ReportHistory(
            report_id=db_report.id,
            action="generate",
            status="completed"
        )
        db.add(export_rec)
        db.add(history_rec)

        await db.commit()
        await db.refresh(db_report)

        # Broadcast completed
        await ws_manager.broadcast({
            "event": "report_completed",
            "data": {
                "report_id": db_report.id,
                "name": db_report.name,
                "status": "completed",
                "file_location": file_path
            }
        })

        return db_report

    except Exception as e:
        db_report.status = "failed"
        history_rec = ReportHistory(
            report_id=db_report.id,
            action="generate",
            status="failed"
        )
        db.add(history_rec)
        await db.commit()

        await ws_manager.broadcast({
            "event": "report_failed",
            "data": {"report_id": db_report.id, "error": str(e)}
        })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}"
        )

@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Report).where(Report.id == report_id)
    res = await db.execute(stmt)
    report = res.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@router.get("/download/{report_id}")
async def download_report(report_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Report).where(Report.id == report_id)
    res = await db.execute(stmt)
    report = res.scalar_one_or_none()
    if not report or not report.file_location or not os.path.exists(report.file_location):
        raise HTTPException(status_code=404, detail="Report file not found or not yet generated")

    media_type = "application/pdf"
    if report.export_format.upper() == "CSV":
        media_type = "text/csv"
    elif report.export_format.upper() in ["EXCEL", "XLSX"]:
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    filename = f"{report.name.replace(' ', '_')}.{report.export_format.lower()}"
    return FileResponse(path=report.file_location, media_type=media_type, filename=filename)

@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(report_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Report).where(Report.id == report_id)
    res = await db.execute(stmt)
    report = res.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.file_location and os.path.exists(report.file_location):
        try:
            os.remove(report.file_location)
        except Exception:
            pass

    await db.delete(report)
    await db.commit()
    return None
