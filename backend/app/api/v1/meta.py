import time
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional

from app.database import get_db
from app.core.config import settings
from app.core.security import decrypt_token, encrypt_token
from app.models.models import (
    Campaign as CampaignModel, MetaAdSet as AdSetModel, MetaAd as AdModel,
    Creative as CreativeModel, Pixel as PixelModel, CustomConversion as CustomConversionModel,
    CustomAudience as CustomAudienceModel, Insight as InsightModel, SyncJob as SyncJobModel,
    MetaWebhookEvent, OAuthToken, MetaAccount
)
from app.schemas.schemas import (
    CampaignResponse, AdSetResponse, AdResponse, CreativeResponse, PixelResponse,
    CustomConversionResponse, CustomAudienceResponse, InsightResponse,
    SyncStatusResponse, SyncTriggerRequest, WebhookEventResponse, WebhookReprocessResponse,
    MetaCapiEventRequest, MetaCapiEventResponse, MetaPermissionsResponse, MetaPermissionItem
)
from app.services.meta_sync import run_meta_sync, META_GRAPH_URL
from app.services.meta_webhook_service import (
    verify_hub_signature, process_webhook_payload, reprocess_webhook_event_by_id
)

router = APIRouter(prefix="/meta", tags=["Meta Marketing API Sync"])

@router.get("/webhook", response_class=PlainTextResponse)
async def verify_meta_webhook_alias(
    request: Request,
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge")
):
    """GET /api/v1/meta/webhook - Verification handshake for Meta Webhook subscription."""
    expected_token = settings.META_WEBHOOK_VERIFY_TOKEN
    if not expected_token:
        raise HTTPException(
            status_code=500,
            detail="META_WEBHOOK_VERIFY_TOKEN is not configured.",
        )

    if (
        hub_mode == "subscribe"
        and hub_verify_token == expected_token
        and hub_challenge
    ):
        return PlainTextResponse(content=str(hub_challenge), status_code=200)

    raise HTTPException(
        status_code=403,
        detail="Meta Webhook verification failed.",
    )

@router.post("/webhook")
async def receive_meta_webhook_alias(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """POST /api/v1/meta/webhook - Ingest Meta Webhook payload."""
    raw_body = await request.body()
    signature_header = request.headers.get("X-Hub-Signature-256")
    signature_valid = verify_hub_signature(raw_body, signature_header)
    
    if signature_header and not signature_valid:
        raise HTTPException(status_code=401, detail="Invalid X-Hub-Signature-256 HMAC signature.")

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}")

    result = await process_webhook_payload(payload=payload, raw_body=raw_body, signature_verified=signature_valid, db=db)
    return {"status": "EVENT_RECEIVED", "processed_count": result.get("processed_count", 0), "details": result}

