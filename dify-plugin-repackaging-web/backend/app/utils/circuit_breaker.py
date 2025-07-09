import time
from typing import Callable, Any, Optional
from functools import wraps
import asyncio
import logging

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    A circuit breaker implementation to prevent cascade failures
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit is tripped, requests fail immediately
    - HALF_OPEN: Testing if service has recovered
    """
    
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        name: Optional[str] = None
    ):
        """
        Initialize the circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch (default: Exception)
            name: Optional name for logging
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name or "CircuitBreaker"
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = self.CLOSED
    
    def _record_success(self):
        """Record a successful call"""
        self.failure_count = 0
        self.last_failure_time = None
        if self.state == self.HALF_OPEN:
            self.state = self.CLOSED
            logger.info(f"{self.name}: Circuit closed after successful recovery")
    
    def _record_failure(self):
        """Record a failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = self.OPEN
            logger.warning(
                f"{self.name}: Circuit opened after {self.failure_count} failures"
            )
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit"""
        return (
            self.state == self.OPEN and
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call a function through the circuit breaker
        
        Args:
            func: Function to call
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Function result
            
        Raises:
            CircuitOpenError: If circuit is open
            Original exception: If function fails
        """
        if self.state == self.OPEN:
            if self._should_attempt_reset():
                self.state = self.HALF_OPEN
                logger.info(f"{self.name}: Attempting reset to half-open state")
            else:
                raise CircuitOpenError(
                    f"{self.name}: Circuit is open, not attempting call"
                )
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except self.expected_exception as e:
            self._record_failure()
            raise e
    
    async def async_call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call an async function through the circuit breaker
        
        Args:
            func: Async function to call
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Function result
            
        Raises:
            CircuitOpenError: If circuit is open
            Original exception: If function fails
        """
        if self.state == self.OPEN:
            if self._should_attempt_reset():
                self.state = self.HALF_OPEN
                logger.info(f"{self.name}: Attempting reset to half-open state")
            else:
                raise CircuitOpenError(
                    f"{self.name}: Circuit is open, not attempting call"
                )
        
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except self.expected_exception as e:
            self._record_failure()
            raise e
    
    def decorator(self, func: Callable) -> Callable:
        """
        Decorator version of the circuit breaker
        
        Args:
            func: Function to wrap
            
        Returns:
            Wrapped function
        """
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self.async_call(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                return self.call(func, *args, **kwargs)
            return wrapper
    
    def get_state(self) -> dict:
        """Get current circuit breaker state"""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "name": self.name
        }
    
    def reset(self):
        """Manually reset the circuit breaker to closed state"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = self.CLOSED
        logger.info(f"{self.name}: Circuit manually reset to closed state")


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


# Create singleton instances for different services
marketplace_circuit_breaker = CircuitBreaker(
    failure_threshold=5,  # Increased from 3 to be more tolerant
    recovery_timeout=15,  # Reduced from 30 to recover faster
    expected_exception=Exception,
    name="MarketplaceAPI"
)