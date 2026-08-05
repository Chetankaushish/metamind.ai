import httpx
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.models import Campaign as CampaignModel, OAuthToken, AuditLog
from app.schemas.schemas import (
    CampaignResponse, CampaignCreate, CampaignUpdate, BulkCampaignActionRequest,
    CampaignRenameRequest, CampaignBudgetActionRequest, CampaignAuditLogResponse
)
from sqlalchemy import or_, desc, asc
from app.core.config import settings
from app.core.security import decrypt_token
from app.api.v1.ws import ws_manager
from app.api.v1.dashboard import invalidate_dashboard_cache

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

META_GRAPH_URL = f"https://graph.facebook.com/{settings.META_GRAPH_API_VERSION}"

async def _get_access_token(db: AsyncSession) -> str:
    stmt = select(OAuthToken).where(OAuthToken.is_valid == True).order_by(OAuthToken.created_at.desc())
    res = await db.execute(stmt)
    tok = res.scalar_one_or_none()
    return decrypt_token(tok.encrypted_access_token) if tok else "EAAG_DUMMY_TOKEN"

async def _call_meta_api_update(campaign_id: str, payload: dict, access_token: str) -> bool:
    """Helper to post updates directly to Meta Marketing API."""
    url = f"{META_GRAPH_URL}/{campaign_id}"
    params = {"access_token": access_token}
    params.update(payload)
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url, params=params, timeout=10.0)
            return res.status_code == 200
    except Exception:
        return False

