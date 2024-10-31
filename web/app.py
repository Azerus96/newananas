from flask import Flask, render_template, request, jsonify
from typing import Optional

from ..core.game import Game
from ..agents.human import HumanAgent
from ..agents.random import RandomAgent
from ..agents.rl.dqn import DQNAgent
from ..utils.config import Config

app = Flask(__name__)
config = Config()

# Глобальное состояние игры
current_game: Optional[Game] = None
available_agents = {
    'random': RandomAgent,
    'dqn': DQNAgent
}

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/api/new_game', methods=['POST'])
def new_game():
    """Создает новую игру"""
    data = request.get_json()
    
    # Создаем агентов
    player_type = data.get('player_type', 'human')
    opponent_type = data.get('opponent_type', 'random')
    
    if player_type == 'human':
        player = HumanAgent('Player')
    else:
        player = available_agents[player_type]('Player')
        
    opponent = available_agents[opponent_type]('Opponent')
    
    # Создаем игру
    global current_game
    current_game = Game(player, opponent)
    current_game.start()
    
    return jsonify({
        'status': 'ok',
        'game_state': _get_game_state()
    })

@app.route('/api/make_move', methods=['POST'])
def make_move():
    """Выполняет ход в игре"""
    if current_game is None:
        return jsonify({
            'status': 'error',
            'message': 'No active game'
        }), 400
        
    data = request.get_json()
    card = data.get('card')
    street = data.get('street')
    
    try:
        # Выполняем ход игрока
        success = current_game.make_move(1, card, street)
        if not success:
            return jsonify({
                'status': 'error',
                'message': 'Invalid move'
            }), 400
            
        # Если игра не закончена, делаем ход противника
        if not current_game.is_game_over():
            current_game.make_move(2, *current_game.get_opponent_move())
            
        return jsonify({
            'status': 'ok',
            'game_state': _get_game_state()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/game_state')
def get_game_state():
    """Возвращает текущее состояние игры"""
    if current_game is None:
        return jsonify({
            'status': 'error',
            'message': 'No active game'
        }), 400
        
    return jsonify({
        'status': 'ok',
        'game_state': _get_game_state()
    })

def _get_game_state():
    """Формирует словарь с состоянием игры"""
    if current_game is None:
        return None
        
    state = {
        'player_board': {
            'front': [card.to_dict() for card in current_game.player1_board.front.cards],
            'middle': [card.to_dict() for card in current_game.player1_board.middle.cards],
            'back': [card.to_dict() for card in current_game.player1_board.back.cards]
        },
        'opponent_board': {
            'front': [card.to_dict() for card in current_game.player2_board.front.cards],
            'middle': [card.to_dict() for card in current_game.player2_board.middle.cards],
            'back': [card.to_dict() for card in current_game.player2_board.back.cards]
        },
        'player_cards': [card.to_dict() for card in current_game.player1_cards],
        'current_player': current_game.current_player,
        'is_game_over': current_game.is_game_over()
    }
    
    if state['is_game_over']:
        result = current_game.get_result()
        state['result'] = {
            'winner': result.winner,
            'player1_score': result.player1_score,
            'player2_score': result.player2_score,
            'player1_royalties': result.player1_royalties,
            'player2_royalties': result.player2_royalties
        }
        
    return state

if __name__ == '__main__':
    app.run(debug=config.get('web.debug', False))
