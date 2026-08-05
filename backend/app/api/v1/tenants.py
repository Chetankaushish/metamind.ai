from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_db
from app.schemas.schemas import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
    InvitationCreate,
    InvitationAcceptRequest,
    SubscriptionUpdate
)
from app.services.tenant_service import tenant_service
from app.services.tenant_middleware import get_tenant_context, TenantContext

router = APIRouter(tags=["Enterprise Multi-Tenant SaaS"])

# -----------------------------------------------------------------------------
# Organizations API
# -----------------------------------------------------------------------------
@router.get("/organizations", response_model=List[OrganizationResponse])
async def list_organizations(
    x_user_id: Optional[str] = Header("usr_admin", alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all active organizations for the authenticated user session.
    """
    user_id = x_user_id or "usr_admin"
    orgs = await tenant_service.list_organizations(db, user_id=user_id)
    return orgs

@router.post("/organizations", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    req: OrganizationCreate,
    x_user_id: Optional[str] = Header("usr_admin", alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new isolated organization tenant with default settings and owner role.
    """
    user_id = x_user_id or "usr_admin"
    org = await tenant_service.create_organization(
        db=db,
        name=req.name,
        domain=req.domain,
        user_id=user_id
    )
    return org

@router.patch("/organizations/{id}", response_model=OrganizationResponse)
async def update_organization(
    id: str,
    req: OrganizationUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update organization name, domain, or active status.
    """
    org = await tenant_service.update_organization(
        db=db,
        org_id=id,
        name=req.name,
        domain=req.domain,
        is_active=req.is_active
    )
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org

@router.delete("/organizations/{id}", status_code=status.HTTP_200_OK)
async def delete_organization(
    id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an organization tenant and all associated workspace resources.
    """
    success = await tenant_service.delete_organization(db=db, org_id=id)
    if not success:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"status": "success", "message": f"Organization '{id}' deleted successfully."}

# -----------------------------------------------------------------------------
# Workspaces API
# -----------------------------------------------------------------------------
@router.get("/workspaces", response_model=List[WorkspaceResponse])
async def list_workspaces(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    List all workspaces for the current organization context.
    """
    workspaces = await tenant_service.list_workspaces(db, org_id=tenant_ctx.organization_id)
    return workspaces

@router.post("/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    req: WorkspaceCreate,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new workspace within the active organization.
    """
    ws = await tenant_service.create_workspace(
        db=db,
        org_id=tenant_ctx.organization_id,
        name=req.name,
        description=req.description,
        workspace_type=req.workspace_type or "Marketing Team"
    )
    return ws

@router.patch("/workspaces/{id}", response_model=WorkspaceResponse)
async def update_workspace(
    id: str,
    req: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update workspace name or description.
    """
    ws = await tenant_service.update_workspace(
        db=db,
        ws_id=id,
        name=req.name,
        description=req.description,
        workspace_type=req.workspace_type
    )
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws

@router.delete("/workspaces/{id}", status_code=status.HTTP_200_OK)
async def delete_workspace(
    id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a workspace.
    """
    success = await tenant_service.delete_workspace(db=db, ws_id=id)
    if not success:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"status": "success", "message": f"Workspace '{id}' deleted successfully."}

# -----------------------------------------------------------------------------
# Invitations API
# -----------------------------------------------------------------------------
@router.post("/invitations", status_code=status.HTTP_201_CREATED)
async def create_invitation(
    req: InvitationCreate,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    x_user_id: Optional[str] = Header("usr_admin", alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate and send an email invitation token to join the organization.
    """
    user_id = x_user_id or "usr_admin"
    inv = await tenant_service.create_invitation(
        db=db,
        org_id=tenant_ctx.organization_id,
        email=req.email,
        role=req.role or "Manager",
        workspace_id=req.workspace_id,
        invited_by=user_id
    )
    return inv

@router.post("/invitations/{token}/accept", status_code=status.HTTP_200_OK)
async def accept_invitation(
    token: str,
    x_user_id: Optional[str] = Header("usr_admin", alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Accept an invitation token and join the organization.
    """
    user_id = x_user_id or "usr_admin"
    res = await tenant_service.accept_invitation(db=db, token=token, user_id=user_id)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

# -----------------------------------------------------------------------------
# Subscriptions & Usage Metering API
# -----------------------------------------------------------------------------
@router.get("/subscriptions")
async def get_subscription(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Get subscription plan, quota limits, and renewal dates for current tenant.
    """
    return await tenant_service.get_subscription(db, org_id=tenant_ctx.organization_id)

@router.get("/usage")
async def get_usage_metrics(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current billing period usage metrics (API requests, AI tokens, reports, etc.)
    """
    return await tenant_service.get_usage_metrics(db, org_id=tenant_ctx.organization_id)