@router.get("/webhooks/logs", response_model=List[WebhookEventResponse])
async def get_meta_webhook_logs(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """GET /api/v1/meta/webhooks/logs - Audit logs of received webhook events."""
    stmt = select(MetaWebhookEvent).order_by(MetaWebhookEvent.received_at.desc()).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/webhooks/reprocess/{event_id}", response_model=WebhookReprocessResponse)
async def reprocess_meta_webhook_event(
    event_id: str,
    db: AsyncSession = Depends(get_db)
):
    """POST /api/v1/meta/webhooks/reprocess/{event_id} - Retry failed webhook event."""
    res = await reprocess_webhook_event_by_id(event_id=event_id, db=db)
    return WebhookReprocessResponse(event_id=event_id, status=res.get("status", "completed"), message="Reprocessed")

@router.get("/sync", response_model=List[SyncStatusResponse])
async def list_sync_jobs(db: AsyncSession = Depends(get_db)):
    """GET /api/v1/meta/sync - Retrieve recent Meta sync jobs history."""
    stmt = select(SyncJobModel).order_by(SyncJobModel.started_at.desc()).limit(10)
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    return jobs

@router.post("/sync", response_model=SyncStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_meta_sync(
    body: SyncTriggerRequest,
    db: AsyncSession = Depends(get_db)
):
    """POST /api/v1/meta/sync - Trigger background Meta Marketing API data download and sync."""
    job_res = await run_meta_sync(ad_account_id=body.ad_account_id, sync_type=body.sync_type, db=db)
    
    stmt = select(SyncJobModel).where(SyncJobModel.job_id == job_res["job_id"])
    result = await db.execute(stmt)
    sync_job = result.scalar_one_or_none()
    
    if not sync_job:
        raise HTTPException(status_code=500, detail="Failed to initialize sync job")
        
    return sync_job

@router.get("/sync/status", response_model=SyncStatusResponse)
async def get_latest_sync_status(
    job_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """GET /api/v1/meta/sync/status - Get current or specified sync job progress."""
    if job_id:
        stmt = select(SyncJobModel).where(SyncJobModel.job_id == job_id)
    else:
        stmt = select(SyncJobModel).order_by(SyncJobModel.started_at.desc()).limit(1)
        
    result = await db.execute(stmt)
    sync_job = result.scalar_one_or_none()
    
    if not sync_job:
        raise HTTPException(
            status_code=404,
            detail="No Meta sync job has been created yet.",
        )

    return sync_job

@router.get("/campaigns", response_model=List[CampaignResponse])
async def get_synced_campaigns(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """GET /api/v1/meta/campaigns - Get synced campaigns with pagination."""
    stmt = select(CampaignModel).order_by(CampaignModel.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/adsets", response_model=List[AdSetResponse])
async def get_synced_adsets(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """GET /api/v1/meta/adsets - Get synced ad sets with pagination."""
    stmt = select(AdSetModel).order_by(AdSetModel.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/ads", response_model=List[AdResponse])
async def get_synced_ads(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """GET /api/v1/meta/ads - Get synced ads with pagination."""
    stmt = select(AdModel).order_by(AdModel.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/insights", response_model=List[InsightResponse])
async def get_synced_insights(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """GET /api/v1/meta/insights - Get synced marketing performance insights with pagination."""
    stmt = select(InsightModel).order_by(InsightModel.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/creatives", response_model=List[CreativeResponse])
async def get_synced_creatives(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """GET /api/v1/meta/creatives - Get synced ad creatives with pagination."""
    stmt = select(CreativeModel).order_by(CreativeModel.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/pixels", response_model=List[PixelResponse])
async def get_synced_pixels(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """GET /api/v1/meta/pixels - Get synced Meta Pixels with pagination."""
    stmt = select(PixelModel).order_by(PixelModel.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/conversions", response_model=List[CustomConversionResponse])
async def get_synced_conversions(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """GET /api/v1/meta/conversions - Get synced custom conversions with pagination."""
    stmt = select(CustomConversionModel).order_by(CustomConversionModel.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/audiences", response_model=List[CustomAudienceResponse])
async def get_synced_audiences(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """GET /api/v1/meta/audiences - Get synced custom & lookalike audiences with pagination."""
    stmt = select(CustomAudienceModel).order_by(CustomAudienceModel.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/capi/event", response_model=MetaCapiEventResponse)
async def send_meta_capi_event(
    payload: MetaCapiEventRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    POST /api/v1/meta/capi/event - Transmit a server-side Conversions API
    event directly to Meta Graph API.
    """
    if not payload.pixel_id:
        raise HTTPException(
            status_code=400,
            detail="pixel_id is required for a Meta Conversions API event.",
        )

    token_stmt = (
        select(OAuthToken)
        .where(OAuthToken.is_valid.is_(True))
        .order_by(OAuthToken.created_at.desc())
    )
    token_res = await db.execute(token_stmt)
    token_rec = token_res.scalar_one_or_none()

    if not token_rec:
        raise HTTPException(
            status_code=401,
            detail="No active Meta OAuth connection found.",
        )

    access_token = decrypt_token(token_rec.encrypted_access_token)
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Stored Meta access token is invalid.",
        )

    event_data = {
        "event_name": payload.event_name,
        "event_time": payload.event_time or int(time.time()),
        "action_source": payload.action_source,
    }

    if payload.event_source_url:
        event_data["event_source_url"] = payload.event_source_url

    if payload.user_data:
        user_data = {}
        if payload.user_data.email:
            user_data["em"] = [payload.user_data.email]
        if payload.user_data.client_ip_address:
            user_data["client_ip_address"] = payload.user_data.client_ip_address
        if payload.user_data.client_user_agent:
            user_data["client_user_agent"] = payload.user_data.client_user_agent
        if user_data:
            event_data["user_data"] = user_data

    if payload.custom_data:
        custom_data = {}
        if payload.custom_data.currency:
            custom_data["currency"] = payload.custom_data.currency
        if payload.custom_data.value is not None:
            custom_data["value"] = payload.custom_data.value
        if payload.custom_data.content_name:
            custom_data["content_name"] = payload.custom_data.content_name
        if custom_data:
            event_data["custom_data"] = custom_data

    capi_url = f"{META_GRAPH_URL}/{payload.pixel_id}/events"
    capi_params = {"access_token": access_token}
    if payload.test_event_code:
        capi_params["test_event_code"] = payload.test_event_code

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                capi_url,
                params=capi_params,
                json={"data": [event_data]},
            )

        try:
            response_data = response.json()
        except ValueError:
            response_data = {}

        if response.status_code != 200:
            error = response_data.get("error", {})
            error_message = (
                error.get("message")
                or f"Meta CAPI request failed with HTTP {response.status_code}."
            )
            raise HTTPException(status_code=502, detail=error_message)

        return MetaCapiEventResponse(
            status="SUCCESS",
            events_received=response_data.get("events_received", 1),
            messages=["Meta accepted the Conversions API event."],
            fbtrace_id=response_data.get("fbtrace_id"),
            event_name=payload.event_name,
            pixel_id=payload.pixel_id,
        )

    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Meta Conversions API request failed: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send Meta Conversions API event: {exc}",
        ) from exc


@router.get("/permissions", response_model=MetaPermissionsResponse)
async def validate_meta_permissions(db: AsyncSession = Depends(get_db)):
    """
    GET /api/v1/meta/permissions - Validate the active Meta OAuth token
    against Meta Graph API /me/permissions.
    """
    token_stmt = (
        select(OAuthToken)
        .where(OAuthToken.is_valid.is_(True))
        .order_by(OAuthToken.created_at.desc())
    )
    token_res = await db.execute(token_stmt)
    token_rec = token_res.scalar_one_or_none()

    if not token_rec:
        return MetaPermissionsResponse(
            is_valid=False,
            meta_user_id="",
            permissions=[],
            granted_scopes=[],
            declined_scopes=[],
        )

    access_token = decrypt_token(token_rec.encrypted_access_token)
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Stored Meta access token is invalid.",
        )

    permissions_url = f"{META_GRAPH_URL}/me/permissions"
    me_url = f"{META_GRAPH_URL}/me"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            permissions_response = await client.get(
                permissions_url,
                params={"access_token": access_token},
            )
            me_response = await client.get(
                me_url,
                params={"access_token": access_token, "fields": "id"},
            )

        try:
            permissions_payload = permissions_response.json()
        except ValueError:
            permissions_payload = {}

        try:
            me_payload = me_response.json()
        except ValueError:
            me_payload = {}

        if permissions_response.status_code != 200:
            error = permissions_payload.get("error", {})
            raise HTTPException(
                status_code=502,
                detail=error.get(
                    "message",
                    f"Meta permissions request failed with HTTP {permissions_response.status_code}.",
                ),
            )

        if me_response.status_code != 200:
            error = me_payload.get("error", {})
            raise HTTPException(
                status_code=502,
                detail=error.get(
                    "message",
                    f"Meta user lookup failed with HTTP {me_response.status_code}.",
                ),
            )

        meta_user_id = me_payload.get("id")
        if not meta_user_id:
            raise HTTPException(
                status_code=502,
                detail="Meta did not return a user ID.",
            )

        items = []
        granted = []
        declined = []

        for permission in permissions_payload.get("data", []):
            permission_name = permission.get("permission")
            permission_status = permission.get("status")

            if not permission_name or not permission_status:
                continue

            items.append(
                MetaPermissionItem(
                    permission=permission_name,
                    status=permission_status,
                )
            )

            if permission_status == "granted":
                granted.append(permission_name)
            elif permission_status == "declined":
                declined.append(permission_name)

        return MetaPermissionsResponse(
            is_valid=True,
            meta_user_id=meta_user_id,
            permissions=items,
            granted_scopes=granted,
            declined_scopes=declined,
        )

    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Meta permissions request failed: {exc}",
        ) from exc


@router.post("/token/refresh")
async def manual_meta_token_refresh(db: AsyncSession = Depends(get_db)):
    """
    POST /api/v1/meta/token/refresh - Exchange the active Meta OAuth token
    for a refreshed token using Meta's fb_exchange_token flow.
    """
    token_stmt = (
        select(OAuthToken)
        .where(OAuthToken.is_valid.is_(True))
        .order_by(OAuthToken.created_at.desc())
    )
    token_res = await db.execute(token_stmt)
    token_rec = token_res.scalar_one_or_none()

    if not token_rec:
        raise HTTPException(
            status_code=400,
            detail="No active Meta OAuth connection found to refresh.",
        )

    app_id = settings.META_APP_ID
    app_secret = settings.META_APP_SECRET

    if not app_id or not app_secret:
        raise HTTPException(
            status_code=500,
            detail="META_APP_ID and META_APP_SECRET must be configured.",
        )

    old_token = decrypt_token(token_rec.encrypted_access_token)
    if not old_token:
        raise HTTPException(
            status_code=401,
            detail="Stored Meta access token is invalid.",
        )

    refresh_url = f"{META_GRAPH_URL}/oauth/access_token"
    refresh_params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": old_token,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(refresh_url, params=refresh_params)

        try:
            response_data = response.json()
        except ValueError:
            response_data = {}

        if response.status_code != 200:
            error = response_data.get("error", {})
            raise HTTPException(
                status_code=502,
                detail=error.get(
                    "message",
                    f"Meta token refresh failed with HTTP {response.status_code}.",
                ),
            )

        new_token = response_data.get("access_token")
        if not new_token:
            raise HTTPException(
                status_code=502,
                detail="Meta did not return a refreshed access token.",
            )

        token_rec.encrypted_access_token = encrypt_token(new_token)
        token_rec.last_refreshed = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime(),
        )
        await db.commit()

        return {
            "status": "success",
            "message": "Meta OAuth access token refreshed successfully.",
            "refreshed_at": token_rec.last_refreshed,
        }

    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Meta token refresh request failed: {exc}",
        ) from exc