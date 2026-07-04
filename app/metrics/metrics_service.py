from app.metrics.metrics_store import MetricsStore


class MetricsService:
    def __init__(self, store: MetricsStore) -> None:
        self._store = store

    async def record_primary_processed(self) -> None:
        await self._store.increment("total_requests_processed")

    async def record_shadow_shed(self) -> None:
        await self._store.increment("shadow_tasks_shed")

    async def record_shadow_error(self) -> None:
        await self._store.increment("shadow_execution_errors")

    async def record_shadow_timeout(self) -> None:
        await self._store.increment("shadow_execution_timeouts")

    async def record_comparison(self, exact_match: bool) -> None:
        await self._store.increment("comparisons_completed")
        if exact_match:
            await self._store.increment("exact_match_count")

    async def get_metrics(self):
        return await self._store.get_all()
