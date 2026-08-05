from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.models import Campaign as CampaignModel
from app.schemas.schemas import MetricSummaryResponse

router = APIRouter()

@router.get("/metrics", response_model=MetricSummaryResponse, tags=["Metrics"])
async def get_metrics(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CampaignModel))
    campaigns = result.scalars().all()

    if not campaigns:
        return MetricSummaryResponse()

    total_spend = sum(c.spend for c in campaigns)
    total_revenue = sum(c.revenue for c in campaigns)
    total_purchases = sum(c.purchases for c in campaigns)
    total_clicks = sum(c.clicks for c in campaigns)
    total_impressions = sum(c.impressions for c in campaigns)
    total_reach = sum(c.reach for c in campaigns)
    total_budget = sum(c.daily_budget for c in campaigns)

    roas = round(total_revenue / total_spend, 2) if total_spend > 0 else 0.0
    cpa = round(total_spend / total_purchases, 2) if total_purchases > 0 else 0.0
    ctr = round(sum(c.ctr for c in campaigns) / len(campaigns), 2) if campaigns else 0.0

    return MetricSummaryResponse(
        spend=total_spend,
        revenue=total_revenue,
        roas=roas,
        ctr=ctr,
        cpm=round(sum(c.cpm for c in campaigns) / len(campaigns), 2) if campaigns else 0.0,
        cpc=round(sum(c.cpc for c in campaigns) / len(campaigns), 2) if campaigns else 0.0,
        cpa=cpa,
        purchases=total_purchases,
        clicks=total_clicks,
        impressions=total_impressions,
        reach=total_reach,
        budget=total_budget,
        pixel_health="optimal",
        conversion_api_health="optimal"
    )
