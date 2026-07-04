import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db.client import create_engine, create_session_factory, init_db
from app.logging_config import configure_logging
from app.metrics.metrics_store import create_redis
from app.proxy.errors import PrimaryProxyError, PrimaryTimeoutError, PrimaryUnavailableError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = create_engine(settings)
    await init_db(engine)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.redis = await create_redis(settings)
    yield
    await app.state.redis.aclose()
    await engine.dispose()


async def primary_proxy_exception_handler(
    _request: Request, exc: PrimaryProxyError
) -> JSONResponse:
    if isinstance(exc, PrimaryTimeoutError):
        logger.warning("Primary proxy timeout: %s", exc)
        return JSONResponse(
            status_code=504,
            content={"error": str(exc), "code": "PRIMARY_TIMEOUT"},
        )
    if isinstance(exc, PrimaryUnavailableError):
        logger.warning("Primary proxy unavailable: %s", exc)
        return JSONResponse(
            status_code=502,
            content={"error": str(exc), "code": "PRIMARY_UNAVAILABLE"},
        )
    logger.error("Primary proxy error: %s", exc)
    return JSONResponse(
        status_code=502,
        content={"error": str(exc), "code": "PRIMARY_PROXY_ERROR"},
    )
