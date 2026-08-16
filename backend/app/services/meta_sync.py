
import asyncio
import datetime
from datetime import timedelta
import httpx
import uuid
from typing import Dict, Any, Optional

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decrypt_token
from app.core.logging import logger
from app.api.v1.ws import ws_manager
from app.models.models import (
    OAuthToken,
    AdAccount,
    Campaign,
    MetaAdSet,
    MetaAd,
    Insight,
    SyncJob,
    SyncLog,
)
from app.api.v1.dashboard import invalidate_dashboard_cache


META_GRAPH_URL = f"https://graph.facebook.com/{settings.META_GRAPH_API_VERSION}"


def _money(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _integer(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _extract_action_count(
    actions: Optional[list],
    preferred_types: tuple[str, ...] = (
        "purchase",
        "omni_purchase",
        "offsite_conversion.fb_pixel_purchase",
        "onsite_web_purchase",
        "web_in_store_purchase",
    ),
) -> int:
    if not isinstance(actions, list):
        return 0

    normalized = {
        str(item.get("action_type", "")).lower(): _integer(item.get("value"))
        for item in actions
        if isinstance(item, dict)
    }

    for action_type in preferred_types:
        value = normalized.get(action_type.lower())
        if value is not None:
            return value

    # Fallback only when Meta uses a purchase-like action name.
    for action_type, value in normalized.items():
        if "purchase" in action_type:
            return value

    return 0


def _extract_action_value(
    action_values: Optional[list],
    preferred_types: tuple[str, ...] = (
        "purchase",
        "omni_purchase",
        "offsite_conversion.fb_pixel_purchase",
        "onsite_web_purchase",
        "web_in_store_purchase",
    ),
) -> float:
    if not isinstance(action_values, list):
        return 0.0

    normalized = {
        str(item.get("action_type", "")).lower(): _money(item.get("value"))
        for item in action_values
        if isinstance(item, dict)
    }

    for action_type in preferred_types:
        value = normalized.get(action_type.lower())
        if value is not None:
            return value

    for action_type, value in normalized.items():
        if "purchase" in action_type:
            return value

    return 0.0


def _calculate_metrics(row: dict) -> Dict[str, Any]:
    spend = _money(row.get("spend"))
    revenue = _extract_action_value(row.get("action_values"))
    purchases = _extract_action_count(row.get("actions"))

    impressions = _integer(row.get("impressions"))
    reach = _integer(row.get("reach"))
    clicks = _integer(row.get("clicks"))
    ctr = _money(row.get("ctr"))
    cpc = _money(row.get("cpc"))
    cpm = _money(row.get("cpm"))
    frequency = _money(row.get("frequency"))

    if not ctr and impressions:
        ctr = (clicks / impressions) * 100.0

    if not cpc and clicks:
        cpc = spend / clicks

    if not cpm and impressions:
        cpm = (spend / impressions) * 1000.0

    roas = revenue / spend if spend > 0 else 0.0
    cpa = spend / purchases if purchases > 0 else 0.0

    conversions = _extract_action_count(
        row.get("conversions")
        if isinstance(row.get("conversions"), list)
        else row.get("actions")
    )

    if not conversions:
        conversions = purchases

    return {
        "spend": spend,
        "revenue": revenue,
        "purchases": purchases,
        "impressions": impressions,
        "reach": reach,
        "clicks": clicks,
        "ctr": ctr,
        "cpc": cpc,
        "cpm": cpm,
        "cpa": cpa,
        "frequency": frequency,
        "roas": roas,
        "conversions": conversions,
        "cost_per_result": cpa,
    }


async def _fetch_with_backoff(
    client: httpx.AsyncClient,
    url: str,
    params: dict,
    max_retries: int = 3,
) -> dict:
    """GET a Meta Graph API resource with rate-limit/network retries."""

    delay = 1.0

    for attempt in range(max_retries):
        try:
            response = await client.get(
                url,
                params=params,
                timeout=30.0,
            )

            try:
                data = response.json()
            except ValueError:
                data = {"error": {"message": response.text}}

            if response.status_code == 200 and not data.get("error"):
                return data

            error = data.get("error", {})
            error_code = error.get("code")

            if response.status_code == 429 or error_code in (17, 613, 80004):
                if attempt < max_retries - 1:
                    logger.warning(
                        "meta_api_rate_limit_encountered",
                        attempt=attempt + 1,
                        delay=delay,
                        status=response.status_code,
                        error_code=error_code,
                    )
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue

            raise RuntimeError(
                "Meta Graph API request failed "
                f"(status={response.status_code}, "
                f"code={error_code}, "
                f"message={error.get('message', 'Unknown Meta API error')})"
            )

        except httpx.RequestError as exc:
            if attempt < max_retries - 1:
                logger.warning(
                    "meta_api_request_exception",
                    error=str(exc),
                    attempt=attempt + 1,
                    delay=delay,
                )
                await asyncio.sleep(delay)
                delay *= 2
                continue

            raise RuntimeError(
                f"Meta Graph API network request failed: {exc}"
            ) from exc

    raise RuntimeError("Meta Graph API request failed after retries.")


async def _fetch_all_pages(
    client: httpx.AsyncClient,
    url: str,
    params: dict,
) -> list[dict]:
    """Fetch all Meta Graph API pagination pages."""

    results: list[dict] = []
    next_url: Optional[str] = url
    next_params: Optional[dict] = params

    while next_url:
        page = await _fetch_with_backoff(
            client,
            next_url,
            next_params or {},
        )

        data = page.get("data", [])
        if isinstance(data, list):
            results.extend(item for item in data if isinstance(item, dict))

        paging = page.get("paging") or {}
        next_url = paging.get("next")
        next_params = None

    return results


async def _fetch_insights(
    client: httpx.AsyncClient,
    act_id: str,
    access_token: str,
    level: str,
) -> list[dict]:
    """Fetch daily insights for the requested Meta object level."""

    insights_url = f"{META_GRAPH_URL}/{act_id}/insights"
    params = {
        "level": level,
        "time_increment": 1,
        "date_preset": "last_30d",
        "fields": (
            "campaign_id,adset_id,ad_id,date_start,date_stop,"
            "spend,impressions,reach,clicks,ctr,cpc,cpm,frequency,"
            "actions,action_values"
        ),
        "access_token": access_token,
    }

    return await _fetch_all_pages(
        client,
        insights_url,
        params,
    )


def _creative_text(creative: dict) -> tuple[str, str]:
    if not isinstance(creative, dict):
        return "", ""

    title = str(
        creative.get("name")
        or creative.get("title")
        or ""
    )

    body = str(
        creative.get("body")
        or creative.get("message")
        or ""
    )

    object_story_spec = creative.get("object_story_spec") or {}
    if isinstance(object_story_spec, dict):
        link_data = object_story_spec.get("link_data") or {}
        video_data = object_story_spec.get("video_data") or {}

        if isinstance(link_data, dict):
            title = title or str(
                link_data.get("name")
                or link_data.get("caption")
                or ""
            )
            body = body or str(
                link_data.get("message")
                or link_data.get("description")
                or ""
            )

        if isinstance(video_data, dict):
            title = title or str(video_data.get("title") or "")
            body = body or str(video_data.get("message") or "")

    return title, body


def _creative_format(creative: dict) -> str:
    if not isinstance(creative, dict):
        return "Unknown"

    object_story_spec = creative.get("object_story_spec") or {}
    if isinstance(object_story_spec, dict):
        if object_story_spec.get("video_data"):
            return "Video"
        if object_story_spec.get("link_data"):
            return "Link"
        if object_story_spec.get("photo_data"):
            return "Image"
        if object_story_spec.get("template_data"):
            return "Carousel"

    asset_feed_spec = creative.get("asset_feed_spec")
    if isinstance(asset_feed_spec, dict):
        if asset_feed_spec.get("videos"):
            return "Video"
        if asset_feed_spec.get("images"):
            return "Image"
        if asset_feed_spec.get("bodies") and asset_feed_spec.get("link_urls"):
            return "Dynamic"

    return "Unknown"


async def run_meta_sync(
    ad_account_id: Optional[str],
    sync_type: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    job_id = f"job_{uuid.uuid4().hex[:8]}"

    sync_job = SyncJob(
        job_id=job_id,
        ad_account_id=ad_account_id,
        sync_type=sync_type,
        status="in_progress",
        current_object="initializing",
        records_downloaded=0,
        total_records=0,
        progress_pct=0.0,
        started_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(sync_job)
    await db.commit()

    await ws_manager.broadcast({
        "event": "sync_started",
        "data": {
            "job_id": job_id,
            "ad_account_id": ad_account_id,
            "sync_type": sync_type,
            "status": "in_progress",
            "progress_pct": 0.0,
        },
    })

    records_count = 0

    try:
        token_stmt = (
            select(OAuthToken)
            .where(OAuthToken.is_valid == True)
            .order_by(OAuthToken.created_at.desc())
        )
        token_result = await db.execute(token_stmt)
        token_record = token_result.scalar_one_or_none()

        if not token_record:
            raise RuntimeError(
                "No valid Meta access token found. "
                "Please connect a Meta ad account first."
            )

        access_token = decrypt_token(
            token_record.encrypted_access_token
        )

        if not access_token:
            raise RuntimeError(
                "Meta access token is empty or invalid."
            )

        act_id = str(ad_account_id or "").strip()
        if not act_id:
            raise RuntimeError(
                "Meta ad account ID is required to start synchronization."
            )

        if not act_id.startswith("act_"):
            act_id = f"act_{act_id}"

        async with httpx.AsyncClient() as client:
            # Resolve the local AdAccount row. Do not invent an account ID.
            account_stmt = select(AdAccount).where(
                AdAccount.account_id == act_id
            )
            account_result = await db.execute(account_stmt)
            db_ad_account = account_result.scalar_one_or_none()

            if not db_ad_account:
                account_response = await _fetch_with_backoff(
                    client,
                    f"{META_GRAPH_URL}/{act_id}",
                    {
                        "fields": "id,name,currency,timezone,account_status",
                        "access_token": access_token,
                    },
                )

                db_ad_account = AdAccount(
                    account_name=account_response.get("name") or act_id,
                    account_id=act_id,
                    currency=account_response.get("currency"),
                    timezone=account_response.get("timezone"),
                    status=str(
                        account_response.get("account_status", "unknown")
                    ),
                )
                db.add(db_ad_account)
                await db.flush()

            # -----------------------------------------------------------------
            # 1. Campaigns
            # -----------------------------------------------------------------
            sync_job.current_object = "campaigns"
            sync_job.progress_pct = 10.0
            await db.commit()

            campaigns = await _fetch_all_pages(
                client,
                f"{META_GRAPH_URL}/{act_id}/campaigns",
                {
                    "fields": (
                        "id,name,status,objective,buying_type,"
                        "daily_budget,lifetime_budget"
                    ),
                    "access_token": access_token,
                },
            )

            campaign_by_meta_id: dict[str, Campaign] = {}

            for item in campaigns:
                meta_campaign_id = item.get("id")
                if not meta_campaign_id:
                    continue

                result = await db.execute(
                    select(Campaign).where(
                        Campaign.campaign_id == meta_campaign_id
                    )
                )
                campaign = result.scalar_one_or_none()

                daily_budget = (
                    _money(item.get("daily_budget")) / 100.0
                    if item.get("daily_budget") is not None
                    else 0.0
                )
                lifetime_budget = (
                    _money(item.get("lifetime_budget")) / 100.0
                    if item.get("lifetime_budget") is not None
                    else 0.0
                )

                if campaign is None:
                    campaign = Campaign(
                        campaign_id=meta_campaign_id,
                        name=item.get("name") or meta_campaign_id,
                        ad_account_id=db_ad_account.id,
                        status=item.get("status"),
                        objective=item.get("objective"),
                        buying_type=item.get("buying_type"),
                        daily_budget=daily_budget,
                        lifetime_budget=lifetime_budget,
                        spend=0.0,
                        revenue=0.0,
                        roas=0.0,
                        ctr=0.0,
                        cpm=0.0,
                        cpc=0.0,
                        cpa=0.0,
                        purchases=0,
                        clicks=0,
                        impressions=0,
                        reach=0,
                        learning_phase="unknown",
                    )
                    db.add(campaign)
                    await db.flush()
                else:
                    campaign.name = item.get("name") or campaign.name
                    campaign.ad_account_id = db_ad_account.id
                    campaign.status = item.get("status") or campaign.status
                    campaign.objective = item.get("objective") or campaign.objective
                    campaign.buying_type = item.get("buying_type") or campaign.buying_type
                    campaign.daily_budget = daily_budget
                    campaign.lifetime_budget = lifetime_budget

                    # Reset previously stored performance so stale/demo values
                    # cannot remain when Meta returns no insight for this period.
                    campaign.spend = 0.0
                    campaign.revenue = 0.0
                    campaign.roas = 0.0
                    campaign.ctr = 0.0
                    campaign.cpm = 0.0
                    campaign.cpc = 0.0
                    campaign.cpa = 0.0
                    campaign.purchases = 0
                    campaign.clicks = 0
                    campaign.impressions = 0
                    campaign.reach = 0
                    campaign.learning_phase = "unknown"

                campaign_by_meta_id[meta_campaign_id] = campaign
                records_count += 1

            await db.commit()

            # -----------------------------------------------------------------
            # 2. Ad Sets
            # -----------------------------------------------------------------
            sync_job.current_object = "ad_sets"
            sync_job.records_downloaded = records_count
            sync_job.progress_pct = 30.0
            await db.commit()

            ad_sets = await _fetch_all_pages(
                client,
                f"{META_GRAPH_URL}/{act_id}/adsets",
                {
                    "fields": (
                        "id,name,status,daily_budget,campaign_id,"
                        "bid_strategy,optimization_goal"
                    ),
                    "access_token": access_token,
                },
            )

            adset_by_meta_id: dict[str, MetaAdSet] = {}

            for item in ad_sets:
                meta_adset_id = item.get("id")
                if not meta_adset_id:
                    continue

                campaign_meta_id = item.get("campaign_id")
                campaign = campaign_by_meta_id.get(campaign_meta_id)

                if campaign is None and campaign_meta_id:
                    result = await db.execute(
                        select(Campaign).where(
                            Campaign.campaign_id == campaign_meta_id
                        )
                    )
                    campaign = result.scalar_one_or_none()

                if campaign is None:
                    logger.warning(
                        "meta_adset_campaign_not_found",
                        ad_set_id=meta_adset_id,
                        campaign_id=campaign_meta_id,
                    )
                    continue

                result = await db.execute(
                    select(MetaAdSet).where(
                        MetaAdSet.ad_set_id == meta_adset_id
                    )
                )
                ad_set = result.scalar_one_or_none()

                daily_budget = (
                    _money(item.get("daily_budget")) / 100.0
                    if item.get("daily_budget") is not None
                    else 0.0
                )

                if ad_set is None:
                    ad_set = MetaAdSet(
                        ad_set_id=meta_adset_id,
                        campaign_id=campaign.id,
                        name=item.get("name") or meta_adset_id,
                        status=item.get("status"),
                        daily_budget=daily_budget,
                        bid_strategy=item.get("bid_strategy"),
                        optimization_goal=item.get("optimization_goal"),
                        cpa=0.0,
                        roas=0.0,
                        spend=0.0,
                    )
                    db.add(ad_set)
                    await db.flush()
                else:
                    ad_set.campaign_id = campaign.id
                    ad_set.name = item.get("name") or ad_set.name
                    ad_set.status = item.get("status") or ad_set.status
                    ad_set.daily_budget = daily_budget
                    ad_set.bid_strategy = item.get("bid_strategy") or ad_set.bid_strategy
                    ad_set.optimization_goal = item.get("optimization_goal") or ad_set.optimization_goal
                    ad_set.cpa = 0.0
                    ad_set.roas = 0.0
                    ad_set.spend = 0.0

                adset_by_meta_id[meta_adset_id] = ad_set
                records_count += 1

            await db.commit()

            # -----------------------------------------------------------------
            # 3. Ads + Creative
            # -----------------------------------------------------------------
            sync_job.current_object = "ads"
            sync_job.records_downloaded = records_count
            sync_job.progress_pct = 50.0
            await db.commit()

            ads = await _fetch_all_pages(
                client,
                f"{META_GRAPH_URL}/{act_id}/ads",
                {
                    "fields": (
                        "id,name,status,adset_id,"
                        "creative{id,name,thumbnail_url,image_url,"
                        "object_story_spec,asset_feed_spec}"
                    ),
                    "access_token": access_token,
                },
            )

            for item in ads:
                meta_ad_id = item.get("id")
                if not meta_ad_id:
                    continue

                meta_adset_id = item.get("adset_id")
                ad_set = adset_by_meta_id.get(meta_adset_id)

                if ad_set is None and meta_adset_id:
                    result = await db.execute(
                        select(MetaAdSet).where(
                            MetaAdSet.ad_set_id == meta_adset_id
                        )
                    )
                    ad_set = result.scalar_one_or_none()

                if ad_set is None:
                    logger.warning(
                        "meta_ad_adset_not_found",
                        ad_id=meta_ad_id,
                        ad_set_id=meta_adset_id,
                    )
                    continue

                result = await db.execute(
                    select(MetaAd).where(
                        MetaAd.ad_id == meta_ad_id
                    )
                )
                meta_ad = result.scalar_one_or_none()

                creative = item.get("creative") or {}
                title, body = _creative_text(creative)
                creative_format = _creative_format(creative)
                media_url = (
                    creative.get("thumbnail_url")
                    or creative.get("image_url")
                    or ""
                )

                if meta_ad is None:
                    meta_ad = MetaAd(
                        ad_id=meta_ad_id,
                        ad_set_id=ad_set.id,
                        name=item.get("name") or meta_ad_id,
                        status=item.get("status"),
                        format=creative_format,
                        creative_title=title or None,
                        creative_body=body or None,
                        media_url=media_url or None,
                        ctr=0.0,
                        cpc=0.0,
                        spend=0.0,
                        fatigue_level=None,
                    )
                    db.add(meta_ad)
                    await db.flush()
                else:
                    meta_ad.ad_set_id = ad_set.id
                    meta_ad.name = item.get("name") or meta_ad.name
                    meta_ad.status = item.get("status") or meta_ad.status
                    meta_ad.format = creative_format
                    meta_ad.creative_title = title or None
                    meta_ad.creative_body = body or None
                    meta_ad.media_url = media_url or None
                    meta_ad.ctr = 0.0
                    meta_ad.cpc = 0.0
                    meta_ad.spend = 0.0
                    meta_ad.fatigue_level = None

                records_count += 1

            await db.commit()

            # -----------------------------------------------------------------
            # 4. Insights - campaign level
            # -----------------------------------------------------------------
            sync_job.current_object = "insights_campaigns"
            sync_job.records_downloaded = records_count
            sync_job.progress_pct = 65.0
            await db.commit()

            campaign_insights = await _fetch_insights(
                client,
                act_id,
                access_token,
                "campaign",
            )

            for row in campaign_insights:
                meta_campaign_id = row.get("campaign_id")
                campaign = campaign_by_meta_id.get(meta_campaign_id)

                if campaign is None and meta_campaign_id:
                    result = await db.execute(
                        select(Campaign).where(
                            Campaign.campaign_id == meta_campaign_id
                        )
                    )
                    campaign = result.scalar_one_or_none()

                if campaign is None:
                    continue

                metrics = _calculate_metrics(row)
                date_start = row.get("date_start")
                date_stop = row.get("date_stop")

                insight_result = await db.execute(
                    select(Insight).where(
                        Insight.ad_account_id == db_ad_account.id,
                        Insight.campaign_id == campaign.id,
                        Insight.ad_set_id.is_(None),
                        Insight.ad_id.is_(None),
                        Insight.date_start == date_start,
                        Insight.date_stop == date_stop,
                    )
                )
                insight = insight_result.scalar_one_or_none()

                if insight is None:
                    insight = Insight(
                        ad_account_id=db_ad_account.id,
                        campaign_id=campaign.id,
                        date_start=date_start,
                        date_stop=date_stop,
                    )
                    db.add(insight)

                insight.spend = metrics["spend"]
                insight.revenue = metrics["revenue"]
                insight.purchases = metrics["purchases"]
                insight.impressions = metrics["impressions"]
                insight.reach = metrics["reach"]
                insight.clicks = metrics["clicks"]
                insight.ctr = metrics["ctr"]
                insight.cpc = metrics["cpc"]
                insight.cpm = metrics["cpm"]
                insight.cpa = metrics["cpa"]
                insight.frequency = metrics["frequency"]
                insight.roas = metrics["roas"]
                insight.conversions = metrics["conversions"]
                insight.cost_per_result = metrics["cost_per_result"]
                insight.status = row.get("status") or insight.status

            await db.commit()

            # Aggregate campaign-level metrics for dashboard cards/tables.
            for campaign in campaign_by_meta_id.values():
                insight_window_start = (
                    datetime.date.today() - timedelta(days=29)
                )

                result = await db.execute(
                    select(Insight).where(
                        Insight.campaign_id == campaign.id,
                        Insight.ad_account_id == db_ad_account.id,
                        Insight.date_start >= insight_window_start,
                    )
                )
                rows = result.scalars().all()

                campaign.spend = sum(_money(r.spend) for r in rows)
                campaign.revenue = sum(_money(r.revenue) for r in rows)
                campaign.purchases = sum(_integer(r.purchases) for r in rows)
                campaign.impressions = sum(_integer(r.impressions) for r in rows)
                campaign.reach = sum(_integer(r.reach) for r in rows)
                campaign.clicks = sum(_integer(r.clicks) for r in rows)

                campaign.ctr = (
                    (campaign.clicks / campaign.impressions) * 100.0
                    if campaign.impressions > 0
                    else 0.0
                )
                campaign.cpc = (
                    campaign.spend / campaign.clicks
                    if campaign.clicks > 0
                    else 0.0
                )
                campaign.cpm = (
                    (campaign.spend / campaign.impressions) * 1000.0
                    if campaign.impressions > 0
                    else 0.0
                )
                campaign.cpa = (
                    campaign.spend / campaign.purchases
                    if campaign.purchases > 0
                    else 0.0
                )
                campaign.roas = (
                    campaign.revenue / campaign.spend
                    if campaign.spend > 0
                    else 0.0
                )

            await db.commit()

            # -----------------------------------------------------------------
            # 5. Insights - ad set level
            # -----------------------------------------------------------------
            sync_job.current_object = "insights_ad_sets"
            sync_job.progress_pct = 78.0
            await db.commit()

            # Reset aggregate fields before rebuilding them from the current
            # Meta 30-day insight window. This prevents double-counting on
            # repeated syncs.
            for ad_set in adset_by_meta_id.values():
                ad_set.spend = 0.0
                ad_set.cpa = 0.0
                ad_set.roas = 0.0

            adset_insights = await _fetch_insights(
                client,
                act_id,
                access_token,
                "adset",
            )

            adset_metric_totals: dict[str, dict[str, float]] = {}

            for row in adset_insights:
                meta_adset_id = row.get("adset_id")
                ad_set = adset_by_meta_id.get(meta_adset_id)

                if ad_set is None and meta_adset_id:
                    result = await db.execute(
                        select(MetaAdSet).where(
                            MetaAdSet.ad_set_id == meta_adset_id
                        )
                    )
                    ad_set = result.scalar_one_or_none()

                if ad_set is None:
                    continue

                metrics = _calculate_metrics(row)

                totals = adset_metric_totals.setdefault(
                    meta_adset_id,
                    {"spend": 0.0, "revenue": 0.0, "purchases": 0.0},
                )
                totals["spend"] += metrics["spend"]
                totals["revenue"] += metrics["revenue"]
                totals["purchases"] += metrics["purchases"]

                ad_set.spend = totals["spend"]
                ad_set.cpa = (
                    totals["spend"] / totals["purchases"]
                    if totals["purchases"] > 0
                    else 0.0
                )
                ad_set.roas = (
                    totals["revenue"] / totals["spend"]
                    if totals["spend"] > 0
                    else 0.0
                )

                date_start = row.get("date_start")
                date_stop = row.get("date_stop")

                result = await db.execute(
                    select(Insight).where(
                        Insight.ad_account_id == db_ad_account.id,
                        Insight.ad_set_id == ad_set.id,
                        Insight.campaign_id.is_(None),
                        Insight.ad_id.is_(None),
                        Insight.date_start == date_start,
                        Insight.date_stop == date_stop,
                    )
                )
                insight = result.scalar_one_or_none()

                if insight is None:
                    insight = Insight(
                        ad_account_id=db_ad_account.id,
                        ad_set_id=ad_set.id,
                        date_start=date_start,
                        date_stop=date_stop,
                    )
                    db.add(insight)

                insight.spend = metrics["spend"]
                insight.revenue = metrics["revenue"]
                insight.purchases = metrics["purchases"]
                insight.impressions = metrics["impressions"]
                insight.reach = metrics["reach"]
                insight.clicks = metrics["clicks"]
                insight.ctr = metrics["ctr"]
                insight.cpc = metrics["cpc"]
                insight.cpm = metrics["cpm"]
                insight.cpa = metrics["cpa"]
                insight.frequency = metrics["frequency"]
                insight.roas = metrics["roas"]
                insight.conversions = metrics["conversions"]
                insight.cost_per_result = metrics["cost_per_result"]
                insight.status = row.get("status") or insight.status

            await db.commit()

            # -----------------------------------------------------------------
            # 6. Insights - ad level
            # -----------------------------------------------------------------
            sync_job.current_object = "insights_ads"
            sync_job.progress_pct = 88.0
            await db.commit()

            ad_insights = await _fetch_insights(
                client,
                act_id,
                access_token,
                "ad",
            )

            ad_by_meta_id: dict[str, MetaAd] = {}
            result = await db.execute(select(MetaAd))
            for ad in result.scalars().all():
                ad_by_meta_id[ad.ad_id] = ad

            for ad in ad_by_meta_id.values():
                ad.spend = 0.0
                ad.ctr = 0.0
                ad.cpc = 0.0

            ad_metric_totals: dict[str, dict[str, float]] = {}

            for row in ad_insights:
                meta_ad_id = row.get("ad_id")
                meta_ad = ad_by_meta_id.get(meta_ad_id)

                if meta_ad is None:
                    continue

                metrics = _calculate_metrics(row)

                # Ad model contains only aggregate performance fields.
                # Rebuild the current Meta 30-day window instead of accumulating
                # repeatedly across sync runs.
                totals = ad_metric_totals.setdefault(
                    meta_ad_id,
                    {"spend": 0.0, "clicks": 0.0, "impressions": 0.0},
                )
                totals["spend"] += metrics["spend"]
                totals["clicks"] += metrics["clicks"]
                totals["impressions"] += metrics["impressions"]

                meta_ad.spend = totals["spend"]
                meta_ad.ctr = (
                    (totals["clicks"] / totals["impressions"]) * 100.0
                    if totals["impressions"] > 0
                    else 0.0
                )
                meta_ad.cpc = (
                    totals["spend"] / totals["clicks"]
                    if totals["clicks"] > 0
                    else 0.0
                )

                date_start = row.get("date_start")
                date_stop = row.get("date_stop")

                result = await db.execute(
                    select(Insight).where(
                        Insight.ad_account_id == db_ad_account.id,
                        Insight.ad_id == meta_ad.id,
                        Insight.campaign_id.is_(None),
                        Insight.ad_set_id.is_(None),
                        Insight.date_start == date_start,
                        Insight.date_stop == date_stop,
                    )
                )
                insight = result.scalar_one_or_none()

                if insight is None:
                    insight = Insight(
                        ad_account_id=db_ad_account.id,
                        ad_id=meta_ad.id,
                        date_start=date_start,
                        date_stop=date_stop,
                    )
                    db.add(insight)

                insight.spend = metrics["spend"]
                insight.revenue = metrics["revenue"]
                insight.purchases = metrics["purchases"]
                insight.impressions = metrics["impressions"]
                insight.reach = metrics["reach"]
                insight.clicks = metrics["clicks"]
                insight.ctr = metrics["ctr"]
                insight.cpc = metrics["cpc"]
                insight.cpm = metrics["cpm"]
                insight.cpa = metrics["cpa"]
                insight.frequency = metrics["frequency"]
                insight.roas = metrics["roas"]
                insight.conversions = metrics["conversions"]
                insight.cost_per_result = metrics["cost_per_result"]
                insight.status = row.get("status") or insight.status

            await db.commit()

            # -----------------------------------------------------------------
            # 7. Finalize
            # -----------------------------------------------------------------
            sync_job.status = "completed"
            sync_job.current_object = "complete"
            sync_job.records_downloaded = records_count
            sync_job.progress_pct = 100.0
            sync_job.completed_at = datetime.datetime.now(datetime.timezone.utc)
            await db.commit()

            log = SyncLog(
                sync_job_id=sync_job.id,
                log_level="INFO",
                message=(
                    f"Successfully synchronized {records_count} Meta objects "
                    f"and real insights for {act_id}"
                ),
                records_count=records_count,
            )
            db.add(log)
            await db.commit()

            invalidate_dashboard_cache()

            await ws_manager.broadcast({
                "event": "sync_complete",
                "data": {
                    "job_id": job_id,
                    "ad_account_id": act_id,
                    "status": "completed",
                    "records_downloaded": records_count,
                    "progress_pct": 100.0,
                    "message": "Meta Marketing API synchronization complete using live API data",
                },
            })

            return {
                "job_id": job_id,
                "status": "completed",
                "records_downloaded": records_count,
                "progress_pct": 100.0,
            }

    except Exception as exc:
        logger.error(
            "meta_sync_failed",
            error=str(exc),
            job_id=job_id,
        )

        sync_job.status = "failed"
        sync_job.error_message = str(exc)
        sync_job.completed_at = datetime.datetime.now(datetime.timezone.utc)
        await db.commit()

        await ws_manager.broadcast({
            "event": "sync_failed",
            "data": {
                "job_id": job_id,
                "status": "failed",
                "error": str(exc),
            },
        })

        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(exc),
        }
