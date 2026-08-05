import uuid
from datetime import datetime, timezone

def generate_uuid() -> str:
    return str(uuid.uuid4())

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

def calculate_roas(spend: float, revenue: float) -> float:
    if spend <= 0:
        return 0.0
    return round(revenue / spend, 2)
