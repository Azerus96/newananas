# utils/error_handlers.py
from typing import Type, Dict, Any
from flask import jsonify

class AppError(Exception):
    def __init__(self, message: str, code: int = 400, details: Dict[str, Any] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

class GameError(AppError):
    pass

class AuthError(AppError):
    pass

def setup_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(error):
        response = {
            'error': error.message,
            'details': error.details
        }
        return jsonify(response), error.code

    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(500)
    def handle_server_error(error):
        return jsonify({'error': 'Internal server error'}), 500
