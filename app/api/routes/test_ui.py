from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.config import get_settings

router = APIRouter()

_STATIC_DIR = Path(__file__).resolve().parents[2] / "static" / "test-ui"


@router.get("/test")
async def test_ui() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@router.get("/test/config")
async def test_ui_config() -> dict:
    settings = get_settings()
    return {
        "default_model": settings.primary_llm_model,
        "chat_endpoint": "/v1/chat",
        "metrics_endpoint": "/metrics",
    }
