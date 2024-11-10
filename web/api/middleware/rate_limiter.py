# web/api/middleware/rate_limiter.py
from functools import wraps
from flask import request
import time
from utils.cache import cache

class RateLimiter:
    def __init__(self, max_requests, period):
        self.max_requests = max_requests
        self.period = period
        self.cache = cache

    def is_rate_limited(self, key):
        current = int(time.time())
        pipeline = self.cache.redis.pipeline()
        pipeline.zremrangebyscore(key, 0, current - self.period)
        pipeline.zcard(key)
        pipeline.zadd(key, {str(current): current})
        pipeline.expire(key, self.period)
        _, request_count, _, _ = pipeline.execute()
        return request_count > self.max_requests

def rate_limit(max_requests, period):
    limiter = RateLimiter(max_requests, period)
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            key = f'rate_limit:{request.remote_addr}:{f.__name__}'
            if limiter.is_rate_limited(key):
                return jsonify({'error': 'Rate limit exceeded'}), 429
            return f(*args, **kwargs)
        return decorated_function
    return decorator
