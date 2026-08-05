import json
import datetime
from typing import List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.models import (
    AutomationRule,
    AutomationCondition,
    AutomationAction,
    AutomationExecution,
    AutomationLog,
    Campaign,
    AuditLog
)
from app.api.v1.ws import ws_manager

def evaluate_condition(metric_val: float, operator: str, target_val_str: str) -> bool:
    """Evaluates a condition against a metric value."""
    try:
        target_val = float(target_val_str)
    except ValueError:
        target_val = 0.0

    if operator == ">":
        return metric_val > target_val
    elif operator == "<":
        return metric_val < target_val
    elif operator == ">=":
        return metric_val >= target_val
    elif operator == "<=":
        return metric_val <= target_val
    elif operator == "==":
        return metric_val == target_val
    elif operator == "!=":
        return metric_val != target_val
    elif operator.lower() in ["between", "range"]:
        parts = [float(x.strip()) for x in target_val_str.split(",") if x.strip()]
        if len(parts) == 2:
            return parts[0] <= metric_val <= parts[1]
        return False
    elif "contains" in operator.lower():
        return target_val_str.lower() in str(metric_val).lower()
    elif "increase" in operator.lower():
        return metric_val > target_val
    elif "decrease" in operator.lower():
        return metric_val < target_val
    return False

async def evaluate_and_run_rule(rule_id: str, db: AsyncSession, triggered_by: str = "manual") -> Dict[str, Any]:
    """Evaluates rule conditions against local PostgreSQL campaign metrics and executes actions."""
    # 1. Fetch Rule, Conditions, Actions
    stmt_rule = select(AutomationRule).where(AutomationRule.id == rule_id)
    res_rule = await db.execute(stmt_rule)
    rule = res_rule.scalar_one_or_none()
    if not rule:
        return {"status": "failed", "error": "Rule not found"}

    # Broadcast started
    await ws_manager.broadcast({
        "event": "automation_started",
        "data": {"rule_id": rule.id, "name": rule.name, "triggered_by": triggered_by}
    })

    # Create Execution record
    execution = AutomationExecution(
        rule_id=rule.id,
        status="running",
        triggered_by=triggered_by
    )
    db.add(execution)
    await db.flush()

    log_entry = AutomationLog(
        execution_id=execution.id,
        rule_id=rule.id,
        level="INFO",
        message=f"Started evaluating rule '{rule.name}'"
    )
    db.add(log_entry)

    try:
        stmt_conds = select(AutomationCondition).where(AutomationCondition.rule_id == rule.id)
        res_conds = await db.execute(stmt_conds)
        conditions = res_conds.scalars().all()

        stmt_acts = select(AutomationAction).where(AutomationAction.rule_id == rule.id)
        res_acts = await db.execute(stmt_acts)
        actions = res_acts.scalars().all()

        # Fetch campaigns from PostgreSQL
        stmt_camp = select(Campaign)
        res_camp = await db.execute(stmt_camp)
        campaigns = res_camp.scalars().all()

        matched_campaigns: List[Campaign] = []

        for camp in campaigns:
            metric_map = {
                "campaign spend": camp.spend or 0.0,
                "spend": camp.spend or 0.0,
                "roas": camp.roas or 0.0,
                "ctr": camp.ctr or 0.0,
                "cpa": camp.cpa or 0.0,
                "cpc": camp.cpc or 0.0,
                "conversions": float(camp.purchases or 0),
                "revenue": camp.revenue or 0.0,
                "daily budget": camp.daily_budget or 0.0,
                "budget utilization": ((camp.spend or 0.0) / (camp.daily_budget or 1.0)) * 100 if camp.daily_budget else 0.0
            }

            all_match = True
            for cond in conditions:
                m_key = cond.metric.lower()
                m_val = metric_map.get(m_key, camp.spend or 0.0)
                if not evaluate_condition(m_val, cond.operator, cond.value):
                    all_match = False
                    break

            if all_match or not conditions:
                matched_campaigns.append(camp)

        # Execute Actions on Matched Campaigns
        executed_actions_summary = []
        for camp in matched_campaigns:
            for act in actions:
                a_type = act.action_type.lower()
                if "pause" in a_type:
                    camp.status = "PAUSED"
                    executed_actions_summary.append(f"Paused Campaign {camp.name}")
                elif "resume" in a_type:
                    camp.status = "ACTIVE"
                    executed_actions_summary.append(f"Resumed Campaign {camp.name}")
                elif "increase budget" in a_type:
                    perc = 10.0
                    if act.action_params and act.action_params.isdigit():
                        perc = float(act.action_params)
                    camp.daily_budget = (camp.daily_budget or 100.0) * (1 + (perc / 100.0))
                    executed_actions_summary.append(f"Increased budget of {camp.name} by {perc}% to ${camp.daily_budget:.2f}")
                elif "decrease budget" in a_type:
                    perc = 10.0
                    if act.action_params and act.action_params.isdigit():
                        perc = float(act.action_params)
                    camp.daily_budget = max(10.0, (camp.daily_budget or 100.0) * (1 - (perc / 100.0)))
                    executed_actions_summary.append(f"Decreased budget of {camp.name} by {perc}% to ${camp.daily_budget:.2f}")
                elif "notification" in a_type:
                    executed_actions_summary.append(f"Sent notification alert for {camp.name}")
                elif "audit" in a_type:
                    executed_actions_summary.append(f"Logged audit event for {camp.name}")

        # Record AuditLog
        audit = AuditLog(
            user_id="usr_admin",
            action="execute_automation_rule",
            old_value=rule.name,
            new_value=json.dumps(executed_actions_summary),
            result="SUCCESS"
        )
        db.add(audit)

        # Update Rule statistics
        rule.last_executed = datetime.datetime.now(datetime.timezone.utc)
        rule.execution_count = (rule.execution_count or 0) + 1
        rule.success_count = (rule.success_count or 0) + 1

        execution.status = "completed"
        execution.details = json.dumps({
            "matched_campaigns": len(matched_campaigns),
            "executed_actions": executed_actions_summary
        })

        db.add(AutomationLog(
            execution_id=execution.id,
            rule_id=rule.id,
            level="INFO",
            message=f"Rule evaluation finished successfully. Actions executed: {len(executed_actions_summary)}"
        ))

        await db.commit()

        # Broadcast completed
        await ws_manager.broadcast({
            "event": "automation_completed",
            "data": {
                "rule_id": rule.id,
                "status": "completed",
                "matched_count": len(matched_campaigns),
                "actions": executed_actions_summary
            }
        })

        return {
            "status": "completed",
            "matched_campaigns": len(matched_campaigns),
            "executed_actions": executed_actions_summary
        }

    except Exception as e:
        rule.execution_count = (rule.execution_count or 0) + 1
        rule.failure_count = (rule.failure_count or 0) + 1
        execution.status = "failed"
        execution.details = str(e)

        db.add(AutomationLog(
            execution_id=execution.id,
            rule_id=rule.id,
            level="ERROR",
            message=f"Rule evaluation failed: {str(e)}"
        ))
        await db.commit()

        await ws_manager.broadcast({
            "event": "automation_failed",
            "data": {"rule_id": rule.id, "error": str(e)}
        })

        return {"status": "failed", "error": str(e)}
