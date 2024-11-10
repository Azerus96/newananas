# web/api/routes/game_routes.py
from flask import Blueprint, request, jsonify
from services import GameService
from web.api.middleware import require_auth, rate_limit
from web.api.schemas import GameSchema, MoveSchema

game_routes = Blueprint('game', __name__)
game_service = GameService()

@game_routes.route('/new', methods=['POST'])
@require_auth
@rate_limit(100, 60)
def new_game():
    try:
        schema = GameSchema()
        data = schema.load(request.json)
        game = game_service.create_game(data)
        return jsonify(schema.dump(game))
    except Exception as e:
        return jsonify({'error': str(e)}), 400
