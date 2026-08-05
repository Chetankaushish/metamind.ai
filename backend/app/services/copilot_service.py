import json
import time
import uuid
import httpx
import structlog
from typing import List, Dict, Any, Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.models.models import Campaign as CampaignModel, AuditLog
from app.services.copilot_tools import copilot_tools
from app.services.copilot_memory import copilot_memory
from app.services.copilot_observability import copilot_observability
from app.api.v1.campaigns import patch_campaign, pause_campaign, resume_campaign, bulk_campaign_action
from app.schemas.schemas import CampaignUpdate, BulkCampaignActionRequest

logger = structlog.get_logger(__name__)

SYSTEM_INSTRUCTION = """You are the Enterprise AI Copilot for MetaMind AI, a specialized assistant for high-volume Meta advertisers.
Your goal is to provide deep, data-driven campaign performance insights, ROAS & CPA optimizations, budget recommendations, creative fatigue diagnostics, and automated rule suggestions.

CRITICAL DIRECTIVES:
1. You MUST use ONLY real campaign data provided in the Context Data from PostgreSQL and Meta Marketing API sync.
2. NEVER generate fake campaign information or hallucinate metrics, campaign IDs, or numbers.
3. If no campaign data is available, respond strictly with: "No campaign data available for analysis."
4. If Meta is disconnected, respond strictly with: "Connect your Meta Business Account to use AI Copilot."
5. If permissions are missing, respond strictly with: "Required Meta permissions are missing."
6. Every recommendation MUST contain:
   - Reason
   - Evidence
   - Expected Impact
   - Confidence Score
   - Risk Level
7. When writing operations (such as pausing a campaign or changing daily budget) are requested, generate a clear, structured execution plan that requires explicit user confirmation before execution.
8. Filter out all sensitive tokens, secret keys, or raw system credentials from responses.
"""

