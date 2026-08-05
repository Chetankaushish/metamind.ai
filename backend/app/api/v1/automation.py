import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.models import (
    AutomationRule,
    AutomationCondition,
    AutomationAction,
    AutomationExecution,
    AutomationLog,
    AuditLog
)
from app.schemas.schemas import (
    AutomationRuleCreate,
    AutomationRuleUpdate,
    AutomationRuleResponse,
    AutomationExecutionResponse,
    AutomationLogResponse,
    ConditionBase,
    ActionBase
)
from app.services.automation_engine import evaluate_and_run_rule
from app.api.v1.ws import ws_manager

router = APIRouter(prefix="/automation", tags=["Automation & Rule Engine"])

async def _seed_default_rules(db: AsyncSession):
    stmt = select(AutomationRule)
    res = await db.execute(stmt)
    if not res.scalars().first():
        # Seed default rule
        rule1 = AutomationRule(
            name="Low ROAS Campaign Auto-Pause",
            description="Automatically pauses any campaign where ROAS drops below 1.5",
            trigger_type="ROAS",
            is_enabled=True,
            schedule="Daily"
        )
        db.add(rule1)
        await db.flush()

        cond1 = AutomationCondition(
            rule_id=rule1.id,
            metric="ROAS",
            operator="<",
            value="1.5"
        )
        act1 = AutomationAction(
            rule_id=rule1.id,
            action_type="Pause Campaign",
            action_params="Pause low performing campaign"
        )
        db.add(cond1)
        db.add(act1)

        rule2 = AutomationRule(
            name="High Performing Budget Scaler",
            description="Increases daily budget by 15% for campaigns with ROAS > 3.0",
            trigger_type="ROAS",
            is_enabled=True,
            schedule="Daily"
        )
        db.add(rule2)
        await db.flush()

        cond2 = AutomationCondition(
            rule_id=rule2.id,
            metric="ROAS",
            operator=">",
            value="3.0"
        )
        act2 = AutomationAction(
            rule_id=rule2.id,
            action_type="Increase Budget",
            action_params="15"
        )
        db.add(cond2)
        db.add(act2)

        await db.commit()

@router.get("/rules", response_model=List[AutomationRuleResponse])
async def list_rules(db: AsyncSession = Depends(get_db)):
    await _seed_default_rules(db)
    stmt = select(AutomationRule).order_by(AutomationRule.created_at.desc())
    res = await db.execute(stmt)
    rules = res.scalars().all()

    response_list = []
    for r in rules:
        stmt_c = select(AutomationCondition).where(AutomationCondition.rule_id == r.id)
        res_c = await db.execute(stmt_c)
        conds = res_c.scalars().all()

        stmt_a = select(AutomationAction).where(AutomationAction.rule_id == r.id)
        res_a = await db.execute(stmt_a)
        acts = res_a.scalars().all()

        response_list.append(AutomationRuleResponse(
            id=r.id,
            name=r.name,
            description=r.description,
            trigger_type=r.trigger_type,
            is_enabled=r.is_enabled,
            created_by=r.created_by or "usr_admin",
            schedule=r.schedule or "Daily",
            last_executed=r.last_executed,
            execution_count=r.execution_count or 0,
            success_count=r.success_count or 0,
            failure_count=r.failure_count or 0,
            conditions=[ConditionBase(metric=c.metric, operator=c.operator, value=c.value) for c in conds],
            actions=[ActionBase(action_type=a.action_type, action_params=a.action_params) for a in acts],
            created_at=r.created_at
        ))
    return response_list

