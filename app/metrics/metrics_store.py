from redis.asyncio import Redis

from app.config import Settings
from app.types.shadow_evaluation import MetricsResponse

METRIC_KEYS = {
    "total_requests_processed": "metrics:total_requests",
    "shadow_execution_errors": "metrics:shadow_errors",
    "shadow_execution_timeouts": "metrics:shadow_timeouts",
    "shadow_tasks_shed": "metrics:shadow_shed",
    "comparisons_completed": "metrics:comparisons_completed",
    "exact_match_count": "metrics:exact_match_count",
}


class MetricsStore:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def increment(self, key: str, amount: int = 1) -> None:
        await self._redis.incrby(METRIC_KEYS[key], amount)

    async def get_all(self) -> MetricsResponse:
        values: dict[str, int] = {}
        for field, redis_key in METRIC_KEYS.items():
            raw = await self._redis.get(redis_key)
            values[field] = int(raw) if raw else 0

        completed = values["comparisons_completed"]
        matches = values["exact_match_count"]
        rate = (matches / completed) if completed > 0 else 0.0

        return MetricsResponse(
            total_requests_processed=values["total_requests_processed"],
            shadow_execution_errors=values["shadow_execution_errors"],
            shadow_execution_timeouts=values["shadow_execution_timeouts"],
            shadow_tasks_shed=values["shadow_tasks_shed"],
            comparisons_completed=completed,
            exact_match_count=matches,
            exact_match_rate=round(rate, 4),
        )


async def create_redis(settings: Settings | None = None) -> Redis:
    from app.config import get_settings

    cfg = settings or get_settings()
    return Redis.from_url(cfg.redis_url, decode_responses=True)