@router.get("", response_model=List[CampaignResponse])
async def list_campaigns(
    search: Optional[str] = None,
    status: Optional[str] = None,
    objective: Optional[str] = None,
    workspace_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(CampaignModel)

    conditions = []
    if search:
        search_fmt = f"%{search}%"
        conditions.append(or_(
            CampaignModel.name.ilike(search_fmt),
            CampaignModel.campaign_id.ilike(search_fmt)
        ))
    if status and status.upper() != "ALL":
        conditions.append(CampaignModel.status == status.upper())
    if objective and objective.upper() != "ALL":
        conditions.append(CampaignModel.objective == objective.upper())

    if conditions:
        stmt = stmt.where(*conditions)

    # Sorting
    sort_col = getattr(CampaignModel, sort_by, CampaignModel.created_at) if hasattr(CampaignModel, sort_by) else CampaignModel.created_at
    if sort_order and sort_order.lower() == "asc":
        stmt = stmt.order_by(asc(sort_col))
    else:
        stmt = stmt.order_by(desc(sort_col))

    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    campaigns = result.scalars().all()
    return campaigns

@router.get("/audit-logs", response_model=List[CampaignAuditLogResponse])
async def get_campaign_audit_logs(
    campaign_id: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(AuditLog)
    if campaign_id:
        stmt = stmt.where(AuditLog.campaign_id == campaign_id)
    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(CampaignModel).where(
        (CampaignModel.id == campaign_id) | (CampaignModel.campaign_id == campaign_id)
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign

@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(campaign_in: CampaignCreate, db: AsyncSession = Depends(get_db)):
    db_campaign = CampaignModel(
        campaign_id=campaign_in.campaign_id,
        name=campaign_in.name,
        status=campaign_in.status,
        objective=campaign_in.objective,
        buying_type=campaign_in.buying_type,
        daily_budget=campaign_in.daily_budget,
        lifetime_budget=campaign_in.lifetime_budget
    )
    db.add(db_campaign)
    
    # Audit log
    audit = AuditLog(
        user_id="usr_admin",
        campaign_id=campaign_in.campaign_id,
        action="create",
        new_value=f"Created {campaign_in.name}",
        result="SUCCESS"
    )
    db.add(audit)
    
    await db.commit()
    await db.refresh(db_campaign)
    
    invalidate_dashboard_cache()
    
    await ws_manager.broadcast({
        "event": "campaign_created",
        "data": {"campaign_id": db_campaign.campaign_id, "name": db_campaign.name}
    })
    
    return db_campaign

@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def patch_campaign(campaign_id: str, campaign_in: CampaignUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(CampaignModel).where(
        (CampaignModel.id == campaign_id) | (CampaignModel.campaign_id == campaign_id)
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    token = await _get_access_token(db)
    meta_payload = {}
    if campaign_in.name is not None:
        meta_payload["name"] = campaign_in.name
    if campaign_in.status is not None:
        meta_payload["status"] = campaign_in.status
    if campaign_in.daily_budget is not None:
        meta_payload["daily_budget"] = str(int(campaign_in.daily_budget * 100))

    if meta_payload:
        await _call_meta_api_update(campaign.campaign_id, meta_payload, token)

    old_val = f"Name: {campaign.name}, Status: {campaign.status}, Daily Budget: ${campaign.daily_budget}"

    if campaign_in.name is not None:
        campaign.name = campaign_in.name
    if campaign_in.status is not None:
        campaign.status = campaign_in.status
    if campaign_in.daily_budget is not None:
        campaign.daily_budget = campaign_in.daily_budget
    if campaign_in.lifetime_budget is not None:
        campaign.lifetime_budget = campaign_in.lifetime_budget

    new_val = f"Name: {campaign.name}, Status: {campaign.status}, Daily Budget: ${campaign.daily_budget}"

    audit = AuditLog(
        user_id="usr_admin",
        campaign_id=campaign.campaign_id,
        action="update",
        old_value=old_val,
        new_value=new_val,
        result="SUCCESS"
    )
    db.add(audit)

    await db.commit()
    await db.refresh(campaign)

    invalidate_dashboard_cache()

    await ws_manager.broadcast({
        "event": "campaign_updated",
        "data": {"campaign_id": campaign.campaign_id, "status": campaign.status, "name": campaign.name}
    })

    return campaign

@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
async def pause_campaign(campaign_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(CampaignModel).where(
        (CampaignModel.id == campaign_id) | (CampaignModel.campaign_id == campaign_id)
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    token = await _get_access_token(db)
    await _call_meta_api_update(campaign.campaign_id, {"status": "PAUSED"}, token)

    old_status = campaign.status
    campaign.status = "PAUSED"

    audit = AuditLog(
        user_id="usr_admin",
        campaign_id=campaign.campaign_id,
        action="pause",
        old_value=old_status,
        new_value="PAUSED",
        result="SUCCESS"
    )
    db.add(audit)

    await db.commit()
    await db.refresh(campaign)

    invalidate_dashboard_cache()

    await ws_manager.broadcast({
        "event": "campaign_paused",
        "data": {"campaign_id": campaign.campaign_id, "status": "PAUSED"}
    })

    return campaign

@router.post("/{campaign_id}/resume", response_model=CampaignResponse)
async def resume_campaign(campaign_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(CampaignModel).where(
        (CampaignModel.id == campaign_id) | (CampaignModel.campaign_id == campaign_id)
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    token = await _get_access_token(db)
    await _call_meta_api_update(campaign.campaign_id, {"status": "ACTIVE"}, token)

    old_status = campaign.status
    campaign.status = "ACTIVE"

    audit = AuditLog(
        user_id="usr_admin",
        campaign_id=campaign.campaign_id,
        action="resume",
        old_value=old_status,
        new_value="ACTIVE",
        result="SUCCESS"
    )
    db.add(audit)

    await db.commit()
    await db.refresh(campaign)

    invalidate_dashboard_cache()

    await ws_manager.broadcast({
        "event": "campaign_resumed",
        "data": {"campaign_id": campaign.campaign_id, "status": "ACTIVE"}
    })

    return campaign

@router.post("/{campaign_id}/duplicate", response_model=CampaignResponse)
async def duplicate_campaign(campaign_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(CampaignModel).where(
        (CampaignModel.id == campaign_id) | (CampaignModel.campaign_id == campaign_id)
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    new_cid = f"1202{uuid.uuid4().hex[:10]}"
    dup_campaign = CampaignModel(
        campaign_id=new_cid,
        name=f"{campaign.name} (Copy)",
        status="PAUSED",
        objective=campaign.objective,
        buying_type=campaign.buying_type,
        daily_budget=campaign.daily_budget,
        lifetime_budget=campaign.lifetime_budget,
        spend=0.0,
        revenue=0.0,
        roas=0.0,
        ctr=0.0,
        purchases=0
    )
    db.add(dup_campaign)

    audit = AuditLog(
        user_id="usr_admin",
        campaign_id=new_cid,
        action="duplicate",
        old_value=campaign.campaign_id,
        new_value=new_cid,
        result="SUCCESS"
    )
    db.add(audit)

    await db.commit()
    await db.refresh(dup_campaign)

    invalidate_dashboard_cache()

    await ws_manager.broadcast({
        "event": "campaign_created",
        "data": {"campaign_id": dup_campaign.campaign_id, "name": dup_campaign.name}
    })

    return dup_campaign

@router.post("/{campaign_id}/rename", response_model=CampaignResponse)
async def rename_campaign(campaign_id: str, req: CampaignRenameRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(CampaignModel).where(
        (CampaignModel.id == campaign_id) | (CampaignModel.campaign_id == campaign_id)
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    token = await _get_access_token(db)
    await _call_meta_api_update(campaign.campaign_id, {"name": req.name}, token)

    old_name = campaign.name
    campaign.name = req.name

    audit = AuditLog(
        user_id="usr_admin",
        campaign_id=campaign.campaign_id,
        action="rename",
        old_value=old_name,
        new_value=req.name,
        result="SUCCESS"
    )
    db.add(audit)

    await db.commit()
    await db.refresh(campaign)

    invalidate_dashboard_cache()

    await ws_manager.broadcast({
        "event": "campaign_updated",
        "data": {"campaign_id": campaign.campaign_id, "name": req.name}
    })

    return campaign

@router.post("/{campaign_id}/archive", response_model=CampaignResponse)
async def archive_campaign(campaign_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(CampaignModel).where(
        (CampaignModel.id == campaign_id) | (CampaignModel.campaign_id == campaign_id)
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    token = await _get_access_token(db)
    await _call_meta_api_update(campaign.campaign_id, {"status": "ARCHIVED"}, token)

    old_status = campaign.status
    campaign.status = "ARCHIVED"

    audit = AuditLog(
        user_id="usr_admin",
        campaign_id=campaign.campaign_id,
        action="archive",
        old_value=old_status,
        new_value="ARCHIVED",
        result="SUCCESS"
    )
    db.add(audit)

    await db.commit()
    await db.refresh(campaign)

    invalidate_dashboard_cache()

    await ws_manager.broadcast({
        "event": "campaign_archived",
        "data": {"campaign_id": campaign.campaign_id, "status": "ARCHIVED"}
    })

    return campaign

@router.post("/{campaign_id}/budget/increase", response_model=CampaignResponse)
async def increase_campaign_budget(campaign_id: str, req: CampaignBudgetActionRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(CampaignModel).where(
        (CampaignModel.id == campaign_id) | (CampaignModel.campaign_id == campaign_id)
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    old_budget = campaign.daily_budget or 100.0
    new_budget = old_budget

    if req.percentage is not None:
        new_budget = old_budget * (1 + req.percentage / 100.0)
    elif req.amount is not None:
        new_budget = old_budget + req.amount
    elif req.daily_budget is not None:
        new_budget = req.daily_budget

    new_budget = round(max(1.0, new_budget), 2)

    token = await _get_access_token(db)
    await _call_meta_api_update(campaign.campaign_id, {"daily_budget": str(int(new_budget * 100))}, token)

    campaign.daily_budget = new_budget

    audit = AuditLog(
        user_id="usr_admin",
        campaign_id=campaign.campaign_id,
        action="budget_increase",
        old_value=str(old_budget),
        new_value=str(new_budget),
        result="SUCCESS"
    )
    db.add(audit)

    await db.commit()
    await db.refresh(campaign)

    invalidate_dashboard_cache()

    await ws_manager.broadcast({
        "event": "campaign_updated",
        "data": {"campaign_id": campaign.campaign_id, "daily_budget": new_budget}
    })

    return campaign

@router.post("/{campaign_id}/budget/decrease", response_model=CampaignResponse)
async def decrease_campaign_budget(campaign_id: str, req: CampaignBudgetActionRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(CampaignModel).where(
        (CampaignModel.id == campaign_id) | (CampaignModel.campaign_id == campaign_id)
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    old_budget = campaign.daily_budget or 100.0
    new_budget = old_budget

    if req.percentage is not None:
        new_budget = old_budget * (1 - req.percentage / 100.0)
    elif req.amount is not None:
        new_budget = old_budget - req.amount
    elif req.daily_budget is not None:
        new_budget = req.daily_budget

    new_budget = round(max(1.0, new_budget), 2)

    token = await _get_access_token(db)
    await _call_meta_api_update(campaign.campaign_id, {"daily_budget": str(int(new_budget * 100))}, token)

    campaign.daily_budget = new_budget

    audit = AuditLog(
        user_id="usr_admin",
        campaign_id=campaign.campaign_id,
        action="budget_decrease",
        old_value=str(old_budget),
        new_value=str(new_budget),
        result="SUCCESS"
    )
    db.add(audit)

    await db.commit()
    await db.refresh(campaign)

    invalidate_dashboard_cache()

    await ws_manager.broadcast({
        "event": "campaign_updated",
        "data": {"campaign_id": campaign.campaign_id, "daily_budget": new_budget}
    })

    return campaign

@router.post("/{campaign_id}/budget/edit", response_model=CampaignResponse)
async def edit_campaign_budget(campaign_id: str, req: CampaignBudgetActionRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(CampaignModel).where(
        (CampaignModel.id == campaign_id) | (CampaignModel.campaign_id == campaign_id)
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    old_budget = campaign.daily_budget or 0.0
    new_budget = round(max(0.0, req.daily_budget or 0.0), 2)

    token = await _get_access_token(db)
    await _call_meta_api_update(campaign.campaign_id, {"daily_budget": str(int(new_budget * 100))}, token)

    campaign.daily_budget = new_budget

    audit = AuditLog(
        user_id="usr_admin",
        campaign_id=campaign.campaign_id,
        action="budget_edit",
        old_value=str(old_budget),
        new_value=str(new_budget),
        result="SUCCESS"
    )
    db.add(audit)

    await db.commit()
    await db.refresh(campaign)

    invalidate_dashboard_cache()

    await ws_manager.broadcast({
        "event": "campaign_updated",
        "data": {"campaign_id": campaign.campaign_id, "daily_budget": new_budget}
    })

    return campaign

@router.post("/bulk", status_code=status.HTTP_200_OK)
async def bulk_campaign_action(req: BulkCampaignActionRequest, db: AsyncSession = Depends(get_db)):
    token = await _get_access_token(db)
    updated_count = 0

    for cid in req.campaign_ids:
        stmt = select(CampaignModel).where(
            (CampaignModel.id == cid) | (CampaignModel.campaign_id == cid)
        )
        result = await db.execute(stmt)
        campaign = result.scalar_one_or_none()
        if not campaign:
            continue

        old_val = str(campaign.daily_budget) if "budget" in req.action else campaign.status

        if req.action == "pause":
            await _call_meta_api_update(campaign.campaign_id, {"status": "PAUSED"}, token)
            campaign.status = "PAUSED"
            new_val = "PAUSED"
            audit_action = "bulk_pause"
        elif req.action == "resume":
            await _call_meta_api_update(campaign.campaign_id, {"status": "ACTIVE"}, token)
            campaign.status = "ACTIVE"
            new_val = "ACTIVE"
            audit_action = "bulk_resume"
        elif req.action == "archive":
            await _call_meta_api_update(campaign.campaign_id, {"status": "ARCHIVED"}, token)
            campaign.status = "ARCHIVED"
            new_val = "ARCHIVED"
            audit_action = "bulk_archive"
        elif req.action == "update_budget" and req.daily_budget is not None:
            new_budget = round(req.daily_budget, 2)
            await _call_meta_api_update(
                campaign.campaign_id,
                {"daily_budget": str(int(new_budget * 100))},
                token
            )
            campaign.daily_budget = new_budget
            new_val = str(new_budget)
            audit_action = "bulk_budget_update"
        elif req.action == "increase_budget":
            pct = req.percentage or 10.0
            new_budget = round((campaign.daily_budget or 100.0) * (1 + pct / 100.0), 2)
            await _call_meta_api_update(
                campaign.campaign_id,
                {"daily_budget": str(int(new_budget * 100))},
                token
            )
            campaign.daily_budget = new_budget
            new_val = str(new_budget)
            audit_action = "bulk_budget_increase"
        elif req.action == "decrease_budget":
            pct = req.percentage or 10.0
            new_budget = round(max(1.0, (campaign.daily_budget or 100.0) * (1 - pct / 100.0)), 2)
            await _call_meta_api_update(
                campaign.campaign_id,
                {"daily_budget": str(int(new_budget * 100))},
                token
            )
            campaign.daily_budget = new_budget
            new_val = str(new_budget)
            audit_action = "bulk_budget_decrease"
        elif req.action == "delete":
            await db.delete(campaign)
            new_val = "DELETED"
            audit_action = "bulk_delete"
        else:
            continue

        audit = AuditLog(
            user_id="usr_admin",
            campaign_id=campaign.campaign_id,
            action=audit_action,
            old_value=old_val,
            new_value=new_val,
            result="SUCCESS"
        )
        db.add(audit)
        updated_count += 1

    await db.commit()
    invalidate_dashboard_cache()

    await ws_manager.broadcast({
        "event": "campaign_updated",
        "data": {"action": req.action, "count": updated_count}
    })

    return {"status": "success", "updated_records": updated_count}

@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(campaign_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(CampaignModel).where(
        (CampaignModel.id == campaign_id) | (CampaignModel.campaign_id == campaign_id)
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    cid = campaign.campaign_id
    await db.delete(campaign)

    audit = AuditLog(
        user_id="usr_admin",
        campaign_id=cid,
        action="delete",
        result="SUCCESS"
    )
    db.add(audit)

    await db.commit()
    invalidate_dashboard_cache()

    await ws_manager.broadcast({
        "event": "campaign_deleted",
        "data": {"campaign_id": cid}
    })
