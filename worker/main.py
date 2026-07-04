from arq.connections import RedisSettings

from app.config import get_settings
from app.logging_config import configure_logging
from app.shadow.shadow_service import process_shadow_request

settings = get_settings()
configure_logging(settings.log_level)


class WorkerSettings:
    functions = [process_shadow_request]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = settings.shadow_max_concurrency
    job_timeout = settings.shadow_job_timeout_ms / 1000
