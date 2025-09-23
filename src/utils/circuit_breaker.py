import functools
import time

class CircuitBreaker:
    """A simple circuit breaker implementation."""
    def __init__(self, failure_threshold=3, reset_timeout=10):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "CLOSED"

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if time.time() > self.last_failure_time + self.reset_timeout:
                    print("Circuit breaker attempting to half-open.")
                    self.state = "HALF-OPEN"
                else:
                    raise Exception("Circuit breaker is open. Service is unavailable.")

            try:
                result = func(*args, **kwargs)
                self.state = "CLOSED"
                self.failures = 0
                return result
            except Exception as e:
                self.failures += 1
                self.last_failure_time = time.time()
                print(f"Service call failed. Failures: {self.failures}/{self.failure_threshold}")
                if self.failures >= self.failure_threshold:
                    self.state = "OPEN"
                    print("Circuit breaker is now open.")
                raise e

        return wrapper

class CircuitBreakerFactory:
    """Factory to create circuit breaker decorators."""
    @staticmethod
    def create_breaker_decorator(name, failure_threshold=3, reset_timeout=10):
        breaker = CircuitBreaker(failure_threshold, reset_timeout)
        return breaker