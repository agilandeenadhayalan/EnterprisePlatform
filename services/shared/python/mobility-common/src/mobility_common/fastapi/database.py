"""
Async SQLAlchemy database session management.

WHY async? In a microservice that handles many concurrent requests (e.g., 1000
concurrent ride lookups), synchronous DB calls block the event loop. Async
SQLAlchemy with asyncpg lets FastAPI serve other requests while waiting for
PostgreSQL to respond.

PATTERN: "Session-per-request" — each HTTP request gets its own database session
via FastAPI's dependency injection. The session is committed on success and
rolled back on error, then always closed. This prevents connection leaks.

CONNECTION POOLING: SQLAlchemy's built-in pool (default: QueuePool, size=5,
max_overflow=10) reuses connections instead of opening/closing per request.
This avoids the ~5ms overhead of establishing a new PostgreSQL connection.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models across services.

    Every table model inherits from this. SQLAlchemy uses it to track
    all models and generate CREATE TABLE statements.
    """
    pass


# Module-level engine and session factory — initialized by create_engine_and_session()
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine_and_session(
    database_url: str,
    pool_size: int = 5,
    max_overflow: int = 10,
    echo: bool = False,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """
    Create and configure the async SQLAlchemy engine + session factory.

    Call this once during app startup (in the lifespan context manager).
    The engine manages the connection pool; the session factory creates
    per-request sessions.

    Args:
        database_url: PostgreSQL async URL (postgresql+asyncpg://...)
        pool_size: Base number of persistent connections
        max_overflow: Extra connections allowed under load
        echo: Log all SQL statements (useful for debugging N+1 queries)
    """
    global _engine, _session_factory

    _engine = create_async_engine(
        database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        echo=echo,
        # Recycle connections every 30 minutes to prevent stale connections
        pool_recycle=1800,
        # Pre-ping: test connection health before using it from the pool
        pool_pre_ping=True,
    )

    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Allow accessing attributes after commit
    )

    return _engine, _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.

    Usage in route handlers:
        @app.get("/users")
        async def list_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(UserModel))
            return result.scalars().all()

    The session is automatically closed after the request completes,
    even if an exception occurs.
    """
    if _session_factory is None:
        raise RuntimeError(
            "Database not initialized. Call create_engine_and_session() "
            "in your app's lifespan before handling requests."
        )

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def dispose_engine() -> None:
    """Cleanly shut down the connection pool during app shutdown."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
