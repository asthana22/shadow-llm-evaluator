import logging

import httpx

from app.config import Settings
from app.db.client import create_engine, create_session_factory
from app.db.models import ShadowStatus
from app.db.repositories.proxy_request_repository import ProxyRequestRepository
from app.evaluator import evaluate_responses
from app.metrics.metrics_service import MetricsService
from app.metrics.metrics_store import MetricsStore, create_redis
from app.proxy.candidate_llm import CandidateLlmClient
from app.proxy.errors import PrimaryTimeoutError, PrimaryUnavailableError
from app.types.chat import SaveShadowResultInput

logger = logging.getLogger(__name__)


class ShadowService:
    def __init__(
        self,
        settings: Settings,
        repository: ProxyRequestRepository,
        candidate_client: CandidateLlmClient,
        metrics: MetricsService,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._candidate = candidate_client
        self._metrics = metrics

    async def process(self, request_id: str) -> None:
        logger.info("Shadow job started request_id=%s", request_id)
        record = await self._repository.get_by_request_id(request_id)
        if record is None:
            logger.error("Shadow job request not found request_id=%s", request_id)
            await self._metrics.record_shadow_error()
            return

        if record.shadow_status != ShadowStatus.PENDING.value:
            logger.info(
                "Shadow job skipped request_id=%s status=%s",
                request_id,
                record.shadow_status,
            )
            return

        claimed = await self._repository.mark_processing(request_id)
        if not claimed:
            logger.info("Shadow job already claimed request_id=%s", request_id)
            return

        candidate_status: int | None = None
        candidate_response: str | None = None
        latency_candidate_ms: int | None = None
        shadow_error: str | None = None
        shadow_status = ShadowStatus.COMPLETED.value

        logger.info(
            "Calling candidate LLM request_id=%s model=%s",
            request_id,
            self._settings.candidate_llm_model,
        )
        try:
            candidate_status, candidate_response, latency_candidate_ms = (
                await self._candidate.complete(record.request_body)
            )
            logger.info(
                "Candidate LLM response request_id=%s status=%s latency_ms=%s",
                request_id,
                candidate_status,
                latency_candidate_ms,
            )
        except PrimaryTimeoutError:
            logger.warning("Candidate LLM timeout request_id=%s", request_id)
            await self._metrics.record_shadow_timeout()
            await self._save_failure(
                request_id,
                ShadowStatus.FAILED.value,
                "candidate_timeout",
            )
            return
        except (PrimaryUnavailableError, httpx.HTTPError) as exc:
            logger.warning("Candidate LLM error request_id=%s error=%s", request_id, exc)
            await self._metrics.record_shadow_error()
            await self._save_failure(request_id, ShadowStatus.FAILED.value, str(exc))
            return

        if candidate_status is None or candidate_status >= 400:
            logger.warning(
                "Candidate LLM HTTP error request_id=%s status=%s",
                request_id,
                candidate_status,
            )
            await self._metrics.record_shadow_error()
            shadow_status = ShadowStatus.FAILED.value
            shadow_error = f"candidate_http_{candidate_status}"

        evaluation = evaluate_responses(record.primary_response, candidate_response or "")

        await self._repository.save_shadow_result(
            SaveShadowResultInput(
                request_id=request_id,
                candidate_status=candidate_status,
                candidate_response=candidate_response,
                latency_candidate_ms=latency_candidate_ms,
                primary_valid=evaluation.primary_valid,
                candidate_valid=evaluation.candidate_valid,
                exact_action_match=evaluation.exact_action_match,
                primary_action=evaluation.primary_action,
                candidate_action=evaluation.candidate_action,
                shadow_status=shadow_status,
                shadow_error=shadow_error,
            )
        )
        await self._metrics.record_comparison(evaluation.exact_action_match)
        logger.info(
            "Shadow job complete request_id=%s shadow_status=%s primary_valid=%s "
            "candidate_valid=%s exact_match=%s primary_action=%s candidate_action=%s",
            request_id,
            shadow_status,
            evaluation.primary_valid,
            evaluation.candidate_valid,
            evaluation.exact_action_match,
            evaluation.primary_action,
            evaluation.candidate_action,
        )

    async def _save_failure(self, request_id: str, status: str, error: str) -> None:
        logger.warning(
            "Shadow job failed request_id=%s status=%s error=%s",
            request_id,
            status,
            error,
        )
        record = await self._repository.get_by_request_id(request_id)
        if record is None:
            return
        evaluation = evaluate_responses(record.primary_response, "")
        await self._repository.save_shadow_result(
            SaveShadowResultInput(
                request_id=request_id,
                candidate_status=None,
                candidate_response=None,
                latency_candidate_ms=None,
                primary_valid=evaluation.primary_valid,
                candidate_valid=False,
                exact_action_match=False,
                primary_action=evaluation.primary_action,
                candidate_action=None,
                shadow_status=status,
                shadow_error=error,
            )
        )


async def process_shadow_request(_ctx: dict, request_id: str) -> None:
    logger.info("Worker received shadow job request_id=%s", request_id)
    settings = Settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    redis = await create_redis(settings)

    try:
        async with session_factory() as session:
            metrics = MetricsService(MetricsStore(redis))
            service = ShadowService(
                settings=settings,
                repository=ProxyRequestRepository(session),
                candidate_client=CandidateLlmClient(settings),
                metrics=metrics,
            )
            await service.process(request_id)
    finally:
        await redis.aclose()
        await engine.dispose()
