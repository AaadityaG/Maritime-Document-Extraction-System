"""Database configuration and session management"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import AsyncGenerator
import asyncio

from app.core.config import settings


# Base class for all models
Base = declarative_base()


class DatabaseManager:
    """Database connection manager"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.async_session_maker = None
    
    async def connect(self):
        """Initialize database connection"""
        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            future=True
        )
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
        
        # Create tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def disconnect(self):
        """Close database connection"""
        if self.engine:
            await self.engine.dispose()
    
    def get_session(self) -> AsyncSession:
        """Get database session"""
        return self.async_session_maker()


# Global database manager instance
db_manager: DatabaseManager | None = None


async def init_database():
    """Initialize global database manager"""
    global db_manager
    db_manager = DatabaseManager(settings.DATABASE_URL)
    await db_manager.connect()
    return db_manager


async def close_database():
    """Close global database connection"""
    global db_manager
    if db_manager:
        await db_manager.disconnect()
        db_manager = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session"""
    if db_manager is None:
        raise RuntimeError("Database not initialized")
    
    db = db_manager.get_session()
    try:
        yield db
    finally:
        await db.close()
