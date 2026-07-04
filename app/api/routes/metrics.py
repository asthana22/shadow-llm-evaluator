from fastapi import APIRouter, Depends

from app.dependencies import get_metrics_service
from app.metrics.metrics_service import MetricsService
from app.types.shadow_evaluation import MetricsResponse

router = APIRouter()


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    metrics_service: MetricsService = Depends(get_metrics_service),
) -> MetricsResponse:
    return await metrics_service.get_metrics()
