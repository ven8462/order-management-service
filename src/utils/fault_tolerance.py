import logging
from tenacity import (
    retry,
    wait_fixed,
    stop_after_attempt,
    retry_if_exception_type,
    before_sleep_log,
)

from src.utils.circuit_breaker import CircuitBreakerFactory

# Configure a logger for this utility
logger = logging.getLogger(__name__)

# A custom decorator that applies both Circuit Breaker and Tenacity Retry
def fault_tolerant(retries=3, wait_time=2, retry_on_status_codes=None):
    if retry_on_status_codes is None:
        retry_on_status_codes = [502, 503, 504]

    def decorator(func):
        # Apply the Circuit Breaker from your existing factory
        breaker_func = CircuitBreakerFactory.create_breaker_decorator(func)

        @retry(
            wait=wait_fixed(wait_time),
            stop=stop_after_attempt(retries),
            retry=retry_if_exception_type(Exception),
            # This needs to be refined for specific errors
            before_sleep=before_sleep_log(logger, logging.INFO),
        )
        def wrapper(*args, **kwargs):
            return breaker_func(*args, **kwargs)

        return wrapper
    return decorator
