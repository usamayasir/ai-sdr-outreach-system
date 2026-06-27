"""Async SQLAlchemy database engine and session factory."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from config.settings import get_settings

settings = get_settings()
engine = create_async_engine(settings.database_url, echo=False, future=True)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """Yield an async database session."""
    async with async_session() as session:
        yield session
