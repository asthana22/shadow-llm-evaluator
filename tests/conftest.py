import os
import tempfile
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import fakeredis.aioredis
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings, get_settings
from app.db.client import create_engine, create_session_factory, init_db
from app.db.models import Base
from app.dependencies import get_db_session, get_metrics_service, get_shadow_queue
from app.main import create_app
from app.metrics.metrics_service import MetricsService
from app.queue.shadow_queue import ShadowQueue


@pytest.fixture
def sqlite_settings() -> Settings:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return Settings(
        db_driver="sqlite",
        sqlite_path=path,
        enable_audit_log=True,
    )


@pytest_asyncio.fixture
async def db_session(sqlite_settings: Settings) -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{sqlite_settings.sqlite_path}",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()
    if os.path.exists(sqlite_settings.sqlite_path):
        os.unlink(sqlite_settings.sqlite_path)


@pytest_asyncio.fixture
async def chat_app(sqlite_settings, monkeypatch):
    monkeypatch.setenv("DB_DRIVER", "sqlite")
    monkeypatch.setenv("SQLITE_PATH", sqlite_settings.sqlite_path)
    get_settings.cache_clear()

    engine = create_engine(get_settings())
    await init_db(engine)
    session_factory = create_session_factory(engine)

    app = create_app()

    async def override_db_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.redis = fakeredis.aioredis.FakeRedis(decode_responses=True)

    mock_queue = AsyncMock(spec=ShadowQueue)
    mock_queue.try_enqueue = AsyncMock(return_value=True)
    app.dependency_overrides[get_shadow_queue] = lambda: mock_queue

    mock_metrics = AsyncMock(spec=MetricsService)
    app.dependency_overrides[get_metrics_service] = lambda: mock_metrics

    yield app

    app.dependency_overrides.clear()
    await engine.dispose()
    get_settings.cache_clear()