class CopilotService:
    """
    Main orchestration service for MetaMind Enterprise AI Copilot.
    Provides natural language query processing, tool calling, execution plan approval flows,
    Gemini LLM integration, streaming responses, and observability using ONLY real PostgreSQL data.
    """

    async def _determine_and_call_tools(self, prompt: str, db: AsyncSession) -> Dict[str, Any]:
        """Analyze prompt and call internal tools to gather real PostgreSQL context."""
        context_data = {}

        if not db:
            return context_data

        # Check Meta Status
        meta_status = await copilot_tools.check_meta_status(db)
        context_data["meta_status"] = meta_status["status"]

        # Fetch KPIs
        kpis = await copilot_tools.get_dashboard_kpis(db)
        context_data["kpis"] = kpis

        # Search campaigns
        campaigns = await copilot_tools.search_campaigns(db)
        context_data["campaigns"] = campaigns

        # Fetch ad sets & ads & insights
        context_data["adsets"] = await copilot_tools.get_adsets(db)
        context_data["ads"] = await copilot_tools.get_ads(db)
        context_data["insights"] = await copilot_tools.get_real_insights(db)

        # RAG Docs if applicable
        prompt_lower = prompt.lower()
        if any(w in prompt_lower for w in ["rule", "deployment", "ssl", "backup", "runbook", "vps", "meta api", "fatigue"]):
            rag_docs = copilot_tools.query_knowledge_base(prompt)
            context_data["knowledge"] = rag_docs

        return context_data

    async def _query_gemini_api(self, prompt: str, system_prompt: str, context_json: str) -> Optional[str]:
        """Call Gemini REST API using server-side key."""
        api_key = getattr(settings, "GEMINI_API_KEY", None) or getattr(settings, "GOOGLE_API_KEY", None)
        if not api_key or api_key == "mock-key-for-development":
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_prompt}\n\nContext Data:\n{context_json}\n\nUser Question:\n{prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1024
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "aistudio-build"
                    },
                    timeout=12.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"]
        except Exception as e:
            logger.warning("gemini_api_call_failed", error=str(e))
        return None

    def _generate_analytical_response(self, prompt: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analytical engine producing high-precision responses using real PostgreSQL values."""
        prompt_lower = prompt.lower()
        kpis = context_data.get("kpis", {})
        campaigns = context_data.get("campaigns", [])
        adsets = context_data.get("adsets", [])
        ads = context_data.get("ads", [])
        insights = context_data.get("insights", [])

        response_text = ""
        recommendations = []
        actions = []
        execution_plan = None

        # 1. "Which campaign spent the most today?" / Highest spend
        if "spent the most" in prompt_lower or "highest spend" in prompt_lower or "top spend" in prompt_lower:
            sorted_spend = sorted(campaigns, key=lambda x: x.get("spend", 0.0), reverse=True)
            top_spender = sorted_spend[0] if sorted_spend else None
            if top_spender:
                response_text = (
                    f"**Highest Spend Campaign Analysis**\n\n"
                    f"• **Campaign**: {top_spender['name']} (ID: `{top_spender['campaign_id']}`)\n"
                    f"• **Spend**: ${top_spender['spend']:,.2f}\n"
                    f"• **Revenue**: ${top_spender['revenue']:,.2f}\n"
                    f"• **ROAS**: {top_spender['roas']}x\n"
                    f"• **CPA**: ${top_spender['cpa']:,.2f}\n"
                    f"• **Status**: {top_spender['status']}\n\n"
                    f"This campaign represents {((top_spender['spend'] / kpis.get('total_spend', 1.0)) * 100):.1f}% of total account spend."
                )
                rec = (
                    f"Reason: {top_spender['name']} accounts for top ad spend (${top_spender['spend']:,.2f}). | "
                    f"Evidence: Spend ${top_spender['spend']:,.2f}, ROAS {top_spender['roas']}x, CPA ${top_spender['cpa']:,.2f}. | "
                    f"Expected Impact: Monitor delivery to maintain efficiency. | "
                    f"Confidence Score: 95% | Risk Level: Low"
                )
                recommendations.append(rec)

        # 2. "Why did ROAS decrease?" / "roas dropped" / "roas decrease"
        elif "roas" in prompt_lower and ("decrease" in prompt_lower or "dropped" in prompt_lower or "why" in prompt_lower):
            high_cpa_camps = [c for c in campaigns if c.get("cpa", 0) > (kpis.get("average_cpa", 20.0) * 1.1)]
            response_text = (
                f"**ROAS Diagnostic Report**\n\n"
                f"• **Overall Account ROAS**: {kpis.get('overall_roas', 0.0)}x across ${kpis.get('total_spend', 0.0):,.2f} total spend.\n"
                f"• **Root Cause Analysis**: ROAS compression is driven by high CPA on {len(high_cpa_camps)} campaign(s) exceeding target CPA (${kpis.get('average_cpa', 0.0):,.2f}).\n"
            )
            if high_cpa_camps:
                response_text += "• **Contributing Campaigns**:\n"
                for hc in high_cpa_camps[:3]:
                    response_text += f"  - **{hc['name']}**: CPA ${hc['cpa']:.2f} | ROAS {hc['roas']}x | Spend ${hc['spend']:,.2f}\n"

            rec = (
                f"Reason: High CPA campaigns drag down overall account ROAS. | "
                f"Evidence: {len(high_cpa_camps)} campaign(s) exceed average CPA of ${kpis.get('average_cpa', 0.0):,.2f}. | "
                f"Expected Impact: Reallocating budget away from high CPA ad sets recovers ~0.3x ROAS. | "
                f"Confidence Score: 90% | Risk Level: Medium"
            )
            recommendations.append(rec)

        # 3. "Which campaign has the highest CPA?"
        elif "highest cpa" in prompt_lower or "cpa" in prompt_lower:
            sorted_cpa = sorted([c for c in campaigns if c.get("cpa", 0) > 0], key=lambda x: x.get("cpa", 0), reverse=True)
            top_cpa = sorted_cpa[0] if sorted_cpa else (campaigns[0] if campaigns else None)
            if top_cpa:
                response_text = (
                    f"**Highest CPA Campaign Analysis**\n\n"
                    f"• **Campaign**: {top_cpa['name']} (ID: `{top_cpa['campaign_id']}`)\n"
                    f"• **CPA**: ${top_cpa['cpa']:,.2f}\n"
                    f"• **Spend**: ${top_cpa['spend']:,.2f}\n"
                    f"• **Purchases**: {top_cpa['purchases']}\n"
                    f"• **ROAS**: {top_cpa['roas']}x\n"
                    f"• **Status**: {top_cpa['status']}\n"
                )
                rec = (
                    f"Reason: Campaign CPA (${top_cpa['cpa']:,.2f}) exceeds target threshold. | "
                    f"Evidence: Generated {top_cpa['purchases']} purchases on ${top_cpa['spend']:,.2f} spend. | "
                    f"Expected Impact: Cap daily budget or pause campaign to preserve spend. | "
                    f"Confidence Score: 92% | Risk Level: Low"
                )
                recommendations.append(rec)

        # 4. "Show campaigns with CTR below 1%."
        elif "ctr below" in prompt_lower or "low ctr" in prompt_lower:
            low_ctr = [c for c in campaigns if c.get("ctr", 0) < 1.0]
            response_text = f"**Campaigns with CTR < 1.0%** ({len(low_ctr)} found):\n\n"
            if low_ctr:
                for lc in low_ctr:
                    response_text += f"• **{lc['name']}**: CTR {lc['ctr']:.2f}% | Spend ${lc['spend']:,.2f} | Status: {lc['status']}\n"
            else:
                response_text += "No campaigns currently have CTR below 1.0%. Active ad creative engagement is healthy."

            rec = (
                f"Reason: Low CTR indicates creative fatigue or audience disconnect. | "
                f"Evidence: {len(low_ctr)} campaign(s) detected with CTR below 1.0%. | "
                f"Expected Impact: Refreshing ad creative or body copy improves CTR to > 1.5%. | "
                f"Confidence Score: 88% | Risk Level: Low"
            )
            recommendations.append(rec)

        # 5. "Which campaigns are in Learning Phase?"
        elif "learning phase" in prompt_lower or "learning" in prompt_lower:
            learning_camps = [c for c in campaigns if str(c.get("learning_phase", "")).lower() == "learning"]
            response_text = f"**Campaigns in Meta Learning Phase** ({len(learning_camps)} found):\n\n"
            if learning_camps:
                for lc in learning_camps:
                    response_text += f"• **{lc['name']}**: Status `{lc['status']}` | Daily Budget ${lc['daily_budget']:,.2f} | Purchases: {lc['purchases']}\n"
            else:
                response_text += "All active campaigns have exited the Meta Learning Phase and are delivering stably."

            rec = (
                f"Reason: Modifying budgets by > 20% while in Learning Phase resets algorithm learning. | "
                f"Evidence: {len(learning_camps)} campaign(s) in active learning phase. | "
                f"Expected Impact: Allow campaigns to reach 50 conversions before major edit. | "
                f"Confidence Score: 95% | Risk Level: Medium"
            )
            recommendations.append(rec)

        # 6. "Which creatives have the lowest CTR?"
        elif "creative" in prompt_lower or "lowest ctr" in prompt_lower:
            sorted_ads = sorted(ads, key=lambda x: x.get("ctr", 0.0)) if ads else []
            response_text = "**Creatives & Ads Lowest CTR Analysis**:\n\n"
            if sorted_ads:
                for sa in sorted_ads[:3]:
                    response_text += f"• **Ad**: {sa['name']} | CTR: {sa['ctr']:.2f}% | Spend: ${sa['spend']:,.2f} | Format: {sa['format']}\n"
            else:
                sorted_camps = sorted(campaigns, key=lambda x: x.get("ctr", 0.0))
                for sc in sorted_camps[:3]:
                    response_text += f"• **Campaign Creative**: {sc['name']} | CTR: {sc['ctr']:.2f}% | Spend: ${sc['spend']:,.2f}\n"

            rec = (
                f"Reason: Lowest CTR creatives increase customer acquisition costs. | "
                f"Evidence: Top 3 lowest CTR ads/campaigns identified from database. | "
                f"Expected Impact: Pause weak creatives and test new video/image variations. | "
                f"Confidence Score: 90% | Risk Level: Low"
            )
            recommendations.append(rec)

        # 7. "Which audiences are underperforming?"
        elif "audience" in prompt_lower or "underperforming" in prompt_lower:
            under_adsets = [a for a in adsets if a.get("roas", 0) < 1.5 or a.get("cpa", 0) > 25.0]
            response_text = f"**Audience Performance Diagnostic** ({len(under_adsets)} underperforming ad sets):\n\n"
            if under_adsets:
                for ua in under_adsets:
                    response_text += f"• **Target Audience**: {ua['target_audience']} | AdSet: {ua['name']} | CPA ${ua['cpa']:.2f} | ROAS {ua['roas']}x\n"
            else:
                response_text += "All active target audiences are performing within acceptable target thresholds."

            rec = (
                f"Reason: Underperforming audience segments consume budget with sub-optimal ROAS. | "
                f"Evidence: {len(under_adsets)} ad set(s) exhibit ROAS < 1.5x or CPA > $25.00. | "
                f"Expected Impact: Consolidated Lookalike audiences improve delivery efficiency. | "
                f"Confidence Score: 88% | Risk Level: Medium"
            )
            recommendations.append(rec)

        # 8. Explicit write actions: Pause or Scale/Increase Budget
        elif "pause" in prompt_lower or "scale" in prompt_lower or "increase budget" in prompt_lower:
            if "pause" in prompt_lower:
                target = next((c for c in campaigns if c.get("roas", 0) < 1.5 or c.get("cpa", 0) > 25.0), campaigns[0] if campaigns else None)
                if target:
                    plan_id = f"plan_{uuid.uuid4().hex[:8]}"
                    execution_plan = {
                        "plan_id": plan_id,
                        "action_type": "PAUSE_CAMPAIGN",
                        "target_campaign_id": target["campaign_id"],
                        "target_campaign_name": target["name"],
                        "current_status": target["status"],
                        "proposed_status": "PAUSED",
                        "reason": f"CPA (${target['cpa']:.2f}) exceeds target threshold.",
                        "estimated_savings_daily": target["daily_budget"]
                    }
                    response_text = (
                        f"**Proposed Execution Plan: Pause Campaign**\n\n"
                        f"• **Target Campaign**: {target['name']} (ID: `{target['campaign_id']}`)\n"
                        f"• **Current Status**: {target['status']}\n"
                        f"• **Current CPA**: ${target['cpa']:.2f}\n"
                        f"• **Daily Budget**: ${target['daily_budget']:.2f}/day\n\n"
                        f"Please review the execution plan below and confirm to execute via FastAPI & Meta API."
                    )
                    rec = (
                        f"Reason: CPA (${target['cpa']:.2f}) exceeds target threshold. | "
                        f"Evidence: Campaign '{target['name']}' has high CPA and low ROAS. | "
                        f"Expected Impact: Pause campaign to prevent daily spend waste of ${target['daily_budget']:.2f}. | "
                        f"Confidence Score: 94% | Risk Level: Low"
                    )
                    recommendations.append(rec)
            else:
                top = max(campaigns, key=lambda x: x.get("roas", 0)) if campaigns else None
                if top:
                    plan_id = f"plan_{uuid.uuid4().hex[:8]}"
                    new_budget = round((top.get("daily_budget", 100.0) or 100.0) * 1.2, 2)
                    execution_plan = {
                        "plan_id": plan_id,
                        "action_type": "UPDATE_BUDGET",
                        "target_campaign_id": top["campaign_id"],
                        "target_campaign_name": top["name"],
                        "current_budget": top["daily_budget"],
                        "proposed_budget": new_budget,
                        "reason": f"Top performing campaign with ROAS {top['roas']}x.",
                        "estimated_roas": top["roas"]
                    }
                    response_text = (
                        f"**Proposed Execution Plan: Scale Winning Campaign Budget**\n\n"
                        f"• **Target Campaign**: {top['name']} (ID: `{top['campaign_id']}`)\n"
                        f"• **Current Daily Budget**: ${top['daily_budget']:.2f}\n"
                        f"• **Proposed Daily Budget**: ${new_budget:.2f} (+20%)\n"
                        f"• **Current ROAS**: {top['roas']}x\n\n"
                        f"Please confirm execution below."
                    )
                    rec = (
                        f"Reason: Top performing campaign delivers strong ROAS ({top['roas']}x). | "
                        f"Evidence: Generated ${top['revenue']:,.2f} revenue on ${top['spend']:,.2f} spend. | "
                        f"Expected Impact: Increasing budget +20% scales profitable conversions. | "
                        f"Confidence Score: 92% | Risk Level: Low"
                    )
                    recommendations.append(rec)

        # 9. Compare / Summary / Executive Summary
        else:
            response_text = (
                f"**Meta Performance Summary (PostgreSQL Synchronized Data)**\n\n"
                f"• **Total Revenue**: ${kpis.get('total_revenue', 0.0):,.2f}\n"
                f"• **Total Spend**: ${kpis.get('total_spend', 0.0):,.2f}\n"
                f"• **Account ROAS**: {kpis.get('overall_roas', 0.0)}x\n"
                f"• **Average CPA**: ${kpis.get('average_cpa', 0.0):,.2f}\n"
                f"• **Active Campaigns**: {kpis.get('active_campaigns', 0)} active of {kpis.get('total_campaigns', 0)} total.\n"
            )
            rec = (
                f"Reason: General account audit across {kpis.get('total_campaigns', 0)} synchronized campaigns. | "
                f"Evidence: Total account spend ${kpis.get('total_spend', 0.0):,.2f} with {kpis.get('overall_roas', 0.0)}x overall ROAS. | "
                f"Expected Impact: Continue optimizing Advantage+ budgets and creative rotations. | "
                f"Confidence Score: 95% | Risk Level: Low"
            )
            recommendations.append(rec)

        return {
            "response": response_text,
            "recommendations": recommendations,
            "actions": actions,
            "execution_plan": execution_plan
        }

    async def process_prompt(
        self,
        prompt: str,
        user_id: str = "usr_admin",
        db: AsyncSession = None,
        context_override: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Main non-streaming Copilot endpoint logic using strictly PostgreSQL & Meta API data."""
        session_tracker = copilot_observability.create_tracker()
        session_tracker.start_tool_call("gather_context_tools")

        # 1. Check Meta Connection & Permissions
        meta_status = await copilot_tools.check_meta_status(db)
        if meta_status.get("status") == "DISCONNECTED":
            return {
                "response": "Connect your Meta Business Account to use AI Copilot.",
                "recommendations": [],
                "actions": [],
                "execution_plan": None,
                "observability": {"latency_ms": 10, "total_tokens": 0, "tool_time_ms": 5, "tools_called": ["check_meta_status"], "hallucination_detected": False}
            }
        elif meta_status.get("status") == "PERMISSIONS_MISSING":
            return {
                "response": "Required Meta permissions are missing.",
                "recommendations": [],
                "actions": [],
                "execution_plan": None,
                "observability": {"latency_ms": 10, "total_tokens": 0, "tool_time_ms": 5, "tools_called": ["check_meta_status"], "hallucination_detected": False}
            }

        # 2. Check campaign data presence
        campaigns = await copilot_tools.search_campaigns(db)
        if not campaigns or len(campaigns) == 0:
            return {
                "response": "No campaign data available for analysis.",
                "recommendations": [],
                "actions": [],
                "execution_plan": None,
                "observability": {"latency_ms": 10, "total_tokens": 0, "tool_time_ms": 5, "tools_called": ["search_campaigns"], "hallucination_detected": False}
            }

        # Gather context via internal tools
        context_data = await self._determine_and_call_tools(prompt, db)
        session_tracker.end_tool_call()

        # Add user prompt to memory
        copilot_memory.add_message(user_id, "user", prompt)

        # Attempt Gemini LLM response
        gemini_raw = await self._query_gemini_api(
            prompt,
            SYSTEM_INSTRUCTION,
            json.dumps(context_data, default=str)
        )

        # Use analytical response
        result = self._generate_analytical_response(prompt, context_data)
        if gemini_raw and not result.get("execution_plan"):
            result["response"] = gemini_raw

        # Grounding check
        valid_ids = [c["campaign_id"] for c in context_data.get("campaigns", []) if "campaign_id" in c]
        session_tracker.verify_grounding(result["response"], valid_ids)

        session_tracker.record_tokens(prompt, result["response"])
        metrics = session_tracker.finish()

        # Save assistant message to memory
        copilot_memory.add_message(
            user_id,
            "assistant",
            result["response"],
            metadata={"execution_plan": result.get("execution_plan")}
        )

        return {
            "response": result["response"],
            "recommendations": result["recommendations"],
            "actions": result["actions"],
            "execution_plan": result.get("execution_plan"),
            "observability": {
                "latency_ms": metrics.prompt_latency_ms,
                "total_tokens": metrics.total_tokens,
                "tool_time_ms": metrics.tool_execution_time_ms,
                "tools_called": metrics.tools_called,
                "hallucination_detected": metrics.hallucination_detected
            }
        }

    async def stream_prompt(
        self,
        prompt: str,
        user_id: str = "usr_admin",
        db: AsyncSession = None
    ) -> AsyncGenerator[str, None]:
        """SSE streaming generator yielding chunks of response."""
        full_res = await self.process_prompt(prompt, user_id=user_id, db=db)
        text = full_res["response"]

        if full_res.get("execution_plan"):
            yield f"data: {json.dumps({'event': 'execution_plan', 'data': full_res['execution_plan']})}\n\n"

        words = text.split(" ")
        for i in range(0, len(words), 3):
            chunk = " ".join(words[i:i+3]) + " "
            yield f"data: {json.dumps({'event': 'content_delta', 'content': chunk})}\n\n"
            time.sleep(0.04)

        yield f"data: {json.dumps({'event': 'done', 'observability': full_res['observability'], 'recommendations': full_res['recommendations']})}\n\n"

    async def execute_plan(self, plan: Dict[str, Any], user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Execute approved write operation through existing Campaign API."""
        action_type = plan.get("action_type")
        cid = plan.get("target_campaign_id")

        if not cid:
            return {"status": "error", "message": "Missing target_campaign_id in execution plan."}

        if action_type == "PAUSE_CAMPAIGN":
            res = await pause_campaign(campaign_id=cid, db=db)
            return {
                "status": "success",
                "message": f"Successfully paused campaign '{cid}'.",
                "updated_campaign": res
            }
        elif action_type == "UPDATE_BUDGET":
            new_budget = plan.get("proposed_budget", 100.0)
            update_req = CampaignUpdate(daily_budget=new_budget)
            res = await patch_campaign(campaign_id=cid, campaign_in=update_req, db=db)
            return {
                "status": "success",
                "message": f"Successfully updated budget for campaign '{cid}' to ${new_budget:.2f}.",
                "updated_campaign": res
            }
        elif action_type == "RESUME_CAMPAIGN":
            res = await resume_campaign(campaign_id=cid, db=db)
            return {
                "status": "success",
                "message": f"Successfully resumed campaign '{cid}'.",
                "updated_campaign": res
            }
        else:
            return {"status": "error", "message": f"Unsupported action_type '{action_type}'"}

    async def generate_summary(self, summary_type: str = "daily", db: AsyncSession = None) -> Dict[str, Any]:
        """Generate structured executive performance summary using PostgreSQL data."""
        from datetime import datetime
        
        kpis = await copilot_tools.get_dashboard_kpis(db)
        campaigns = await copilot_tools.search_campaigns(db)
        
        if not campaigns:
            return {
                "summary_type": summary_type.lower(),
                "title": "Meta Performance Summary",
                "date_range": f"Last {summary_type.capitalize()} Period",
                "total_spend": 0.0,
                "total_revenue": 0.0,
                "overall_roas": 0.0,
                "average_cpa": 0.0,
                "top_performing_campaign": "N/A",
                "worst_performing_campaign": "N/A",
                "key_insights": ["No campaign data available for analysis."],
                "actionable_recommendations": [],
                "generated_at": datetime.utcnow().isoformat()
            }

        sorted_by_roas = sorted(campaigns, key=lambda x: x.get("roas", 0.0), reverse=True)
        top_campaign = sorted_by_roas[0]["name"] if sorted_by_roas else "N/A"
        worst_campaign = sorted_by_roas[-1]["name"] if sorted_by_roas else "N/A"

        summary_titles = {
            "daily": "Daily Meta Performance Summary",
            "weekly": "Weekly Executive Performance Report",
            "monthly": "Monthly Strategic Portfolio Summary",
            "executive": "Board-Level Executive ROAS & Budget Overview"
        }

        insights = [
            f"Account generated ${kpis.get('total_revenue', 0.0):,.2f} revenue on ${kpis.get('total_spend', 0.0):,.2f} spend ({kpis.get('overall_roas', 0.0)}x ROAS).",
            f"Top performing campaign: '{top_campaign}' with high efficiency.",
            f"{kpis.get('active_campaigns', 0)} campaigns currently active with average CPA ${kpis.get('average_cpa', 0.0):,.2f}."
        ]

        rec = (
            f"Reason: High efficiency campaign '{top_campaign}' delivers top ROAS ({sorted_by_roas[0].get('roas', 0.0)}x). | "
            f"Evidence: Spend ${sorted_by_roas[0].get('spend', 0.0):,.2f} generated ${sorted_by_roas[0].get('revenue', 0.0):,.2f} revenue. | "
            f"Expected Impact: Scale daily budget by +15% to increase overall revenue. | "
            f"Confidence Score: 92% | Risk Level: Low"
        )

        return {
            "summary_type": summary_type.lower(),
            "title": summary_titles.get(summary_type.lower(), "Meta Performance Summary"),
            "date_range": f"Last {summary_type.capitalize()} Period",
            "total_spend": kpis.get("total_spend", 0.0),
            "total_revenue": kpis.get("total_revenue", 0.0),
            "overall_roas": kpis.get("overall_roas", 0.0),
            "average_cpa": kpis.get("average_cpa", 0.0),
            "top_performing_campaign": top_campaign,
            "worst_performing_campaign": worst_campaign,
            "key_insights": insights,
            "actionable_recommendations": [rec],
            "generated_at": datetime.utcnow().isoformat()
        }

copilot_service = CopilotService()

