from fastapi import APIRouter, Depends, HTTPException, status, Header, Response, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any

from app.database import get_db
from app.schemas.schemas import (
    SubscribeRequest,
    ChangePlanRequest,
    PaymentWebhookRequest,
    RefundRequest
)
from app.services.billing_service import billing_service
from app.services.tenant_middleware import get_tenant_context, TenantContext

router = APIRouter(prefix="/billing", tags=["Enterprise Billing & Subscriptions"])

@router.get("/plans")
async def list_plans(db: AsyncSession = Depends(get_db)):
    """
    List all available subscription plans with included seats, limits, and pricing.
    """
    return await billing_service.list_plans(db)

@router.get("/subscription")
async def get_subscription(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Get active subscription details, renewal dates, and current usage limits.
    """
    return await billing_service.get_subscription(db, org_id=tenant_ctx.organization_id)

@router.post("/subscribe")
async def subscribe(
    req: SubscribeRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Subscribe to a new plan using Stripe or Razorpay provider.
    """
    return await billing_service.subscribe(
        db=db,
        org_id=tenant_ctx.organization_id,
        plan_id=req.plan_id,
        provider_name=req.provider or "stripe",
        payment_method_id=req.payment_method_id
    )

@router.post("/change-plan")
async def change_plan(
    req: ChangePlanRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Upgrade or downgrade plan with instant proration calculation.
    """
    return await billing_service.change_plan(
        db=db,
        org_id=tenant_ctx.organization_id,
        new_plan_id=req.new_plan_id
    )

@router.post("/cancel")
async def cancel_subscription(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel active subscription at end of current billing cycle.
    """
    return await billing_service.cancel_subscription(db=db, org_id=tenant_ctx.organization_id)

@router.post("/resume")
async def resume_subscription(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Reactivate a canceled subscription.
    """
    return await billing_service.resume_subscription(db=db, org_id=tenant_ctx.organization_id)

@router.get("/invoices")
async def list_invoices(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    List billing invoice history for the active organization.
    """
    return await billing_service.list_invoices(db, org_id=tenant_ctx.organization_id)

@router.get("/invoices/{id}")
async def get_invoice(
    id: str,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed breakdown for a specific invoice.
    """
    inv = await billing_service.get_invoice(db, invoice_id=id, org_id=tenant_ctx.organization_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return inv

@router.get("/invoices/{id}/download", response_class=HTMLResponse)
async def download_invoice(
    id: str,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Download or print styled HTML invoice.
    """
    html_content = await billing_service.download_invoice_html(db, invoice_id=id, org_id=tenant_ctx.organization_id)
    return HTMLResponse(content=html_content, status_code=200)

@router.post("/payment-webhook")
async def payment_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db)
):
    """
    Receive payment provider webhooks (Stripe / Razorpay) with signature validation and duplicate protection.
    """
    try:
        body_json = await request.json()
    except Exception:
        body_json = {}

    return await billing_service.process_webhook(
        db=db,
        provider_name="stripe" if stripe_signature else "razorpay",
        payload=body_json,
        signature=stripe_signature
    )

@router.get("/quota-check/{feature}")
async def check_feature_quota(
    feature: str,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Usage enforcement endpoint. Checks if plan allows requested action (campaign_sync, automation, ai_request).
    """
    return await billing_service.enforce_quota(db, org_id=tenant_ctx.organization_id, feature=feature)

@router.get("/metrics")
async def get_billing_metrics(
    db: AsyncSession = Depends(get_db)
):
    """
    Observability endpoint for financial metrics (MRR, ARR, Churn, Revenue).
    """
    return await billing_service.get_metrics(db)
