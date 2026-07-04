import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.db.repositories.proxy_request_repository import ProxyRequestRepository
from app.db.services.proxy_request_service import ProxyRequestService
from app.metrics.metrics_service import MetricsService
from app.metrics.metrics_store import MetricsStore, create_redis
from app.proxy.primary_llm import (
    PrimaryLlmClient,
    parse_request_body,
    prepare_upstream_body,
)
from app.queue.shadow_queue import ShadowQueue
from app.types.chat import PrimaryProxyResult

logger = logging.getLogger(__name__)


def _log_task_failure(task: asyncio.Task) -> None:
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.error("Primary side-effects task failed: %s", exc)


class PrimaryProxyService:
    """Primary LLM proxy — user response is never blocked by shadow/DB/metrics work."""

    def __init__(
        self,
        client: PrimaryLlmClient,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._client = client
        self._settings = settings
        self._session_factory = session_factory
        self._default_model = settings.primary_llm_model

    async def handle_chat(
        self,
        request_id: str,
        body: bytes,
        headers: dict[str, str],
    ) -> PrimaryProxyResult:
        upstream_body = prepare_upstream_body(body, self._default_model)
        result = await self._client.forward(upstream_body, headers)

        task = asyncio.create_task(
            self._run_side_effects(request_id=request_id, body=body, result=result),
            name=f"primary-side-effects-{request_id}",
        )
        task.add_done_callback(_log_task_failure)
        return result

    async def _run_side_effects(
        self,
        *,
        request_id: str,
        body: bytes,
        result: PrimaryProxyResult,
    ) -> None:
        redis = None
        try:
            redis = await create_redis(self._settings)
            metrics = MetricsService(MetricsStore(redis))
            shadow_queue = ShadowQueue(self._settings)

            async with self._session_factory() as session:
                proxy_service = ProxyRequestService(ProxyRequestRepository(session))
                try:
                    await proxy_service.save_primary_response(
                        request_id=request_id,
                        request_body=parse_request_body(body),
                        result=result,
                    )
                except Exception:
                    logger.exception("Failed to persist primary response for %s", request_id)
                    await session.rollback()

            try:
                await metrics.record_primary_processed()
            except Exception:
                logger.exception("Failed to record primary metrics for %s", request_id)

            if 200 <= result.status_code < 300:
                try:
                    enqueued = await shadow_queue.try_enqueue(request_id)
                    if not enqueued:
                        await metrics.record_shadow_shed()
                except Exception:
                    logger.exception("Failed to enqueue shadow job for %s", request_id)
                    try:
                        await metrics.record_shadow_error()
                    except Exception:
                        logger.exception(
                            "Failed to record shadow error metric for %s", request_id
                        )
        except Exception:
            logger.exception("Side effects failed for %s", request_id)
        finally:
            if redis is not None:
                await redis.aclose()
