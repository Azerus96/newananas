# web/api/routes/game_routes.py
from flask import Blueprint, request, jsonify
from services.game_service import GameService
from web.api.middleware import require_auth, rate_limit
from utils.error_handlers import GameError

game_routes = Blueprint('game', __name__)
game_service = GameService()

@game_routes.route('/new', methods=['POST'])
@require_auth
@rate_limit(100, 60)
def new_game():
    try:
        game = game_service.create_game(request.json)
        return jsonify(game)
    except GameError as e:
        return jsonify({'error': str(e)}), e.code
    except Exception as e:
         # web/api/routes/game_routes.py (продолжение)
        return jsonify({'error': 'Internal server error'}), 500

@game_routes.route('/move', methods=['POST'])
@require_auth
@rate_limit(100, 60)
def make_move():
    try:
        game_id = request.json.get('game_id')
        move_data = request.json.get('move')
        if not game_id or not move_data:
            return jsonify({'error': 'Missing required data'}), 400
            
        result = game_service.make_move(game_id, move_data)
        return jsonify(result)
    except GameError as e:
        return jsonify({'error': str(e)}), e.code
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@game_routes.route('/state/<game_id>', methods=['GET'])
@require_auth
def get_game_state(game_id):
    try:
        state = game_service.get_game_state(game_id)
        return jsonify(state)
    except GameError as e:
        return jsonify({'error': str(e)}), e.code
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@game_routes.route('/fantasy/<game_id>', methods=['POST'])
@require_auth
def handle_fantasy(game_id):
    try:
        fantasy_data = request.json
        result = game_service.process_fantasy(game_id, fantasy_data)
        return jsonify(result)
    except GameError as e:
        return jsonify({'error': str(e)}), e.code
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500
