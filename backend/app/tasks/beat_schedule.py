BEAT_SCHEDULE = {
    "sync-meta-campaigns-every-15-mins": {
        "task": "app.tasks.sync_meta_campaign_telemetry",
        "schedule": 900.0,
    },
    "auto-refresh-meta-tokens-daily": {
        "task": "app.tasks.refresh_meta_tokens",
        "schedule": 86400.0,
    }
}
