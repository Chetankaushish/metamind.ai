from celery import Celery
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "metamind_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    result_expires=86400,
    task_routes={
        "app.tasks.sync_meta_campaign_telemetry": {"queue": "meta_sync"},
        "app.tasks.refresh_meta_tokens": {"queue": "auth_tokens"},
        "*": {"queue": "default"}
    },
    beat_schedule={
        "sync-meta-campaigns-every-15-mins": {
            "task": "app.tasks.sync_meta_campaign_telemetry",
            "schedule": 900.0,
        },
        "auto-refresh-meta-tokens-daily": {
            "task": "app.tasks.refresh_meta_tokens",
            "schedule": 86400.0,
        }
    }
)
