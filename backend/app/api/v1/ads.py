from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.database import get_db
from app.models.models import MetaAd as AdModel
from app.schemas.schemas import AdResponse

router = APIRouter()

@router.get("/ads", response_model=List[AdResponse], tags=["Ads"])
async def list_ads(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AdModel))
    ads = result.scalars().all()
    return ads
