import time
from collections import deque

class RateLimiter:
    def __init__(self, max_calls_per_minute: int = 10):
        self.max_calls = max_calls_per_minute
        self.calls = deque()
    
    def is_allowed(self) -> bool:
        current_time = time.time()
        cutoff_time = current_time - 60
        
        # Remove old calls
        while self.calls and self.calls[0] < cutoff_time:
            self.calls.popleft()
        
        return len(self.calls) < self.max_calls
    
    def record_call(self):
        self.calls.append(time.time())
    
    def reset(self):
        self.calls = deque()

# Global rate limiter
web_rate_limiter = RateLimiter(max_calls_per_minute=10)