class PrimaryProxyError(Exception):
    """Base error for primary LLM proxy failures."""


class PrimaryTimeoutError(PrimaryProxyError):
    """Primary LLM did not respond within the configured timeout."""


class PrimaryUnavailableError(PrimaryProxyError):
    """Primary LLM could not be reached."""
