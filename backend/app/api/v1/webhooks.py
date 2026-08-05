from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional

from app.database import get_db
from app.core.config import settings
from app.models.models import MetaWebhookEvent, LeadEvent, MessengerEvent
from app.schemas.schemas import (
    WebhookEventResponse, WebhookReprocessResponse, LeadEventResponse, MessengerEventResponse
)
from app.services.meta_webhook_service import (
    verify_hub_signature, process_webhook_payload, reprocess_webhook_event_by_id
)

router = APIRouter(prefix="/webhooks", tags=["Meta Webhooks Engine"])

@router.get("/meta", response_class=PlainTextResponse)
@router.get("/meta/webhook", response_class=PlainTextResponse)
async def verify_meta_webhook_challenge(
    request: Request,
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge")
):
    """
    GET /api/v1/webhooks/meta - Handles Meta Webhook verification handshake.
    Compares hub.verify_token with META_WEBHOOK_VERIFY_TOKEN. Returns hub.challenge.
    """
    expected_token = settings.META_WEBHOOK_VERIFY_TOKEN or "metamind_webhook_secret_v21"
    
    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        if hub_challenge:
            return PlainTextResponse(content=str(hub_challenge), status_code=200)
        return PlainTextResponse(content="OK", status_code=200)
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Meta Webhook verification failed. Token mismatch or invalid mode."
    )

@router.post("/meta")
@router.post("/meta/webhook")
async def receive_meta_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    POST /api/v1/webhooks/meta - Ingests Meta Webhook event notifications.
    Verifies X-Hub-Signature-256 HMAC-SHA256 signature, deduplicates, stores, and updates DB & WebSockets.
    """
    raw_body = await request.body()
    signature_header = request.headers.get("X-Hub-Signature-256")
    
    # 1. Verify HMAC-SHA256 signature
    signature_valid = verify_hub_signature(raw_body, signature_header)
    
    # Strict validation check: Reject invalid signatures
    # If in test/dev mode without header, verify_hub_signature handles rules or we reject if signature provided is bad
    if signature_header and not signature_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-Hub-Signature-256 HMAC signature. Rejecting untrusted webhook payload."
        )

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed JSON body: {exc}"
        )

    # 2. Process payload
    result = await process_webhook_payload(
        payload=payload,
        raw_body=raw_body,
        signature_verified=signature_valid,
        db=db
    )

    return {
        "status": "EVENT_RECEIVED",
        "processed_count": result.get("processed_count", 0),
        "details": result
    }

@router.get("/logs", response_model=List[WebhookEventResponse])
async def get_webhook_event_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = None,
    object_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """GET /api/v1/webhooks/logs - Audit logs of all ingested Meta webhook events."""
    stmt = select(MetaWebhookEvent).order_by(MetaWebhookEvent.received_at.desc())
    if status_filter:
        stmt = stmt.where(MetaWebhookEvent.status == status_filter)
    if object_type:
        stmt = stmt.where(MetaWebhookEvent.object_type == object_type)
        
    stmt = stmt.offset(offset).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/reprocess/{event_id}", response_model=WebhookReprocessResponse)
async def reprocess_failed_webhook(
    event_id: str,
    db: AsyncSession = Depends(get_db)
):
    """POST /api/v1/webhooks/reprocess/{event_id} - Manually retry failed webhook event processing."""
    res = await reprocess_webhook_event_by_id(event_id=event_id, db=db)
    return WebhookReprocessResponse(
        event_id=event_id,
        status=res.get("status", "completed"),
        message=f"Reprocessed webhook event. Processed items: {res.get('processed_count', 0)}"
    )

@router.get("/leads", response_model=List[LeadEventResponse])
async def get_lead_webhook_events(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """GET /api/v1/webhooks/leads - List captured Meta lead form submission events."""
    stmt = select(LeadEvent).order_by(LeadEvent.created_time.desc()).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/messages", response_model=List[MessengerEventResponse])
async def get_messenger_webhook_events(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """GET /api/v1/webhooks/messages - List captured Meta Messenger events."""
    stmt = select(MessengerEvent).order_by(MessengerEvent.timestamp.desc()).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()
