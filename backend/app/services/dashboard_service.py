import datetime
import json
from typing import List, Dict, Any, Optional

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_

from app.core.config import settings
from app.models.models import (
    Campaign as CampaignModel,
    MetaAdSet as AdSetModel,
    MetaAd as AdModel,
    Insight as InsightModel,
    SyncJob as SyncJobModel,
    MetaAccount as MetaAccountModel,
)

from app.schemas.schemas import (
    DashboardOverviewResponse,
    DashboardKPIsResponse,
    DashboardChartsResponse,
    ChartDataPoint,
    TopCampaignItem,
    TopAdItem,
    TrendItem,
    BreakdownItem,
    CampaignComparisonItem,
    TimePerformanceItem,
    ComparisonSummaryResponse,
)


CACHE_STORE: Dict[str, Any] = {}


class DashboardService:
    @staticmethod
    async def get_cache(key: str) -> Optional[Any]:
        global CACHE_STORE

        try:
            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            val = await r.get(f"dashboard:{key}")
            await r.aclose()

            if val:
                return json.loads(val)

        except (
            redis.RedisError,
            ConnectionError,
            json.JSONDecodeError,
            OSError,
        ):
            pass

        return CACHE_STORE.get(key)

    @staticmethod
    async def set_cache(
        key: str,
        data: Any,
        ttl_seconds: int = 300,
    ):
        global CACHE_STORE

        CACHE_STORE[key] = data

        try:
            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            await r.setex(
                f"dashboard:{key}",
                ttl_seconds,
                json.dumps(data, default=str),
            )
            await r.aclose()

        except (
            redis.RedisError,
            ConnectionError,
            json.JSONDecodeError,
            OSError,
        ):
            pass

    @staticmethod
    def invalidate_cache():
        global CACHE_STORE

        CACHE_STORE.clear()

        try:
            import redis as sync_redis

            r = sync_redis.from_url(settings.REDIS_URL)
            keys = r.keys("dashboard:*")

            if keys:
                r.delete(*keys)

            r.close()

        except (
            sync_redis.RedisError,
            ConnectionError,
            KeyError,
            TypeError,
            ValueError,
            OSError,
        ):
            pass

    @staticmethod
    def _campaign_level_filter():
        """
        Insight rows written by the Meta sync are hierarchical:
        campaign-level rows have campaign_id populated and ad_set_id/ad_id null.
        This prevents campaign + ad set + ad rows from being double-counted.
        """
        return and_(
            InsightModel.ad_set_id.is_(None),
            InsightModel.ad_id.is_(None),
        )

    @staticmethod
    def _metric_values(row) -> Dict[str, float]:
        spend = float(row.spend or 0)
        revenue = float(row.revenue or 0)
        purchases = int(row.purchases or 0)
        clicks = int(row.clicks or 0)
        impressions = int(row.impressions or 0)
        reach = int(row.reach or 0)

        return {
            "spend": spend,
            "revenue": revenue,
            "purchases": purchases,
            "clicks": clicks,
            "impressions": impressions,
            "reach": reach,
        }

    @classmethod
    def _build_kpis(
        cls,
        *,
        spend: float,
        revenue: float,
        purchases: int,
        clicks: int,
        impressions: int,
        reach: int,
        budget: float,
        campaign_count: int,
        adset_count: int,
        ads_count: int,
    ) -> DashboardKPIsResponse:
        roas = round(revenue / spend, 2) if spend > 0 else 0.0
        cpa = round(spend / purchases, 2) if purchases > 0 else 0.0
        cpc = round(spend / clicks, 2) if clicks > 0 else 0.0
        cpm = round((spend / impressions) * 1000, 2) if impressions > 0 else 0.0
        ctr = round((clicks / impressions) * 100, 2) if impressions > 0 else 0.0
        frequency = round(impressions / reach, 2) if reach > 0 else 0.0

        has_data = (
            spend > 0
            or revenue > 0
            or purchases > 0
            or clicks > 0
            or impressions > 0
        )

        return DashboardKPIsResponse(
            spend=spend,
            revenue=revenue,
            roas=roas,
            ctr=ctr,
            cpm=cpm,
            cpc=cpc,
            cpa=cpa,
            reach=reach,
            impressions=impressions,
            frequency=frequency,
            purchases=purchases,
            conversions=purchases,
            budget=budget,
            campaign_count=campaign_count,
            ad_set_count=adset_count,
            ads_count=ads_count,
            has_data=has_data,
        )

    @classmethod
    async def _aggregate_insights(
        cls,
        db: AsyncSession,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
        status: Optional[str] = None,
        objective: Optional[str] = None,
    ) -> Dict[str, Any]:
        conditions = [cls._campaign_level_filter()]

        if start_date:
            conditions.append(InsightModel.date_start >= start_date.isoformat())

        if end_date:
            conditions.append(InsightModel.date_start <= end_date.isoformat())

        stmt = select(
            func.coalesce(func.sum(InsightModel.spend), 0.0).label("spend"),
            func.coalesce(func.sum(InsightModel.revenue), 0.0).label("revenue"),
            func.coalesce(func.sum(InsightModel.purchases), 0).label("purchases"),
            func.coalesce(func.sum(InsightModel.clicks), 0).label("clicks"),
            func.coalesce(func.sum(InsightModel.impressions), 0).label("impressions"),
            func.coalesce(func.sum(InsightModel.reach), 0).label("reach"),
            func.count(func.distinct(InsightModel.campaign_id)).label("campaign_count"),
        ).select_from(InsightModel)

        if status or objective:
            stmt = stmt.join(
                CampaignModel,
                CampaignModel.campaign_id == InsightModel.campaign_id,
            )

            if status:
                conditions.append(CampaignModel.status == status.upper())

            if objective:
                conditions.append(CampaignModel.objective == objective.upper())

        stmt = stmt.where(and_(*conditions))

        result = await db.execute(stmt)
        row = result.one()

        campaign_count = int(row.campaign_count or 0)

        # Budget is configuration, not a historical Insight metric.
        budget_stmt = select(
            func.coalesce(func.sum(CampaignModel.daily_budget), 0.0)
        )

        if status:
            budget_stmt = budget_stmt.where(
                CampaignModel.status == status.upper()
            )

        if objective:
            budget_stmt = budget_stmt.where(
                CampaignModel.objective == objective.upper()
            )

        budget_result = await db.execute(budget_stmt)
        budget = float(budget_result.scalar() or 0.0)

        # Counts are metadata counts, not performance totals.
        count_stmt = select(
            func.count(AdSetModel.id),
        )

        adset_result = await db.execute(count_stmt)
        adset_count = int(adset_result.scalar() or 0)

        ads_result = await db.execute(select(func.count(AdModel.id)))
        ads_count = int(ads_result.scalar() or 0)

        return {
            "spend": float(row.spend or 0),
            "revenue": float(row.revenue or 0),
            "purchases": int(row.purchases or 0),
            "clicks": int(row.clicks or 0),
            "impressions": int(row.impressions or 0),
            "reach": int(row.reach or 0),
            "campaign_count": campaign_count,
            "adset_count": adset_count,
            "ads_count": ads_count,
            "budget": budget,
        }

    @classmethod
    async def get_kpis(
        cls,
        db: AsyncSession,
        status: Optional[str] = None,
        objective: Optional[str] = None,
    ) -> DashboardKPIsResponse:
        cache_key = f"kpis:{status}:{objective}"
        cached = await cls.get_cache(cache_key)

        if cached:
            return DashboardKPIsResponse(**cached)

        agg = await cls._aggregate_insights(
            db=db,
            status=status,
            objective=objective,
        )

        res = cls._build_kpis(
            spend=agg["spend"],
            revenue=agg["revenue"],
            purchases=agg["purchases"],
            clicks=agg["clicks"],
            impressions=agg["impressions"],
            reach=agg["reach"],
            budget=agg["budget"],
            campaign_count=agg["campaign_count"],
            adset_count=agg["adset_count"],
            ads_count=agg["ads_count"],
        )

        await cls.set_cache(cache_key, res.model_dump())
        return res

    @classmethod
    async def get_overview(
        cls,
        db: AsyncSession,
    ) -> DashboardOverviewResponse:
        kpis = await cls.get_kpis(db=db)

        sync_stmt = (
            select(SyncJobModel)
            .where(SyncJobModel.status == "completed")
            .order_by(SyncJobModel.completed_at.desc())
            .limit(1)
        )
        sync_res = await db.execute(sync_stmt)
        last_job = sync_res.scalar_one_or_none()

        last_sync_str = (
            last_job.completed_at.isoformat()
            if last_job and last_job.completed_at
            else None
        )

        acc_stmt = select(MetaAccountModel).limit(1)
        acc_res = await db.execute(acc_stmt)
        meta_acc = acc_res.scalar_one_or_none()

        connection_status = (
            meta_acc.connection_status
            if meta_acc
            else "not_connected"
        )

        return DashboardOverviewResponse(
            kpis=kpis,
            last_sync_time=last_sync_str,
            connection_status=connection_status,
            is_synced=kpis.has_data,
        )

    @classmethod
    async def get_charts(
        cls,
        db: AsyncSession,
    ) -> DashboardChartsResponse:
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=6)

        stmt = (
            select(
                InsightModel.date_start,
                func.coalesce(func.sum(InsightModel.spend), 0.0).label("spend"),
                func.coalesce(func.sum(InsightModel.revenue), 0.0).label("revenue"),
                func.coalesce(func.sum(InsightModel.purchases), 0).label("purchases"),
                func.coalesce(func.sum(InsightModel.clicks), 0).label("clicks"),
                func.coalesce(func.sum(InsightModel.impressions), 0).label("impressions"),
            )
            .where(
                cls._campaign_level_filter(),
                InsightModel.date_start >= start_date.isoformat(),
                InsightModel.date_start <= end_date.isoformat(),
            )
            .group_by(InsightModel.date_start)
            .order_by(InsightModel.date_start)
        )

        result = await db.execute(stmt)
        rows = result.all()

        if not rows:
            return DashboardChartsResponse(
                spend_trend=[],
                revenue_trend=[],
                roas_trend=[],
                conversion_trend=[],
            )

        points = []

        for row in rows:
            spend = float(row.spend or 0)
            revenue = float(row.revenue or 0)
            purchases = int(row.purchases or 0)
            clicks = int(row.clicks or 0)
            impressions = int(row.impressions or 0)

            roas = round(revenue / spend, 2) if spend > 0 else 0.0
            ctr = (
                round((clicks / impressions) * 100, 2)
                if impressions > 0
                else 0.0
            )
            cpa = (
                round(spend / purchases, 2)
                if purchases > 0
                else 0.0
            )

            try:
                display_date = datetime.date.fromisoformat(
                    str(row.date_start)[:10]
                ).strftime("%b %d")
            except ValueError:
                display_date = str(row.date_start)

            points.append(
                ChartDataPoint(
                    date=display_date,
                    spend=spend,
                    revenue=revenue,
                    roas=roas,
                    ctr=ctr,
                    cpa=cpa,
                    conversions=purchases,
                )
            )

        return DashboardChartsResponse(
            spend_trend=points,
            revenue_trend=points,
            roas_trend=points,
            conversion_trend=points,
        )

    @classmethod
    async def get_top_campaigns(
        cls,
        db: AsyncSession,
    ) -> List[TopCampaignItem]:
        stmt = (
            select(CampaignModel)
            .order_by(CampaignModel.spend.desc())
            .limit(5)
        )

        result = await db.execute(stmt)
        campaigns = result.scalars().all()

        return [
            TopCampaignItem(
                id=c.campaign_id,
                name=c.name,
                status=c.status,
                spend=float(c.spend or 0),
                revenue=float(c.revenue or 0),
                roas=float(c.roas or 0),
                ctr=float(c.ctr or 0),
                cpa=float(c.cpa or 0),
                purchases=int(c.purchases or 0),
            )
            for c in campaigns
        ]

    @classmethod
    async def get_worst_campaigns(
        cls,
        db: AsyncSession,
    ) -> List[TopCampaignItem]:
        stmt = (
            select(CampaignModel)
            .where(CampaignModel.spend > 0)
            .order_by(CampaignModel.cpa.desc())
            .limit(5)
        )

        result = await db.execute(stmt)
        campaigns = result.scalars().all()

        return [
            TopCampaignItem(
                id=c.campaign_id,
                name=c.name,
                status=c.status,
                spend=float(c.spend or 0),
                revenue=float(c.revenue or 0),
                roas=float(c.roas or 0),
                ctr=float(c.ctr or 0),
                cpa=float(c.cpa or 0),
                purchases=int(c.purchases or 0),
            )
            for c in campaigns
        ]

    @classmethod
    async def get_campaign_comparison(
        cls,
        db: AsyncSession,
    ) -> List[CampaignComparisonItem]:
        stmt = (
            select(CampaignModel)
            .order_by(CampaignModel.spend.desc())
            .limit(10)
        )

        result = await db.execute(stmt)
        campaigns = result.scalars().all()

        if not campaigns:
            return []

        avg_roas = (
            sum(float(c.roas or 0) for c in campaigns) / len(campaigns)
        )
        avg_cpa = (
            sum(float(c.cpa or 0) for c in campaigns) / len(campaigns)
        )

        items = []

        for c in campaigns:
            roas = float(c.roas or 0)
            cpa = float(c.cpa or 0)

            roas_delta = (
                round(((roas - avg_roas) / avg_roas) * 100, 1)
                if avg_roas > 0
                else 0.0
            )
            cpa_delta = (
                round(((cpa - avg_cpa) / avg_cpa) * 100, 1)
                if avg_cpa > 0
                else 0.0
            )

            items.append(
                CampaignComparisonItem(
                    id=c.campaign_id,
                    name=c.name,
                    status=c.status,
                    objective=c.objective,
                    spend=float(c.spend or 0),
                    revenue=float(c.revenue or 0),
                    roas=roas,
                    cpa=cpa,
                    ctr=float(c.ctr or 0),
                    cpm=float(c.cpm or 0),
                    cpc=float(c.cpc or 0),
                    purchases=int(c.purchases or 0),
                    impressions=int(c.impressions or 0),
                    clicks=int(c.clicks or 0),
                    roas_delta_pct=roas_delta,
                    cpa_delta_pct=cpa_delta,
                )
            )

        return items

    @classmethod
    async def get_top_ads(
        cls,
        db: AsyncSession,
    ) -> List[TopAdItem]:
        stmt = (
            select(AdModel)
            .order_by(AdModel.spend.desc())
            .limit(5)
        )

        result = await db.execute(stmt)
        ads = result.scalars().all()

        return [
            TopAdItem(
                id=a.ad_id,
                name=a.name,
                format=a.format,
                status=a.status,
                spend=float(a.spend or 0),
                ctr=float(a.ctr or 0),
                cpc=float(a.cpc or 0),
                fatigue_level=a.fatigue_level,
            )
            for a in ads
        ]

    @classmethod
    async def _period_kpis(
        cls,
        db: AsyncSession,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> DashboardKPIsResponse:
        agg = await cls._aggregate_insights(
            db=db,
            start_date=start_date,
            end_date=end_date,
        )

        return cls._build_kpis(
            spend=agg["spend"],
            revenue=agg["revenue"],
            purchases=agg["purchases"],
            clicks=agg["clicks"],
            impressions=agg["impressions"],
            reach=agg["reach"],
            budget=agg["budget"],
            campaign_count=agg["campaign_count"],
            adset_count=agg["adset_count"],
            ads_count=agg["ads_count"],
        )

    @staticmethod
    def _trend(
        metric: str,
        current: float,
        previous: float,
    ) -> TrendItem:
        if previous == 0:
            percent_change = 0.0 if current == 0 else None
        else:
            percent_change = round(
                ((current - previous) / abs(previous)) * 100,
                1,
            )

        if current > previous:
            direction = "up"
        elif current < previous:
            direction = "down"
        else:
            direction = "flat"

        return TrendItem(
            metric=metric,
            current_value=current,
            previous_value=previous,
            percent_change=percent_change,
            direction=direction,
        )

    @classmethod
    async def get_trends(
        cls,
        db: AsyncSession,
    ) -> List[TrendItem]:
        end_date = datetime.date.today()
        current_start = end_date - datetime.timedelta(days=6)
        previous_end = current_start - datetime.timedelta(days=1)
        previous_start = previous_end - datetime.timedelta(days=6)

        current = await cls._period_kpis(
            db,
            current_start,
            end_date,
        )
        previous = await cls._period_kpis(
            db,
            previous_start,
            previous_end,
        )

        return [
            cls._trend("ROAS", current.roas, previous.roas),
            cls._trend("Revenue", current.revenue, previous.revenue),
            cls._trend("CPA", current.cpa, previous.cpa),
            cls._trend("CTR", current.ctr, previous.ctr),
        ]

    @classmethod
    async def get_period_comparison(
        cls,
        db: AsyncSession,
    ) -> ComparisonSummaryResponse:
        end_date = datetime.date.today()
        current_start = end_date - datetime.timedelta(days=6)
        previous_end = current_start - datetime.timedelta(days=1)
        previous_start = previous_end - datetime.timedelta(days=6)

        current = await cls._period_kpis(
            db,
            current_start,
            end_date,
        )
        previous = await cls._period_kpis(
            db,
            previous_start,
            previous_end,
        )

        def pct(current_value: float, previous_value: float) -> float:
            if previous_value == 0:
                return 0.0
            return round(
                ((current_value - previous_value) / abs(previous_value)) * 100,
                1,
            )

        top_camps = await cls.get_top_campaigns(db=db)
        worst_camps = await cls.get_worst_campaigns(db=db)

        return ComparisonSummaryResponse(
            current_period=current,
            previous_period=previous,
            spend_growth_pct=pct(current.spend, previous.spend),
            revenue_growth_pct=pct(current.revenue, previous.revenue),
            roas_growth_pct=pct(current.roas, previous.roas),
            cpa_growth_pct=pct(current.cpa, previous.cpa),
            purchases_growth_pct=pct(
                current.purchases,
                previous.purchases,
            ),
            best_performer=top_camps[0] if top_camps else None,
            worst_performer=worst_camps[0] if worst_camps else None,
        )

    @classmethod
    async def get_breakdown(
        cls,
        db: AsyncSession,
        dimension: str,
    ) -> List[BreakdownItem]:
        """
        Only return breakdowns that are actually represented in the database.

        The current Insight schema does not persist Meta breakdown dimensions
        such as platform, device, age, gender, or geography. Returning
        hardcoded percentages here would fabricate data, so unsupported
        dimensions return an empty result until the sync layer stores those
        breakdowns explicitly.
        """
        # No breakdown dimension is persisted by the current Insight model.
        # Never manufacture percentages or demographic/platform data.
        return []

    @classmethod
    async def get_time_performance(
        cls,
        db: AsyncSession,
        granularity: str,
    ) -> List[TimePerformanceItem]:
        """
        Build time performance from stored campaign-level Meta Insights.

        Unsupported granularities return an empty result rather than
        fabricating hourly/weekly/monthly data.
        """
        granularity = granularity.lower().strip()

        if granularity != "daily":
            return []

        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=6)

        stmt = (
            select(
                InsightModel.date_start,
                func.coalesce(func.sum(InsightModel.spend), 0.0).label("spend"),
                func.coalesce(func.sum(InsightModel.revenue), 0.0).label("revenue"),
                func.coalesce(func.sum(InsightModel.purchases), 0).label("purchases"),
                func.coalesce(func.sum(InsightModel.clicks), 0).label("clicks"),
                func.coalesce(func.sum(InsightModel.impressions), 0).label("impressions"),
            )
            .where(
                cls._campaign_level_filter(),
                InsightModel.date_start >= start_date.isoformat(),
                InsightModel.date_start <= end_date.isoformat(),
            )
            .group_by(InsightModel.date_start)
            .order_by(InsightModel.date_start)
        )

        result = await db.execute(stmt)
        rows = result.all()

        items = []

        for row in rows:
            spend = float(row.spend or 0)
            revenue = float(row.revenue or 0)
            purchases = int(row.purchases or 0)
            clicks = int(row.clicks or 0)
            impressions = int(row.impressions or 0)

            roas = round(revenue / spend, 2) if spend > 0 else 0.0
            ctr = (
                round((clicks / impressions) * 100, 2)
                if impressions > 0
                else 0.0
            )
            cpa = (
                round(spend / purchases, 2)
                if purchases > 0
                else 0.0
            )

            items.append(
                TimePerformanceItem(
                    period=str(row.date_start)[:10],
                    spend=spend,
                    revenue=revenue,
                    roas=roas,
                    purchases=purchases,
                    clicks=clicks,
                    impressions=impressions,
                    ctr=ctr,
                    cpa=cpa,
                )
            )

        return items


dashboard_service = DashboardService()
