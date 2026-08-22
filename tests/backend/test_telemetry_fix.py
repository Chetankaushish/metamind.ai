import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.tasks.tasks import _async_sync_job, sync_meta_campaign_telemetry
from app.models.models import AdAccount, OAuthToken

@pytest.mark.asyncio
async def test_async_sync_job_resolves_active_ad_account():
    mock_db = AsyncMock()
    mock_account = AdAccount(account_id="act_123456789", status="active")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_account
    mock_db.execute.return_value = mock_result

    with patch("app.tasks.tasks.AsyncSessionLocal") as mock_session_local, \
         patch("app.tasks.tasks.run_meta_sync", new_callable=AsyncMock) as mock_run_sync:

        mock_session_local.return_value.__aenter__.return_value = mock_db
        mock_run_sync.return_value = {"status": "completed", "job_id": "job_123"}

        res = await _async_sync_job()

        assert res["status"] == "completed"
        mock_run_sync.assert_called_once_with(
            ad_account_id="act_123456789",
            sync_type="scheduled",
            db=mock_db
        )

@pytest.mark.asyncio
async def test_async_sync_job_handles_no_active_ad_account():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    with patch("app.tasks.tasks.AsyncSessionLocal") as mock_session_local, \
         patch("app.tasks.tasks.run_meta_sync", new_callable=AsyncMock) as mock_run_sync:

        mock_session_local.return_value.__aenter__.return_value = mock_db
        mock_run_sync.return_value = {"status": "failed", "error": "Meta ad account ID is required"}

        res = await _async_sync_job()

        mock_run_sync.assert_called_once_with(
            ad_account_id=None,
            sync_type="scheduled",
            db=mock_db
        )
