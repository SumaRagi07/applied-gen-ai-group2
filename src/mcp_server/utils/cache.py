import time
from typing import Optional, Any

class SimpleCache:
    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            value, expiry_time = self.cache[key]
            if time.time() < expiry_time:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        expiry_time = time.time() + self.ttl
        self.cache[key] = (value, expiry_time)
    
    def clear_expired(self):
        current_time = time.time()
        expired_keys = [
            key for key, (_, expiry) in self.cache.items()
            if current_time >= expiry
        ]
        for key in expired_keys:
            del self.cache[key]
    
    def clear(self):
        self.cache = {}

# Global cache instance
web_cache = SimpleCache(ttl_seconds=300)