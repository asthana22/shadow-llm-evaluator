from fastapi import FastAPI

from app.api.routes import chat, health, metrics, test_ui
from app.middleware.errors import lifespan, primary_proxy_exception_handler
from app.proxy.errors import PrimaryProxyError


def create_app() -> FastAPI:
    application = FastAPI(
        title="Shadow-Mode LLM Evaluator API",
        description="Proxy primary LLM traffic and async shadow-evaluate a candidate LLM",
        version="1.0.0",
        lifespan=lifespan,
    )

    application.add_exception_handler(PrimaryProxyError, primary_proxy_exception_handler)

    application.include_router(health.router, tags=["health"])
    application.include_router(chat.router, tags=["chat"])
    application.include_router(metrics.router, tags=["metrics"])
    application.include_router(test_ui.router, tags=["test-ui"])

    return application


app = create_app()
