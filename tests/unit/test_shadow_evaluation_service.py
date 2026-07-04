import pytest

from app.db.repositories.shadow_evaluation_repository import ShadowEvaluationRepository
from app.db.services.shadow_evaluation_service import ShadowEvaluationService
from app.types.shadow_evaluation import CreateShadowEvaluationInput, ShadowOutcome


@pytest.fixture
def sample_input() -> CreateShadowEvaluationInput:
    return CreateShadowEvaluationInput(
        request_id="req-123",
        request_body={"prompt": "hello"},
        primary_status=200,
        primary_response='{"action":"search"}',
        candidate_status=200,
        candidate_response='{"action":"search"}',
        primary_valid=True,
        candidate_valid=True,
        exact_action_match=True,
        primary_action="search",
        candidate_action="search",
        shadow_outcome=ShadowOutcome.COMPLETED,
        latency_primary_ms=120,
        latency_candidate_ms=340,
    )


@pytest.mark.asyncio
async def test_skips_persistence_when_audit_disabled(db_session, sample_input):
    repo = ShadowEvaluationRepository(db_session)
    service = ShadowEvaluationService(repo, enable_audit_log=False)

    result = await service.record_evaluation(sample_input)
    assert result is None


@pytest.mark.asyncio
async def test_persists_evaluation_when_audit_enabled(db_session, sample_input):
    repo = ShadowEvaluationRepository(db_session)
    service = ShadowEvaluationService(repo, enable_audit_log=True)

    result = await service.record_evaluation(sample_input)
    assert result is not None
    assert result.request_id == "req-123"
    assert result.exact_action_match is True

    found = await service.get_by_request_id("req-123")
    assert found is not None
    assert found.primary_action == "search"


@pytest.mark.asyncio
async def test_repository_insert_and_find(db_session):
    from datetime import datetime, timezone

    from app.types.shadow_evaluation import ShadowEvaluationRecord

    repo = ShadowEvaluationRepository(db_session)
    record = ShadowEvaluationRecord(
        id="uuid-1",
        request_id="req-abc",
        created_at=datetime.now(timezone.utc).isoformat(),
        request_body={"foo": "bar"},
        primary_status=200,
        primary_response='{"action":"x"}',
        candidate_status=200,
        candidate_response='{"action":"y"}',
        primary_valid=True,
        candidate_valid=True,
        exact_action_match=False,
        primary_action="x",
        candidate_action="y",
        shadow_outcome=ShadowOutcome.COMPLETED,
        latency_primary_ms=50,
        latency_candidate_ms=80,
        error_message=None,
    )

    await repo.insert(record)
    row = await repo.find_by_request_id("req-abc")
    assert row is not None
    assert row.primary_action == "x"
    assert row.exact_action_match is False
