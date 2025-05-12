import redis
import json
from datetime import timedelta, datetime
from typing import Optional, Any, Dict, List
import logging
import os

logger = logging.getLogger(__name__)

def default_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

class Cache:
    def __init__(self, host=None, port=None, db=0):
        try:
            # Use environment variables with fallback to default values
            redis_host = host or os.getenv('REDIS_HOST', 'localhost')
            redis_port = port or int(os.getenv('REDIS_PORT', 6379))
            
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=db,
                decode_responses=True
            )
            logger.info(f"Successfully connected to Redis at {redis_host}:{redis_port}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self.redis_client = None

    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Store data in cache with expiration time in seconds"""
        try:
            if self.redis_client:
                serialized_value = json.dumps(value, default=default_serializer)
                return self.redis_client.setex(key, expire, serialized_value)
            return False
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """Retrieve data from cache"""
        try:
            if self.redis_client:
                data = self.redis_client.get(key)
                return json.loads(data) if data else None
            return None
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None

    def delete(self, key: str) -> bool:
        """Delete data from cache"""
        try:
            if self.redis_client:
                return bool(self.redis_client.delete(key))
            return False
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            return False

    def clear_pattern(self, pattern: str) -> bool:
        """Clear all keys matching a pattern"""
        try:
            if self.redis_client:
                keys = self.redis_client.keys(pattern)
                if keys:
                    return bool(self.redis_client.delete(*keys))
            return False
        except Exception as e:
            logger.error(f"Cache clear pattern error: {str(e)}")
            return False

# Create a global cache instance
cache = Cache()

# Cache key generators
def get_branch_cache_key(branch_id: int) -> str:
    return f"branch:{branch_id}"

def get_transaction_cache_key(transaction_id: str) -> str:
    return f"transaction:{transaction_id}"

def get_branch_transactions_cache_key(branch_id: int, status: Optional[str] = None) -> str:
    return f"branch_transactions:{branch_id}:{status or 'all'}"

def get_branch_stats_cache_key(branch_id: int) -> str:
    return f"branch_stats:{branch_id}"

# Cache decorator
def cache_result(expire: int = 3600):
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # If not in cache, execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(cache_key, result, expire)
            
            return result
        return wrapper
    return decorator 