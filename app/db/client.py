import logging
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings, get_settings
from app.db.models import Base

logger = logging.getLogger(__name__)

# Columns added after initial proxy_requests table — applied on startup for SQLite.
SQLITE_PROXY_REQUESTS_COLUMNS: tuple[tuple[str, str], ...] = (
    ("candidate_status", "INTEGER"),
    ("candidate_response", "TEXT"),
    ("latency_candidate_ms", "INTEGER"),
    ("primary_valid", "INTEGER"),
    ("candidate_valid", "INTEGER"),
    ("exact_action_match", "INTEGER"),
    ("primary_action", "VARCHAR(255)"),
    ("candidate_action", "VARCHAR(255)"),
    ("shadow_error", "TEXT"),
)


def create_engine(settings: Settings | None = None) -> AsyncEngine:
    cfg = settings or get_settings()
    if cfg.resolved_db_driver == "sqlite":
        db_path = Path(cfg.sqlite_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_async_engine(cfg.sqlalchemy_url, echo=False)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def _migrate_sqlite_proxy_requests(sync_conn) -> None:
    inspector = inspect(sync_conn)
    if not inspector.has_table("proxy_requests"):
        return

    existing = {column["name"] for column in inspector.get_columns("proxy_requests")}
    for column_name, column_type in SQLITE_PROXY_REQUESTS_COLUMNS:
        if column_name in existing:
            continue
        sync_conn.execute(
            text(f"ALTER TABLE proxy_requests ADD COLUMN {column_name} {column_type}")
        )
        logger.info("Added missing column proxy_requests.%s", column_name)


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if conn.dialect.name == "sqlite":
            await conn.run_sync(_migrate_sqlite_proxy_requests)


async def get_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session
