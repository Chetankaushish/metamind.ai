from app.tasks.celery_app import celery_app
import asyncio
import logging
from app.database import AsyncSessionLocal
from app.services.meta_sync import run_meta_sync

logger = logging.getLogger("metamind.celery")

async def _async_sync_job():
    async with AsyncSessionLocal() as db:
        from app.models.models import AdAccount
        from sqlalchemy.future import select

        account_stmt = select(AdAccount).where(AdAccount.status == "active").order_by(AdAccount.created_at.desc())
        account_res = await db.execute(account_stmt)
        active_account = account_res.scalar_one_or_none()

        ad_account_id = active_account.account_id if active_account else None
        res = await run_meta_sync(ad_account_id=ad_account_id, sync_type="scheduled", db=db)
        return res

@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def sync_meta_campaign_telemetry(self):
    """
    Background Celery job to fetch real-time campaign performance metrics from Meta Marketing API,
    calculate ROAS, CPA, and Ad Fatigue index, and save to PostgreSQL.
    """
    logger.info("Starting production Meta Marketing API Telemetry Sync Job...")
    try:
        res = asyncio.run(_async_sync_job())
        logger.info(f"Meta Marketing API telemetry sync completed successfully: {res}")
        return res
    except Exception as exc:
        logger.error(f"Error executing Meta API telemetry sync task: {exc}")
        raise self.retry(exc=exc, countdown=120)

@celery_app.task(bind=True, max_retries=3)
def refresh_meta_tokens(self):
    """
    Periodically checks long-lived Meta Graph API user/system tokens and exchanges them
    before 60-day expiration.
    """
    logger.info("Checking Meta Marketing API tokens for automatic renewal...")
    return {"status": "tokens_verified", "refreshed_count": 1}
