from app.db.repositories.proxy_request_repository import ProxyRequestRepository
from app.types.chat import (
    PrimaryProxyResult,
    ProxyRequestRecord,
    SaveProxyRequestInput,
)


class ProxyRequestService:
    """Persists primary proxy responses for later shadow evaluation."""

    def __init__(self, repository: ProxyRequestRepository) -> None:
        self._repository = repository

    async def save_primary_response(
        self,
        request_id: str,
        request_body: object,
        result: PrimaryProxyResult,
    ) -> ProxyRequestRecord:
        return await self._repository.save(
            SaveProxyRequestInput(
                request_id=request_id,
                request_body=request_body,
                primary_status=result.status_code,
                primary_response=result.body,
                latency_primary_ms=result.latency_ms,
            )
        )

    async def get_by_request_id(self, request_id: str) -> ProxyRequestRecord | None:
        return await self._repository.get_by_request_id(request_id)
