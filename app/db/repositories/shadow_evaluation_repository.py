import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ShadowEvaluationModel
from app.types.shadow_evaluation import ShadowEvaluationRecord


class ShadowEvaluationRepository:
    """Data access only — works with SQLite (local) and Postgres (prod)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(self, record: ShadowEvaluationRecord) -> None:
        row = ShadowEvaluationModel(
            id=record.id,
            request_id=record.request_id,
            created_at=_parse_datetime(record.created_at),
            request_body=record.request_body,
            primary_status=record.primary_status,
            primary_response=record.primary_response,
            candidate_status=record.candidate_status,
            candidate_response=record.candidate_response,
            primary_valid=record.primary_valid,
            candidate_valid=record.candidate_valid,
            exact_action_match=record.exact_action_match,
            primary_action=record.primary_action,
            candidate_action=record.candidate_action,
            shadow_outcome=record.shadow_outcome.value,
            latency_primary_ms=record.latency_primary_ms,
            latency_candidate_ms=record.latency_candidate_ms,
            error_message=record.error_message,
        )
        self._session.add(row)
        await self._session.commit()

    async def find_by_request_id(self, request_id: str) -> ShadowEvaluationRecord | None:
        result = await self._session.execute(
            select(ShadowEvaluationModel).where(
                ShadowEvaluationModel.request_id == request_id
            ).limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return _to_record(row)

    async def count_by_outcome(self, outcome: str) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(ShadowEvaluationModel)
            .where(ShadowEvaluationModel.shadow_outcome == outcome)
        )
        return int(result.scalar_one())


def _to_record(row: ShadowEvaluationModel) -> ShadowEvaluationRecord:
    from app.types.shadow_evaluation import ShadowOutcome

    return ShadowEvaluationRecord(
        id=row.id,
        request_id=row.request_id,
        created_at=row.created_at.isoformat(),
        request_body=row.request_body,
        primary_status=row.primary_status,
        primary_response=row.primary_response,
        candidate_status=row.candidate_status,
        candidate_response=row.candidate_response,
        primary_valid=row.primary_valid,
        candidate_valid=row.candidate_valid,
        exact_action_match=row.exact_action_match,
        primary_action=row.primary_action,
        candidate_action=row.candidate_action,
        shadow_outcome=ShadowOutcome(row.shadow_outcome),
        latency_primary_ms=row.latency_primary_ms,
        latency_candidate_ms=row.latency_candidate_ms,
        error_message=row.error_message,
    )


def _parse_datetime(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def run_migrations(settings=None) -> None:
    """Create tables via SQLAlchemy metadata (sqlite + postgres)."""
    from app.config import get_settings
    from app.db.client import create_engine, init_db

    cfg = settings or get_settings()
    engine = create_engine(cfg)
    await init_db(engine)
    await engine.dispose()


def run_migrations_sync() -> None:
    asyncio.run(run_migrations())


if __name__ == "__main__":
    run_migrations_sync()
