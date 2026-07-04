from datetime import datetime, timezone

from app.db.models import ShadowEvaluationModel
from app.db.repositories.shadow_evaluation_repository import ShadowEvaluationRepository
from app.types.shadow_evaluation import (
    CreateShadowEvaluationInput,
    ShadowEvaluationRecord,
)


class ShadowEvaluationService:
    """
    Business logic for persisting shadow evaluation audit records.

    Does NOT: call LLMs, run heuristics, or update Redis metrics.
    """

    def __init__(
        self,
        repository: ShadowEvaluationRepository,
        enable_audit_log: bool,
    ) -> None:
        self._repository = repository
        self._enable_audit_log = enable_audit_log

    def is_enabled(self) -> bool:
        return self._enable_audit_log

    async def record_evaluation(
        self, input_data: CreateShadowEvaluationInput
    ) -> ShadowEvaluationRecord | None:
        if not self._enable_audit_log:
            return None

        record = self._build_record(input_data)
        await self._repository.insert(record)
        return record

    async def get_by_request_id(self, request_id: str) -> ShadowEvaluationRecord | None:
        if not self._enable_audit_log:
            return None
        return await self._repository.find_by_request_id(request_id)

    def _build_record(self, input_data: CreateShadowEvaluationInput) -> ShadowEvaluationRecord:
        return ShadowEvaluationRecord(
            id=ShadowEvaluationModel.new_id(),
            request_id=input_data.request_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            request_body=input_data.request_body,
            primary_status=input_data.primary_status,
            primary_response=input_data.primary_response,
            candidate_status=input_data.candidate_status,
            candidate_response=input_data.candidate_response,
            primary_valid=input_data.primary_valid,
            candidate_valid=input_data.candidate_valid,
            exact_action_match=input_data.exact_action_match,
            primary_action=input_data.primary_action,
            candidate_action=input_data.candidate_action,
            shadow_outcome=input_data.shadow_outcome,
            latency_primary_ms=input_data.latency_primary_ms,
            latency_candidate_ms=input_data.latency_candidate_ms,
            error_message=input_data.error_message,
        )
