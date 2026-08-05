from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_db
from app.services.dashboard_service import dashboard_service, DashboardService
from app.schemas.schemas import (
    DashboardOverviewResponse, DashboardKPIsResponse, DashboardChartsResponse,
    TopCampaignItem, TopAdItem, TrendItem, BreakdownItem,
    CampaignComparisonItem, TimePerformanceItem, ComparisonSummaryResponse
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard Aggregations"])

def invalidate_dashboard_cache():
    DashboardService.invalidate_cache()

@router.get("/kpis", response_model=DashboardKPIsResponse)
async def get_dashboard_kpis(
    status: Optional[str] = Query(None),
    objective: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """GET /api/v1/dashboard/kpis - High performance aggregation for core metrics."""
    return await dashboard_service.get_kpis(db=db, status=status, objective=objective)

@router.get("/overview", response_model=DashboardOverviewResponse)
async def get_dashboard_overview(db: AsyncSession = Depends(get_db)):
    """GET /api/v1/dashboard/overview - Complete dashboard metrics, connection state, and last sync info."""
    return await dashboard_service.get_overview(db=db)

@router.get("/charts", response_model=DashboardChartsResponse)
async def get_dashboard_charts(db: AsyncSession = Depends(get_db)):
    """GET /api/v1/dashboard/charts - Time series data points for spend, revenue, ROAS, conversions."""
    return await dashboard_service.get_charts(db=db)

@router.get("/top-campaigns", response_model=List[TopCampaignItem])
async def get_top_campaigns(db: AsyncSession = Depends(get_db)):
    """GET /api/v1/dashboard/top-campaigns - Top performing campaigns ranked by spend & ROAS."""
    return await dashboard_service.get_top_campaigns(db=db)

@router.get("/worst-campaigns", response_model=List[TopCampaignItem])
async def get_worst_campaigns(db: AsyncSession = Depends(get_db)):
    """GET /api/v1/dashboard/worst-campaigns - Underperforming campaigns needing optimization attention."""
    return await dashboard_service.get_worst_campaigns(db=db)

@router.get("/campaign-comparison", response_model=List[CampaignComparisonItem])
async def get_campaign_comparison(db: AsyncSession = Depends(get_db)):
    """GET /api/v1/dashboard/campaign-comparison - Detailed side-by-side metric table for active campaigns."""
    return await dashboard_service.get_campaign_comparison(db=db)

@router.get("/top-ads", response_model=List[TopAdItem])
async def get_top_ads(db: AsyncSession = Depends(get_db)):
    """GET /api/v1/dashboard/top-ads - Top performing ads and creative assets."""
    return await dashboard_service.get_top_ads(db=db)

@router.get("/trends", response_model=List[TrendItem])
async def get_dashboard_trends(db: AsyncSession = Depends(get_db)):
    """GET /api/v1/dashboard/trends - Metric trend comparisons against previous period."""
    return await dashboard_service.get_trends(db=db)

@router.get("/comparison", response_model=ComparisonSummaryResponse)
async def get_period_comparison(db: AsyncSession = Depends(get_db)):
    """GET /api/v1/dashboard/comparison - Current vs Previous period growth percentages."""
    return await dashboard_service.get_period_comparison(db=db)

@router.get("/breakdown/platform", response_model=List[BreakdownItem])
async def get_platform_breakdown(db: AsyncSession = Depends(get_db)):
    """GET /api/v1/dashboard/breakdown/platform - Performance metrics broken down by placement platform."""
    return await dashboard_service.get_breakdown(db=db, dimension="platform")

@router.get("/breakdown/device", response_model=List[BreakdownItem])
async def get_device_breakdown(db: AsyncSession = Depends(get_db)):
    """GET /api/v1/dashboard/breakdown/device - Mobile vs Desktop vs Tablet performance split."""
    return await dashboard_service.get_breakdown(db=db, dimension="device")

@router.get("/breakdown/age", response_model=List[BreakdownItem])
async def get_age_breakdown(db: AsyncSession = Depends(get_db)):
    """GET /api/v1/dashboard/breakdown/age - Demographic performance by age bracket."""
    return await dashboard_service.get_breakdown(db=db, dimension="age")

@router.get("/breakdown/gender", response_model=List[BreakdownItem])
async def get_gender_breakdown(db: AsyncSession = Depends(get_db)):
    """GET /api/v1/dashboard/breakdown/gender - Demographic performance by gender."""
    return await dashboard_service.get_breakdown(db=db, dimension="gender")

@router.get("/breakdown/geographic", response_model=List[BreakdownItem])
async def get_geographic_breakdown(db: AsyncSession = Depends(get_db)):
    """GET /api/v1/dashboard/breakdown/geographic - Country level campaign performance distribution."""
    return await dashboard_service.get_breakdown(db=db, dimension="geographic")

@router.get("/performance/hourly", response_model=List[TimePerformanceItem])
async def get_hourly_performance(db: AsyncSession = Depends(get_db)):
    """GET /api/v1/dashboard/performance/hourly - Hourly performance curve across 24 hours."""
    return await dashboard_service.get_time_performance(db=db, granularity="hourly")

@router.get("/performance/daily", response_model=List[TimePerformanceItem])
async def get_daily_performance(db: AsyncSession = Depends(get_db)):
    """GET /api/v1/dashboard/performance/daily - Daily performance breakdown for the past 7 days."""
    return await dashboard_service.get_time_performance(db=db, granularity="daily")

@router.get("/performance/weekly", response_model=List[TimePerformanceItem])
async def get_weekly_performance(db: AsyncSession = Depends(get_db)):
    """GET /api/v1/dashboard/performance/weekly - Weekly performance trend for past 4 weeks."""
    return await dashboard_service.get_time_performance(db=db, granularity="weekly")

@router.get("/performance/monthly", response_model=List[TimePerformanceItem])
async def get_monthly_performance(db: AsyncSession = Depends(get_db)):
    """GET /api/v1/dashboard/performance/monthly - Monthly performance trend for past 6 months."""
    return await dashboard_service.get_time_performance(db=db, granularity="monthly")
