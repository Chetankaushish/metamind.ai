from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.schemas.schemas import (
    CopilotRequest,
    CopilotResponse,
    CopilotExecutePlanRequest,
    CopilotContextUpdateRequest,
    CopilotSummaryRequest,
    CopilotSummaryResponse
)
from app.services.copilot_service import copilot_service
from app.services.copilot_memory import copilot_memory
from app.services.rbac_service import get_user_permissions

router = APIRouter(prefix="/copilot", tags=["AI Copilot"])

@router.post("", response_model=CopilotResponse)
@router.post("/chat", response_model=CopilotResponse)
async def run_copilot(
    req: CopilotRequest,
    x_user_id: Optional[str] = Header("usr_admin", alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Process natural language queries for campaign performance analysis, ROAS optimization,
    CPA diagnostics, and automated budget scaling recommendations.
    """
    res = await copilot_service.process_prompt(
        prompt=req.prompt,
        user_id=x_user_id or "usr_admin",
        db=db,
        context_override=req.context
    )
    return CopilotResponse(
        response=res["response"],
        recommendations=res["recommendations"],
        actions=res["actions"],
        execution_plan=res.get("execution_plan"),
        observability=res.get("observability")
    )

@router.post("/stream")
async def stream_copilot(
    req: CopilotRequest,
    x_user_id: Optional[str] = Header("usr_admin", alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Stream Copilot response chunk-by-chunk via Server-Sent Events (SSE).
    Supports execution plan event broadcasting and token streaming.
    """
    generator = copilot_service.stream_prompt(
        prompt=req.prompt,
        user_id=x_user_id or "usr_admin",
        db=db
    )
    return StreamingResponse(generator, media_type="text/event-stream")

@router.post("/execute-plan")
async def execute_copilot_plan(
    req: CopilotExecutePlanRequest,
    x_user_id: Optional[str] = Header("usr_admin", alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Execute a user-confirmed write plan through existing Campaign API.
    Enforces RBAC authorization and generates audit logs.
    """
    user_id = x_user_id or "usr_admin"
    
    # Check RBAC authorization
    perms = await get_user_permissions(user_id, db)
    # Default admin user has all permissions
    if perms and not any(p in perms for p in ["manage_campaigns", "pause_campaigns", "edit_budgets"]):
        if user_id != "usr_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="RBAC permission denied: Action requires 'manage_campaigns' or 'edit_budgets' permission."
            )

    result = await copilot_service.execute_plan(plan=req.plan, user_id=user_id, db=db)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    
    return result

@router.get("/context")
async def get_copilot_context(
    x_user_id: Optional[str] = Header("usr_admin", alias="X-User-ID")
):
    """
    Get user memory state including conversation history, preferences,
    recent campaigns viewed, and pinned campaigns.
    """
    user_id = x_user_id or "usr_admin"
    return {
        "history": copilot_memory.get_history(user_id),
        "preferences": copilot_memory.get_preferences(user_id),
        "recent_campaigns": copilot_memory.get_recent_campaigns(user_id),
        "pinned_campaigns": copilot_memory.get_pinned_campaigns(user_id)
    }

@router.post("/context")
async def update_copilot_context(
    req: CopilotContextUpdateRequest,
    x_user_id: Optional[str] = Header("usr_admin", alias="X-User-ID")
):
    """
    Update user preferences or toggle pinned campaigns.
    """
    user_id = x_user_id or "usr_admin"
    
    updated_prefs = None
    if req.preferences:
        updated_prefs = copilot_memory.update_preferences(user_id, req.preferences)

    pinned = None
    if req.pinned_campaign_id and req.pinned_campaign_name:
        pinned = copilot_memory.toggle_pin_campaign(user_id, req.pinned_campaign_id, req.pinned_campaign_name)

    return {
        "preferences": updated_prefs or copilot_memory.get_preferences(user_id),
        "pinned_campaigns": pinned or copilot_memory.get_pinned_campaigns(user_id)
    }

@router.get("/history")
async def get_copilot_history(
    x_user_id: Optional[str] = Header("usr_admin", alias="X-User-ID")
):
    """Retrieve conversation history memory for the current session."""
    user_id = x_user_id or "usr_admin"
    return {
        "user_id": user_id,
        "history": copilot_memory.get_history(user_id)
    }

@router.delete("/history")
async def clear_copilot_history(
    x_user_id: Optional[str] = Header("usr_admin", alias="X-User-ID")
):
    """Clear conversation history memory for the current session."""
    user_id = x_user_id or "usr_admin"
    copilot_memory.clear_history(user_id)
    return {"status": "success", "message": "Conversation history cleared."}

@router.get("/summaries", response_model=CopilotSummaryResponse)
@router.post("/summaries", response_model=CopilotSummaryResponse)
async def get_copilot_summary(
    req: Optional[CopilotSummaryRequest] = None,
    summary_type: str = "daily",
    db: AsyncSession = Depends(get_db)
):
    """
    Generate structured executive performance summary (Daily, Weekly, Monthly, Executive).
    Reuses existing PostgreSQL metrics and campaign tools.
    """
    type_to_use = req.summary_type if req and req.summary_type else summary_type
    summary_data = await copilot_service.generate_summary(summary_type=type_to_use, db=db)
    return CopilotSummaryResponse(**summary_data)
