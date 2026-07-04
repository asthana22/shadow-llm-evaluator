from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProxyRequestModel, ShadowStatus
from app.types.chat import (
    ProxyRequestRecord,
    SaveProxyRequestInput,
    SaveShadowResultInput,
)


class ProxyRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, input_data: SaveProxyRequestInput) -> ProxyRequestRecord:
        row = ProxyRequestModel(
            request_id=input_data.request_id,
            request_body=input_data.request_body,
            primary_status=input_data.primary_status,
            primary_response=input_data.primary_response,
            latency_primary_ms=input_data.latency_primary_ms,
            shadow_status=ShadowStatus.PENDING.value,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _to_record(row)

    async def get_by_request_id(self, request_id: str) -> ProxyRequestRecord | None:
        result = await self._session.execute(
            select(ProxyRequestModel).where(ProxyRequestModel.request_id == request_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return _to_record(row)

    async def mark_processing(self, request_id: str) -> bool:
        result = await self._session.execute(
            update(ProxyRequestModel)
            .where(
                ProxyRequestModel.request_id == request_id,
                ProxyRequestModel.shadow_status == ShadowStatus.PENDING.value,
            )
            .values(shadow_status=ShadowStatus.PROCESSING.value)
        )
        await self._session.commit()
        return result.rowcount > 0

    async def save_shadow_result(self, input_data: SaveShadowResultInput) -> None:
        await self._session.execute(
            update(ProxyRequestModel)
            .where(ProxyRequestModel.request_id == input_data.request_id)
            .values(
                candidate_status=input_data.candidate_status,
                candidate_response=input_data.candidate_response,
                latency_candidate_ms=input_data.latency_candidate_ms,
                primary_valid=input_data.primary_valid,
                candidate_valid=input_data.candidate_valid,
                exact_action_match=input_data.exact_action_match,
                primary_action=input_data.primary_action,
                candidate_action=input_data.candidate_action,
                shadow_status=input_data.shadow_status,
                shadow_error=input_data.shadow_error,
            )
        )
        await self._session.commit()


def _to_record(row: ProxyRequestModel) -> ProxyRequestRecord:
    return ProxyRequestRecord(
        request_id=row.request_id,
        request_body=row.request_body,
        primary_status=row.primary_status,
        primary_response=row.primary_response,
        latency_primary_ms=row.latency_primary_ms,
        shadow_status=row.shadow_status,
        created_at=row.created_at.isoformat(),
        candidate_status=row.candidate_status,
        candidate_response=row.candidate_response,
        latency_candidate_ms=row.latency_candidate_ms,
        primary_valid=row.primary_valid,
        candidate_valid=row.candidate_valid,
        exact_action_match=row.exact_action_match,
        primary_action=row.primary_action,
        candidate_action=row.candidate_action,
        shadow_error=row.shadow_error,
    )
