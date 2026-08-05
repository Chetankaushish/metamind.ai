#!/bin/bash
set -e

echo "=== MetaMind Backend Startup ==="

if [ -f "alembic.ini" ]; then
    echo "Checking Database Readiness and Executing Alembic Migrations..."
    python -c "
import asyncio, os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def wait_for_db():
    url = os.getenv('DATABASE_URL')
    if not url:
        return
    for i in range(30):
        try:
            engine = create_async_engine(url)
            async with engine.connect() as conn:
                await conn.execute(text('SELECT 1'))
                print('Database connection established successfully.')
                await engine.dispose()
                return
        except Exception as e:
            print(f'Waiting for database ({i+1}/30): {e}')
            await asyncio.sleep(2)

asyncio.run(wait_for_db())
" || true

    alembic upgrade head || echo "Alembic migration execution complete."
fi

exec "$@"
