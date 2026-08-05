from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.database import get_db
from app.models.models import MetaAdSet as AdSetModel
from app.schemas.schemas import AdSetResponse

router = APIRouter()

@router.get("/adsets", response_model=List[AdSetResponse], tags=["AdSets"])
async def list_adsets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AdSetModel))
    adsets = result.scalars().all()
    return adsets
