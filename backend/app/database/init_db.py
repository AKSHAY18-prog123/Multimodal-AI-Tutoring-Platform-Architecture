import asyncio
from sqlalchemy import select
from backend.app.database.session import engine, Base, AsyncSessionLocal
import backend.app.database.models # Import all models to register with Base.metadata
from backend.app.database.models.user import User
from backend.app.database.models.learner import LearnerProfile
from backend.app.core.logging import logger

async def init_database():
    """Create all SQLite tables cleanly without fake learner or course seed data."""
    logger.info("Initializing database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized cleanly (zero fake seed data).")

if __name__ == "__main__":
    asyncio.run(init_database())
