import httpx
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
    """Return the newest valid decrypted Meta access token.

    Never fall back to a dummy token. A missing/invalid token must fail
    explicitly so the application cannot accidentally operate on fake data.
    """
    stmt = (
        select(OAuthToken)
        .where(OAuthToken.is_valid.is_(True))
        .order_by(OAuthToken.created_at.desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    tok = res.scalar_one_or_none()

    if not tok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "No valid Meta access token found. "
                "Connect a Meta ad account before performing this action."
            ),
        )

    try:
        token = decrypt_token(tok.encrypted_access_token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to decrypt the stored Meta access token.",
        ) from exc

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Stored Meta access token is empty.",
        )

    return token

async def _call_meta_api_update(
    campaign_id: str,
    payload: dict,
    access_token: str,
) -> bool:
    """Update a campaign in Meta and fail loudly when Meta rejects the change."""
    if not campaign_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Meta campaign ID is required.",
        )

    url = f"{META_GRAPH_URL}/{campaign_id}"

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=5.0)
        ) as client:
            response = await client.post(
                url,
                params={
                    "access_token": access_token,
                    **payload,
                },
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Meta Graph API request timed out.",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Meta Graph API: {exc}",
        ) from exc

    if response.status_code < 200 or response.status_code >= 300:
        try:
            error_body = response.json()
        except ValueError:
            error_body = {"message": response.text[:500]}

        error = error_body.get("error", {}) if isinstance(error_body, dict) else {}
        message = error.get("message") or "Meta Graph API rejected the request."

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Meta API error: {message}",
        )

    return True

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

@router.post("", response_model=CampaignResponse, status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def create_campaign(
    campaign_in: CampaignCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Campaign creation is intentionally disabled until the real Meta campaign
    creation flow is configured.

    This prevents local-only campaign rows that do not exist in Meta Ads
    Manager and would later appear as real campaigns in the dashboard.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Campaign creation is disabled until the Meta campaign creation "
            "flow is configured for a connected ad account. No local-only "
            "campaign is created."
        ),
    )


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
        user_id=None,
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
        user_id=None,
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
        user_id=None,
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
async def duplicate_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Duplicate a campaign only through a real Meta campaign-creation flow.

    The previous implementation generated a synthetic campaign ID locally.
    That created records which did not exist in Meta and could later be
    mistaken for real campaigns. Until the Meta campaign-creation payload
    is explicitly implemented for the connected ad account, fail safely.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Campaign duplication is disabled until the Meta campaign "
            "creation flow is configured. No synthetic campaign is created."
        ),
    )


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
        user_id=None,
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
        user_id=None,
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

    old_budget = float(campaign.daily_budget or 0.0)
    new_budget = old_budget

    if req.percentage is not None:
        new_budget = old_budget * (1 + req.percentage / 100.0)
    elif req.amount is not None:
        new_budget = old_budget + req.amount
    elif req.daily_budget is not None:
        new_budget = req.daily_budget

    new_budget = round(max(0.0, new_budget), 2)

    token = await _get_access_token(db)
    await _call_meta_api_update(campaign.campaign_id, {"daily_budget": str(int(new_budget * 100))}, token)

    campaign.daily_budget = new_budget

    audit = AuditLog(
        user_id=None,
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

    old_budget = float(campaign.daily_budget or 0.0)
    new_budget = old_budget

    if req.percentage is not None:
        new_budget = old_budget * (1 - req.percentage / 100.0)
    elif req.amount is not None:
        new_budget = old_budget - req.amount
    elif req.daily_budget is not None:
        new_budget = req.daily_budget

    new_budget = round(max(0.0, new_budget), 2)

    token = await _get_access_token(db)
    await _call_meta_api_update(campaign.campaign_id, {"daily_budget": str(int(new_budget * 100))}, token)

    campaign.daily_budget = new_budget

    audit = AuditLog(
        user_id=None,
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
        user_id=None,
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
            pct = req.percentage
            if pct is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="percentage is required for increase_budget.",
                )
            new_budget = round((campaign.daily_budget or 0.0) * (1 + pct / 100.0), 2)
            await _call_meta_api_update(
                campaign.campaign_id,
                {"daily_budget": str(int(new_budget * 100))},
                token
            )
            campaign.daily_budget = new_budget
            new_val = str(new_budget)
            audit_action = "bulk_budget_increase"
        elif req.action == "decrease_budget":
            pct = req.percentage
            if pct is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="percentage is required for decrease_budget.",
                )
            new_budget = round(max(0.0, (campaign.daily_budget or 0.0) * (1 - pct / 100.0)), 2)
            await _call_meta_api_update(
                campaign.campaign_id,
                {"daily_budget": str(int(new_budget * 100))},
                token
            )
            campaign.daily_budget = new_budget
            new_val = str(new_budget)
            audit_action = "bulk_budget_decrease"
        elif req.action == "delete":
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=(
                    "Bulk local-only campaign deletion is disabled. "
                    "Delete/archive campaigns through Meta and sync the result."
                ),
            )
        else:
            continue

        audit = AuditLog(
            user_id=None,
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

@router.delete("/{campaign_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def delete_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Local-only deletion is disabled to prevent PostgreSQL and Meta from
    becoming inconsistent. Use Meta's supported campaign lifecycle operation
    and then let the sync layer reconcile the database.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Local-only campaign deletion is disabled. Campaign lifecycle "
            "changes must be performed through Meta and reconciled by sync."
        ),
    )