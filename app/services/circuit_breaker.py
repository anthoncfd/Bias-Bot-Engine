import time
import threading
import logging

logger = logging.getLogger(__name__)

class CircuitBreaker:
    def __init__(self, fail_threshold=3, timeout=60):
        self.fail_threshold = fail_threshold
        self.timeout = timeout
        self.fail_count = 0
        self.last_fail_time = 0
        self.state = "CLOSED"
        self.lock = threading.Lock()

    def call(self, func, *args, **kwargs):
        with self.lock:
            if self.state == "OPEN":
                if time.time() - self.last_fail_time > self.timeout:
                    self.state = "HALF_OPEN"
                    logger.info("Circuit breaker system shifting to state: HALF_OPEN. Triggering trial executions.")
                else:
                    raise Exception("System exception: Circuit breaker is locked in OPEN state.")
        try:
            result = func(*args, **kwargs)
            with self.lock:
                if self.state == "HALF_OPEN":
                    self.state = "CLOSED"
                    self.fail_count = 0
                    logger.info("System loop verified functional. Circuit breaker returned to state: CLOSED.")
            return result
        except Exception as e:
            with self.lock:
                self.fail_count += 1
                self.last_fail_time = time.time()
                if self.fail_count >= self.fail_threshold:
                    self.state = "OPEN"
                    logger.error(f"Execution failed {self.fail_count} times sequentially. System routing isolated to state: OPEN.")
            raise e
