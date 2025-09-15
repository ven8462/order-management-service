import logging

from django.conf import settings
from pybreaker import CircuitBreaker, CircuitBreakerListener, CircuitBreakerState

logger = logging.getLogger(__name__)


class MonitoringListener(CircuitBreakerListener):
    def state_change(
        self,
        cb: CircuitBreaker,
        old_state: CircuitBreakerState,
        new_state: CircuitBreakerState,
    ) -> None:
        logger.warning(
            "CircuitBreaker '%s' state changed: '%s' -> '%s'",
            cb.name,
            old_state,
            new_state,
        )

    def failure(self, cb: CircuitBreaker, exc: Exception) -> None:
        logger.error(
            "CircuitBreaker '%s' recorded failure. Count: %d",
            cb.name,
            cb.fail_counter,
        )


class CircuitBreakerFactory:
    def __init__(self) -> None:
        self._breakers = {}
        self._listener = MonitoringListener()

    def get_breaker(self, service_name: str) -> CircuitBreaker:
        service_name = service_name.upper()
        if service_name not in self._breakers:
            fail_max = getattr(settings, f"CB_{service_name}_FAIL_MAX")
            reset_timeout = getattr(settings, f"CB_{service_name}_RESET_TIMEOUT")

            breaker = CircuitBreaker(
                fail_max=fail_max,
                reset_timeout=reset_timeout,
                listeners=[self._listener],
                name=service_name,
            )
            self._breakers[service_name] = breaker
            logger.info(
                "Initialized breaker for '%s': fail_max=%s, reset_timeout=%s",
                service_name,
                fail_max,
                reset_timeout,
            )

        return self._breakers[service_name]


breaker_factory = CircuitBreakerFactory()
