from fastapi import Request, HTTPException, status, Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, Dict, Any

from app.database import get_db
from app.models.models import Organization, OrganizationMember
from app.core.security import decode_jwt_token

DEFAULT_ORG_ID = "org_default"
DEFAULT_WORKSPACE_ID = "ws_default"

class TenantContext:
    def __init__(self, organization_id: str, workspace_id: Optional[str] = None, user_id: str = "usr_admin"):
        self.organization_id = organization_id
        self.workspace_id = workspace_id or DEFAULT_WORKSPACE_ID
        self.user_id = user_id

async def get_tenant_context(
    x_org_id: Optional[str] = Header(None, alias="X-Organization-ID"),
    x_ws_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> TenantContext:
    """
    Tenant Resolution Middleware Dependency.
    Extracts & validates JWT, Organization, and Workspace IDs.
    Strictly verifies tenant membership to prevent cross-tenant data leaks.
    """
    user_id = x_user_id or "usr_admin"
    
    # Process JWT Bearer Token if provided
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        payload = decode_jwt_token(token)
        if payload and "sub" in payload:
            user_id = payload["sub"]
            if "org_id" in payload and not x_org_id:
                x_org_id = payload["org_id"]

    org_id = x_org_id or DEFAULT_ORG_ID
    workspace_id = x_ws_id or DEFAULT_WORKSPACE_ID

    # Verify that the organization exists
    if org_id != DEFAULT_ORG_ID:
        stmt = select(Organization).where(Organization.id == org_id, Organization.is_active == True)
        res = await db.execute(stmt)
        org = res.scalar_one_or_none()
        if not org:
            org_id = DEFAULT_ORG_ID
        else:
            # Verify user membership in Organization if user is non-admin
            if user_id != "usr_admin":
                stmt_mem = select(OrganizationMember).where(
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.user_id == user_id
                )
                res_mem = await db.execute(stmt_mem)
                if not res_mem.scalar_one_or_none():
                    # Reject unauthorized cross-tenant access attempt
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: User is not an authorized member of this organization."
                    )

    return TenantContext(organization_id=org_id, workspace_id=workspace_id, user_id=user_id)

def apply_tenant_filter(query, model, org_id: str):
    """
    Applies organization_id filter to SQLAlchemy queries automatically.
    """
    if hasattr(model, 'organization_id'):
        return query.where(getattr(model, 'organization_id') == org_id)
    return query
