import logging

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

SHADOW_JOB_NAME = "process_shadow_request"
ARQ_QUEUE_KEY = "arq:queue"


class ShadowQueue:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def _pool(self) -> ArqRedis:
        return await create_pool(RedisSettings.from_dsn(self._settings.redis_url))

    async def queue_depth(self, pool: ArqRedis) -> int:
        return await pool.zcard(ARQ_QUEUE_KEY)

    async def try_enqueue(self, request_id: str) -> bool:
        """Returns True if enqueued, False if shed due to capacity."""
        pool = await self._pool()
        try:
            depth = await self.queue_depth(pool)
            if depth >= self._settings.shadow_max_queue_size:
                logger.warning("Shadow queue full (%s), shedding %s", depth, request_id)
                return False
            await pool.enqueue_job(SHADOW_JOB_NAME, request_id)
            return True
        finally:
            await pool.aclose()
