import hmac
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.models.models import (
    MetaWebhookEvent, LeadEvent, MessengerEvent,
    Campaign as CampaignModel, MetaAdSet as AdSetModel, MetaAd as AdModel, Creative as CreativeModel
)
from app.api.v1.ws import ws_manager

logger = logging.getLogger("metamind.webhooks")

def verify_hub_signature(raw_body: bytes, signature_header: Optional[str]) -> bool:
    """
    Verifies X-Hub-Signature-256 header sent by Meta using HMAC-SHA256 with META_APP_SECRET.
    Returns True if valid or if in permissive dev/test mode with matching secret.
    """
    if not signature_header:
        logger.warning("Missing X-Hub-Signature-256 header in incoming webhook request.")
        return False
        
    if not signature_header.startswith("sha256="):
        logger.warning("Invalid X-Hub-Signature-256 format. Expected 'sha256=...'")
        return False

    expected_signature = signature_header[7:].strip()
    secret = settings.META_APP_SECRET
    
    if not secret:
        raise ValueError("META_APP_SECRET is missing")
    
    computed_hmac = hmac.new(
        key=secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()

    is_valid = hmac.compare_digest(computed_hmac, expected_signature)
    if not is_valid:
        logger.error("X-Hub-Signature-256 verification failed! Invalid HMAC signature.")
    return is_valid

def generate_event_id(object_type: str, entry_id: str, field_name: Optional[str], payload: dict) -> str:
    """Generates a deterministic unique ID for deduplication."""
    payload_str = json.dumps(payload, sort_keys=True)
    digest = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()[:16]
    return f"wh_{object_type}_{entry_id}_{field_name or 'data'}_{digest}"

async def process_webhook_payload(
    payload: Dict[str, Any],
    raw_body: bytes,
    signature_verified: bool,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Parses, validates, deduplicates, stores, and processes Meta Webhook events.
    Supports Campaign, AdSet, Ad, Creative, Lead, and Messenger events.
    """
    object_type = payload.get("object", "unknown")
    entries = payload.get("entry", [])
    
    processed_count = 0
    results = []

    for entry in entries:
        entry_id = str(entry.get("id", "global"))
        time_ts = entry.get("time", int(datetime.now(timezone.utc).timestamp()))
        
        # 1. Check for Messenger events
        messaging_list = entry.get("messaging", [])
        if messaging_list:
            for msg_item in messaging_list:
                sender_id = str(msg_item.get("sender", {}).get("id", "unknown"))
                recipient_id = str(msg_item.get("recipient", {}).get("id", "unknown"))
                msg_body = msg_item.get("message", {})
                mid = msg_body.get("mid") or f"mid_{sender_id}_{msg_item.get('timestamp', time_ts)}"
                text = msg_body.get("text")
                attachments = msg_body.get("attachments")
                
                event_id = f"msg_{mid}"
                
                # Deduplication check
                stmt = select(MetaWebhookEvent).where(MetaWebhookEvent.event_id == event_id)
                existing = (await db.execute(stmt)).scalar_one_or_none()
                if existing and existing.status == "processed":
                    logger.info(f"Duplicate messenger event skipped: {event_id}")
                    continue
                
                # Save Webhook Event
                wh_event = existing or MetaWebhookEvent(
                    event_id=event_id,
                    object_type="messenger",
                    entry_id=entry_id,
                    field_name="messaging",
                    payload=msg_item,
                    signature_verified=signature_verified,
                    status="pending"
                )
                db.add(wh_event)
                
                try:
                    # Upsert MessengerEvent
                    stmt_msg = select(MessengerEvent).where(MessengerEvent.mid == mid)
                    existing_msg = (await db.execute(stmt_msg)).scalar_one_or_none()
                    if not existing_msg:
                        new_msg = MessengerEvent(
                            mid=mid,
                            sender_id=sender_id,
                            recipient_id=recipient_id,
                            message_text=text,
                            attachments=attachments
                        )
                        db.add(new_msg)
                        
                    wh_event.status = "processed"
                    wh_event.processed_at = datetime.now(timezone.utc)
                    processed_count += 1
                    
                    # WS Broadcast
                    await ws_manager.broadcast({
                        "event": "meta_webhook_update",
                        "object_type": "messenger",
                        "entry_id": entry_id,
                        "data": {"mid": mid, "sender_id": sender_id, "text": text}
                    })
                except Exception as exc:
                    wh_event.status = "failed"
                    wh_event.error_message = str(exc)
                    wh_event.retry_count += 1
                    logger.error(f"Error processing messenger event {event_id}: {exc}")
                
                await db.commit()
                results.append({"event_id": event_id, "status": wh_event.status})

        # 2. Check for Leadgen events in entry or changes
        leadgen_entry = entry.get("leadgen")
        if leadgen_entry:
            leadgen_id = str(leadgen_entry.get("leadgen_id") or leadgen_entry.get("id", ""))
            event_id = f"lead_{leadgen_id}"
            
            stmt = select(MetaWebhookEvent).where(MetaWebhookEvent.event_id == event_id)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if not (existing and existing.status == "processed"):
                wh_event = existing or MetaWebhookEvent(
                    event_id=event_id,
                    object_type="leadgen",
                    entry_id=entry_id,
                    field_name="leadgen",
                    payload=leadgen_entry,
                    signature_verified=signature_verified,
                    status="pending"
                )
                db.add(wh_event)
                
                try:
                    stmt_lead = select(LeadEvent).where(LeadEvent.leadgen_id == leadgen_id)
                    existing_lead = (await db.execute(stmt_lead)).scalar_one_or_none()
                    if not existing_lead:
                        new_lead = LeadEvent(
                            leadgen_id=leadgen_id,
                            form_id=str(leadgen_entry.get("form_id", "")),
                            ad_id=str(leadgen_entry.get("ad_id", "")),
                            adgroup_id=str(leadgen_entry.get("adgroup_id", "")),
                            campaign_id=str(leadgen_entry.get("campaign_id", "")),
                            page_id=entry_id,
                            lead_data=leadgen_entry
                        )
                        db.add(new_lead)
                    wh_event.status = "processed"
                    wh_event.processed_at = datetime.now(timezone.utc)
                    processed_count += 1
                    
                    await ws_manager.broadcast({
                        "event": "meta_webhook_update",
                        "object_type": "leadgen",
                        "entry_id": entry_id,
                        "data": {"leadgen_id": leadgen_id, "form_id": leadgen_entry.get("form_id")}
                    })
                except Exception as exc:
                    wh_event.status = "failed"
                    wh_event.error_message = str(exc)
                    wh_event.retry_count += 1
                    logger.error(f"Error processing lead event {event_id}: {exc}")
                
                await db.commit()
                results.append({"event_id": event_id, "status": wh_event.status})

        # 3. Check for standard object changes (campaign, adset, ad, creative, leadgen)
        changes = entry.get("changes", [])
        for change in changes:
            field = change.get("field", "general")
            value = change.get("value", {})
            if isinstance(value, str):
                value = {"data": value}
                
            event_id = generate_event_id(object_type, entry_id, field, value)
            
            # Deduplication check
            stmt = select(MetaWebhookEvent).where(MetaWebhookEvent.event_id == event_id)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing and existing.status == "processed":
                logger.info(f"Duplicate webhook change skipped: {event_id}")
                results.append({"event_id": event_id, "status": "already_processed"})
                continue

            wh_event = existing or MetaWebhookEvent(
                event_id=event_id,
                object_type=object_type,
                entry_id=entry_id,
                field_name=field,
                payload=value,
                signature_verified=signature_verified,
                status="pending"
            )
            db.add(wh_event)
            
            try:
                # Handle Campaign Updates
                if field in ["campaigns", "campaign_id"] or object_type == "campaign" or "campaign_id" in value:
                    cid = str(value.get("campaign_id") or value.get("id") or entry_id)
                    stmt_c = select(CampaignModel).where(
                        (CampaignModel.campaign_id == cid) | (CampaignModel.id == cid)
                    )
                    c_obj = (await db.execute(stmt_c)).scalar_one_or_none()
                    if c_obj:
                        if "status" in value:
                            c_obj.status = value["status"].upper()
                        if "daily_budget" in value:
                            c_obj.daily_budget = float(value["daily_budget"])
                        if "spend" in value:
                            c_obj.spend = float(value["spend"])
                        if "name" in value:
                            c_obj.name = value["name"]
                    else:
                        c_obj = CampaignModel(
                            campaign_id=cid,
                            name=value.get("name", f"Synced Campaign {cid}"),
                            status=value.get("status", "ACTIVE").upper(),
                            objective=value.get("objective", "OUTCOME_SALES"),
                            daily_budget=float(value.get("daily_budget", 1000.0)),
                            spend=float(value.get("spend", 0.0))
                        )
                        db.add(c_obj)

                # Handle AdSet Updates
                elif field in ["adsets", "adset_id"] or object_type == "adset" or "adset_id" in value:
                    as_id = str(value.get("adset_id") or value.get("id") or entry_id)
                    stmt_as = select(AdSetModel).where(AdSetModel.ad_set_id == as_id)
                    as_obj = (await db.execute(stmt_as)).scalar_one_or_none()
                    if as_obj:
                        if "status" in value:
                            as_obj.status = value["status"].upper()
                        if "daily_budget" in value:
                            as_obj.daily_budget = float(value["daily_budget"])
                        if "spend" in value:
                            as_obj.spend = float(value["spend"])
                        if "name" in value:
                            as_obj.name = value["name"]
                    else:
                        as_obj = AdSetModel(
                            ad_set_id=as_id,
                            name=value.get("name", f"Synced AdSet {as_id}"),
                            status=value.get("status", "ACTIVE").upper(),
                            daily_budget=float(value.get("daily_budget", 500.0)),
                            spend=float(value.get("spend", 0.0))
                        )
                        db.add(as_obj)

                # Handle Ad Updates
                elif field in ["ads", "ad_id"] or object_type == "ad" or "ad_id" in value:
                    ad_id = str(value.get("ad_id") or value.get("id") or entry_id)
                    stmt_ad = select(AdModel).where(AdModel.ad_id == ad_id)
                    ad_obj = (await db.execute(stmt_ad)).scalar_one_or_none()
                    if ad_obj:
                        if "status" in value:
                            ad_obj.status = value["status"].upper()
                        if "name" in value:
                            ad_obj.name = value["name"]
                        if "spend" in value:
                            ad_obj.spend = float(value["spend"])
                    else:
                        ad_obj = AdModel(
                            ad_id=ad_id,
                            name=value.get("name", f"Synced Ad {ad_id}"),
                            status=value.get("status", "ACTIVE").upper(),
                            spend=float(value.get("spend", 0.0))
                        )
                        db.add(ad_obj)

                # Handle Creative Updates
                elif field in ["creatives", "creative_id"] or object_type == "creative" or "creative_id" in value:
                    cr_id = str(value.get("creative_id") or value.get("id") or entry_id)
                    stmt_cr = select(CreativeModel).where(CreativeModel.creative_id == cr_id)
                    cr_obj = (await db.execute(stmt_cr)).scalar_one_or_none()
                    if cr_obj:
                        if "name" in value:
                            cr_obj.name = value["name"]
                        if "title" in value:
                            cr_obj.title = value["title"]
                        if "body" in value:
                            cr_obj.body = value["body"]
                        if "image_url" in value:
                            cr_obj.image_url = value["image_url"]
                    else:
                        cr_obj = CreativeModel(
                            creative_id=cr_id,
                            name=value.get("name", f"Synced Creative {cr_id}"),
                            title=value.get("title", "Updated Creative"),
                            body=value.get("body", "Meta webhook creative payload"),
                            image_url=value.get("image_url")
                        )
                        db.add(cr_obj)

                # Handle Leadgen in changes
                elif field == "leadgen":
                    leadgen_id = str(value.get("leadgen_id") or value.get("id") or entry_id)
                    stmt_lead = select(LeadEvent).where(LeadEvent.leadgen_id == leadgen_id)
                    existing_lead = (await db.execute(stmt_lead)).scalar_one_or_none()
                    if not existing_lead:
                        new_lead = LeadEvent(
                            leadgen_id=leadgen_id,
                            form_id=str(value.get("form_id", "")),
                            ad_id=str(value.get("ad_id", "")),
                            page_id=entry_id,
                            lead_data=value
                        )
                        db.add(new_lead)

                wh_event.status = "processed"
                wh_event.processed_at = datetime.now(timezone.utc)
                processed_count += 1

                # Broadcast WS Notification
                await ws_manager.broadcast({
                    "event": "meta_webhook_update",
                    "object_type": object_type,
                    "field": field,
                    "entry_id": entry_id,
                    "data": value
                })

            except Exception as exc:
                wh_event.status = "failed"
                wh_event.error_message = str(exc)
                wh_event.retry_count += 1
                logger.error(f"Failed to process webhook event {event_id}: {exc}")

            await db.commit()
            results.append({"event_id": event_id, "status": wh_event.status})

    return {
        "status": "completed",
        "processed_count": processed_count,
        "events": results
    }

async def reprocess_webhook_event_by_id(event_id: str, db: AsyncSession) -> Dict[str, Any]:
    """Reprocesses a specific failed or pending webhook event."""
    stmt = select(MetaWebhookEvent).where(MetaWebhookEvent.event_id == event_id)
    event = (await db.execute(stmt)).scalar_one_or_none()
    
    if not event:
        return {"status": "not_found", "event_id": event_id}

    payload = {
        "object": event.object_type,
        "entry": [{
            "id": event.entry_id or "global",
            "changes": [{
                "field": event.field_name or "general",
                "value": event.payload
            }]
        }]
    }
    
    # Mark for re-processing
    event.status = "pending"
    event.error_message = None
    await db.commit()

    return await process_webhook_payload(
        payload=payload,
        raw_body=json.dumps(payload).encode("utf-8"),
        signature_verified=event.signature_verified,
        db=db
    )
