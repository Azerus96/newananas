# web/api/middleware/auth.py
from functools import wraps
from flask import request, jsonify, session
from utils.error_handlers import AuthError

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            raise AuthError('Authentication required', code=401)
        return f(*args, **kwargs)
    return decorated

def validate_session():
    user_id = session.get('user_id')
    if not user_id:
        raise AuthError('Invalid session', code=401)
    return user_id
