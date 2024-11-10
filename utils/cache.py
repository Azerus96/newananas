# utils/cache.py
from functools import wraps
import redis
from config import Config

class Cache:
    def __init__(self):
        self.redis = redis.Redis.from_url(Config.REDIS_URL)

    def memoize(self, timeout=300):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                key = f"{f.__name__}:{str(args)}:{str(kwargs)}"
                result = self.redis.get(key)
                if result is not None:
                    return result
                result = f(*args, **kwargs)
                self.redis.setex(key, timeout, result)
                return result
            return decorated_function
        return decorator

cache = Cache()
