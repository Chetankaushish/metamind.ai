from typing import Generic, TypeVar, Type, Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

ModelType = TypeVar("ModelType")

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        stmt = select(self.model).where(getattr(self.model, "id") == id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_multi(self, db: AsyncSession, *, offset: int = 0, limit: int = 100) -> List[ModelType]:
        stmt = select(self.model).offset(offset).limit(limit)
        res = await db.execute(stmt)
        return res.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: Any) -> ModelType:
        if isinstance(obj_in, dict):
            db_obj = self.model(**obj_in)
        else:
            db_obj = obj_in
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
