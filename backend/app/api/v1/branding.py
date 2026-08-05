from fastapi import APIRouter, Depends, HTTPException, status, Header, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any

from app.database import get_db
from app.schemas.schemas import (
    BrandingConfigResponse,
    BrandingConfigUpdate,
    CustomDomainCreate,
    CustomDomainResponse,
    AgencyClientCreate,
    AgencyClientResponse,
    AgencySwitchRequest,
    AgencySwitchResponse,
    EmailTemplateResponse,
    EmailTemplateUpdate,
    AuditLogResponse
)
from app.services.whitelabel_service import whitelabel_service
from app.services.tenant_middleware import get_tenant_context, TenantContext

router = APIRouter(tags=["Enterprise White Label & Agency Platform"])

# -----------------------------------------------------------------------------
# Branding API
# -----------------------------------------------------------------------------
@router.get("/branding", response_model=BrandingConfigResponse)
async def get_branding(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Get white-label branding configuration for the active tenant context.
    """
    return await whitelabel_service.get_branding(db, org_id=tenant_ctx.organization_id)

@router.patch("/branding", response_model=BrandingConfigResponse)
async def update_branding(
    req: BrandingConfigUpdate,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    x_user_id: Optional[str] = Header("usr_admin", alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Update tenant white-label branding (logo, colors, custom CSS, typography, email & PDF templates).
    """
    updates = req.model_dump(exclude_unset=True)
    return await whitelabel_service.update_branding(
        db=db,
        org_id=tenant_ctx.organization_id,
        user_id=x_user_id or "usr_admin",
        updates=updates
    )

# -----------------------------------------------------------------------------
# Custom Domains API
# -----------------------------------------------------------------------------
@router.get("/domains", response_model=List[CustomDomainResponse])
async def list_domains(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    List attached custom domains and SSL certificate statuses for active organization.
    """
    return await whitelabel_service.list_domains(db, org_id=tenant_ctx.organization_id)

@router.post("/domains", response_model=CustomDomainResponse, status_code=status.HTTP_201_CREATED)
async def add_domain(
    req: CustomDomainCreate,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    x_user_id: Optional[str] = Header("usr_admin", alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Attach a new custom white-label domain (e.g. agency.example.com) with DNS CNAME & TXT challenge records.
    """
    try:
        return await whitelabel_service.add_domain(
            db=db,
            org_id=tenant_ctx.organization_id,
            user_id=x_user_id or "usr_admin",
            domain_name=req.domain
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/domains/{id}/verify")
async def verify_domain(
    id: str,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    x_user_id: Optional[str] = Header("usr_admin", alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger DNS verification & SSL certificate issuance for custom domain.
    """
    try:
        return await whitelabel_service.verify_domain(
            db=db,
            domain_id=id,
            org_id=tenant_ctx.organization_id,
            user_id=x_user_id or "usr_admin"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/domains/{id}", status_code=status.HTTP_200_OK)
async def delete_domain(
    id: str,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    x_user_id: Optional[str] = Header("usr_admin", alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove custom domain binding from organization.
    """
    success = await whitelabel_service.delete_domain(
        db=db,
        domain_id=id,
        org_id=tenant_ctx.organization_id,
        user_id=x_user_id or "usr_admin"
    )
    if not success:
        raise HTTPException(status_code=404, detail="Domain not found")
    return {"status": "success", "message": f"Custom domain '{id}' removed successfully."}

# -----------------------------------------------------------------------------
# Agency Multi-Client & Hierarchy API
# -----------------------------------------------------------------------------
@router.get("/agency/clients", response_model=List[AgencyClientResponse])
async def list_agency_clients(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    List client organizations managed by the active agency organization.
    """
    return await whitelabel_service.list_agency_clients(db, agency_org_id=tenant_ctx.organization_id)

@router.post("/agency/clients", response_model=AgencyClientResponse, status_code=status.HTTP_201_CREATED)
async def create_agency_client(
    req: AgencyClientCreate,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    x_user_id: Optional[str] = Header("usr_admin", alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Provision a new isolated client organization under agency management hierarchy.
    """
    return await whitelabel_service.create_agency_client(
        db=db,
        agency_org_id=tenant_ctx.organization_id,
        user_id=x_user_id or "usr_admin",
        client_data=req.model_dump()
    )

@router.post("/agency/switch", response_model=AgencySwitchResponse)
async def switch_agency_client(
    req: AgencySwitchRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    x_user_id: Optional[str] = Header("usr_admin", alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Switch active tenant organization context for agency administrators.
    """
    return await whitelabel_service.switch_agency_client(
        db=db,
        agency_org_id=tenant_ctx.organization_id,
        user_id=x_user_id or "usr_admin",
        target_client_id=req.target_client_id
    )

# -----------------------------------------------------------------------------
# Email Templates & PDF Branding API
# -----------------------------------------------------------------------------
@router.get("/branding/email-template/{template_type}")
async def get_email_template(
    template_type: str,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Get white-labeled HTML email template for invitation, billing, reports, alerts, etc.
    """
    return await whitelabel_service.get_email_template(
        db=db,
        org_id=tenant_ctx.organization_id,
        template_type=template_type
    )

@router.post("/branding/pdf-preview", response_class=HTMLResponse)
async def preview_branded_pdf(
    payload: Dict[str, Any],
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Preview report HTML export styled with tenant white-label colors, headers, logos, and custom footer.
    """
    title = payload.get("title", "Executive Summary")
    body_html = payload.get("content_html", "<p>Campaign performance metrics breakdown for active period.</p>")
    pdf_html = await whitelabel_service.generate_branded_pdf_html(
        db=db,
        org_id=tenant_ctx.organization_id,
        title=title,
        content_html=body_html
    )
    return HTMLResponse(content=pdf_html, status_code=200)

@router.get("/branding/audit-logs", response_model=List[AuditLogResponse])
async def list_audit_logs(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Get audit history logs for white-label configuration changes & domain operations.
    """
    return await whitelabel_service.list_audit_logs(db, org_id=tenant_ctx.organization_id)