@router.post("/rules", response_model=AutomationRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(req: AutomationRuleCreate, db: AsyncSession = Depends(get_db)):
    rule = AutomationRule(
        name=req.name,
        description=req.description,
        trigger_type=req.trigger_type,
        schedule=req.schedule,
        is_enabled=True,
        created_by="usr_admin"
    )
    db.add(rule)
    await db.flush()

    cond_objs = []
    for c in req.conditions:
        cond = AutomationCondition(rule_id=rule.id, metric=c.metric, operator=c.operator, value=c.value)
        db.add(cond)
        cond_objs.append(c)

    act_objs = []
    for a in req.actions:
        act = AutomationAction(rule_id=rule.id, action_type=a.action_type, action_params=a.action_params)
        db.add(act)
        act_objs.append(a)

    audit = AuditLog(
        user_id="usr_admin",
        action="create_automation_rule",
        new_value=req.name,
        result="SUCCESS"
    )
    db.add(audit)

    await db.commit()
    await db.refresh(rule)

    return AutomationRuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        trigger_type=rule.trigger_type,
        is_enabled=rule.is_enabled,
        created_by=rule.created_by,
        schedule=rule.schedule,
        last_executed=rule.last_executed,
        execution_count=0,
        success_count=0,
        failure_count=0,
        conditions=cond_objs,
        actions=act_objs,
        created_at=rule.created_at
    )

@router.patch("/rules/{rule_id}", response_model=AutomationRuleResponse)
async def update_rule(rule_id: str, req: AutomationRuleUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(AutomationRule).where(AutomationRule.id == rule_id)
    res = await db.execute(stmt)
    rule = res.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if req.name is not None:
        rule.name = req.name
    if req.description is not None:
        rule.description = req.description
    if req.trigger_type is not None:
        rule.trigger_type = req.trigger_type
    if req.schedule is not None:
        rule.schedule = req.schedule
    if req.is_enabled is not None:
        rule.is_enabled = req.is_enabled

    await db.commit()
    await db.refresh(rule)

    stmt_c = select(AutomationCondition).where(AutomationCondition.rule_id == rule.id)
    res_c = await db.execute(stmt_c)
    conds = res_c.scalars().all()

    stmt_a = select(AutomationAction).where(AutomationAction.rule_id == rule.id)
    res_a = await db.execute(stmt_a)
    acts = res_a.scalars().all()

    return AutomationRuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        trigger_type=rule.trigger_type,
        is_enabled=rule.is_enabled,
        created_by=rule.created_by,
        schedule=rule.schedule,
        last_executed=rule.last_executed,
        execution_count=rule.execution_count or 0,
        success_count=rule.success_count or 0,
        failure_count=rule.failure_count or 0,
        conditions=[ConditionBase(metric=c.metric, operator=c.operator, value=c.value) for c in conds],
        actions=[ActionBase(action_type=a.action_type, action_params=a.action_params) for a in acts],
        created_at=rule.created_at
    )

@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(AutomationRule).where(AutomationRule.id == rule_id)
    res = await db.execute(stmt)
    rule = res.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    await db.delete(rule)
    await db.commit()
    return None

@router.post("/rules/{rule_id}/run")
async def run_rule_now(rule_id: str, db: AsyncSession = Depends(get_db)):
    result = await evaluate_and_run_rule(rule_id, db, triggered_by="manual_ui")
    return result

@router.post("/rules/{rule_id}/enable")
async def enable_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(AutomationRule).where(AutomationRule.id == rule_id)
    res = await db.execute(stmt)
    rule = res.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.is_enabled = True
    await db.commit()

    await ws_manager.broadcast({
        "event": "rule_enabled",
        "data": {"rule_id": rule.id, "name": rule.name}
    })

    return {"status": "enabled", "rule_id": rule.id}

@router.post("/rules/{rule_id}/disable")
async def disable_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(AutomationRule).where(AutomationRule.id == rule_id)
    res = await db.execute(stmt)
    rule = res.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.is_enabled = False
    await db.commit()

    await ws_manager.broadcast({
        "event": "rule_disabled",
        "data": {"rule_id": rule.id, "name": rule.name}
    })

    return {"status": "disabled", "rule_id": rule.id}

@router.get("/history", response_model=List[AutomationExecutionResponse])
async def list_history(db: AsyncSession = Depends(get_db)):
    stmt = select(AutomationExecution).order_by(AutomationExecution.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()
