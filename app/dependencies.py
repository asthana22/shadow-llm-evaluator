from collections.abc import AsyncGenerator
from uuid import uuid4

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings, get_settings
from app.db.repositories.proxy_request_repository import ProxyRequestRepository
from app.db.services.proxy_request_service import ProxyRequestService
from app.metrics.metrics_service import MetricsService
from app.metrics.metrics_store import MetricsStore
from app.proxy.primary_llm import PrimaryLlmClient
from app.proxy.primary_proxy_service import PrimaryProxyService
from app.queue.shadow_queue import ShadowQueue


def generate_request_id() -> str:
    """Server-generated UUID — never trust client-provided IDs (PK collision risk)."""
    return str(uuid4())


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        yield session


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


def get_metrics_service(redis: Redis = Depends(get_redis)) -> MetricsService:
    return MetricsService(MetricsStore(redis))


def get_shadow_queue(settings: Settings = Depends(get_settings)) -> ShadowQueue:
    return ShadowQueue(settings)


def get_primary_llm_client(
    settings: Settings = Depends(get_settings),
) -> PrimaryLlmClient:
    return PrimaryLlmClient(settings)


def get_proxy_request_service(
    session: AsyncSession = Depends(get_db_session),
) -> ProxyRequestService:
    return ProxyRequestService(ProxyRequestRepository(session))


def get_primary_proxy_service(
    request: Request,
    client: PrimaryLlmClient = Depends(get_primary_llm_client),
    settings: Settings = Depends(get_settings),
) -> PrimaryProxyService:
    return PrimaryProxyService(
        client,
        settings,
        request.app.state.session_factory,
    )
