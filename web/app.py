# web/app.py

from flask import Flask, render_template, jsonify, request, g
from typing import Optional, Dict
import os
import json
from datetime import datetime

from ..core.game import Game, GameState
from ..core.fantasy import FantasyMode
from ..agents.random import RandomAgent
from ..agents.rl.dqn import DQNAgent
from ..agents.rl.a3c import A3CAgent
from ..agents.rl.ppo import PPOAgent
from ..training.training_mode import TrainingSession, TrainingConfig
from ..utils.config import config
from ..utils.logger import get_logger

logger = get_logger(__name__)

app = Flask(__name__)

# Глобальные переменные для хранения состояния
current_game: Optional[Game] = None
current_training_session: Optional[TrainingSession] = None

@app.route('/')
def index():
    """Отображает главную страницу"""
    return render_template('index.html')

@app.route('/training')
def training():
    """Отображает страницу режима тренировки"""
    return render_template('training.html')

@app.route('/api/new_game', methods=['POST'])
def new_game():
    """Создает новую игру"""
    global current_game
    
    try:
        data = request.get_json()
        opponent_type = data.get('opponent_type', 'random')
        
        # Создаем противника в зависимости от выбранного типа
        if opponent_type == 'random':
            opponent = RandomAgent()
        elif opponent_type == 'dqn':
            opponent = DQNAgent.load_latest()
        elif opponent_type == 'a3c':
            opponent = A3CAgent.load_latest()
        elif opponent_type == 'ppo':
            opponent = PPOAgent.load_latest()
        else:
            return jsonify({
                'status': 'error',
                'message': f'Unknown opponent type: {opponent_type}'
            }), 400

        # Создаем новую игру
        current_game = Game(
            player1=None,  # Человек
            player2=opponent,
            fantasy_mode=FantasyMode.PROGRESSIVE if data.get('progressive_fantasy') 
                        else FantasyMode.NORMAL
        )
        
        current_game.start()
        
        return jsonify({
            'status': 'ok',
            'game_state': _get_game_state()
        })
        
    except Exception as e:
        logger.error(f"Error creating new game: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/make_move', methods=['POST'])
def make_move():
    """Выполняет ход в игре"""
    if current_game is None:
        return jsonify({
            'status': 'error',
            'message': 'No active game'
        }), 400

    try:
        data = request.get_json()
        card = data.get('card')
        street = data.get('street')

        # Выполняем ход игрока
        success = current_game.make_move(1, card, street)
        if not success:
            return jsonify({
                'status': 'error',
                'message': 'Invalid move'
            }), 400

        # Если игра не закончена, делаем ход ИИ
        if not current_game.is_game_over():
            ai_move = current_game.get_ai_move()
            current_game.make_move(2, *ai_move)

        return jsonify({
            'status': 'ok',
            'game_state': _get_game_state()
        })

    except Exception as e:
        logger.error(f"Error making move: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/training/start', methods=['POST'])
def start_training():
    """Начинает новую сессию тренировки"""
    global current_training_session
    
    try:
        data = request.get_json()
        config = TrainingConfig(
            fantasy_mode=data.get('fantasy_mode', False),
            progressive_fantasy=data.get('progressive_fantasy', False),
            time_limit=data.get('time_limit', 30)
        )
        
        current_training_session = TrainingSession(config)
        
        return jsonify({
            'status': 'ok',
            'session_id': current_training_session.id
        })
        
    except Exception as e:
        logger.error(f"Error starting training session: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/training/distribute', methods=['POST'])
def distribute_cards():
    """Обрабатывает запрос на распределение карт в режиме тренировки"""
    if current_training_session is None:
        return jsonify({
            'status': 'error',
            'message': 'No active training session'
        }), 400

    try:
        data = request.get_json()
        
        # Получаем ход от ИИ
        move_result = current_training_session.make_move(
            input_cards=data.get('input_cards', []),
            removed_cards=data.get('removed_cards', [])
        )
        
        return jsonify({
            'status': 'ok',
            'move': move_result['move'],
            'statistics': move_result['statistics']
        })
        
    except Exception as e:
        logger.error(f"Error in training distribution: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/training/stats', methods=['GET'])
def get_training_stats():
    """Возвращает статистику текущей сессии тренировки"""
    if current_training_session is None:
        return jsonify({
            'status': 'error',
            'message': 'No active training session'
        }), 400

    try:
        stats = current_training_session.get_statistics()
        return jsonify({
            'status': 'ok',
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting training stats: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def _get_game_state():
    """Формирует словарь с текущим состоянием игры"""
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
        'is_game_over': current_game.is_game_over(),
        'fantasy_mode': current_game.fantasy_mode.value
    # web/app.py (продолжение)

    if state['is_game_over']:
        result = current_game.get_result()
        state['result'] = {
            'winner': result.winner,
            'player1_score': result.player1_score,
            'player2_score': result.player2_score,
            'player1_royalties': result.player1_royalties,
            'player2_royalties': result.player2_royalties,
            'fantasy_achieved': result.fantasy_achieved if hasattr(result, 'fantasy_achieved') else False
        }

    return state

@app.route('/api/training/reset', methods=['POST'])
def reset_training():
    """Сбрасывает текущую сессию тренировки"""
    global current_training_session
    
    try:
        if current_training_session:
            current_training_session.save_progress()
            current_training_session = None
            
        return jsonify({
            'status': 'ok'
        })
        
    except Exception as e:
        logger.error(f"Error resetting training session: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/training/save', methods=['POST'])
def save_training_progress():
    """Сохраняет прогресс тренировки"""
    if current_training_session is None:
        return jsonify({
            'status': 'error',
            'message': 'No active training session'
        }), 400

    try:
        save_path = current_training_session.save_progress()
        return jsonify({
            'status': 'ok',
            'save_path': save_path
        })
        
    except Exception as e:
        logger.error(f"Error saving training progress: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/training/load', methods=['POST'])
def load_training_progress():
    """Загружает сохраненный прогресс тренировки"""
    global current_training_session
    
    try:
        data = request.get_json()
        save_path = data.get('save_path')
        
        if not save_path or not os.path.exists(save_path):
            return jsonify({
                'status': 'error',
                'message': 'Invalid save path'
            }), 400
            
        current_training_session = TrainingSession.load_from_save(save_path)
        
        return jsonify({
            'status': 'ok',
            'session_id': current_training_session.id
        })
        
    except Exception as e:
        logger.error(f"Error loading training progress: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/training/update_config', methods=['POST'])
def update_training_config():
    """Обновляет конфигурацию тренировки"""
    if current_training_session is None:
        return jsonify({
            'status': 'error',
            'message': 'No active training session'
        }), 400

    try:
        data = request.get_json()
        current_training_session.update_config(TrainingConfig(**data))
        
        return jsonify({
            'status': 'ok'
        })
        
    except Exception as e:
        logger.error(f"Error updating training config: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.before_request
def before_request():
    """Выполняется перед каждым запросом"""
    g.start_time = datetime.now()

@app.after_request
def after_request(response):
    """Выполняется после каждого запроса"""
    if hasattr(g, 'start_time'):
        elapsed = datetime.now() - g.start_time
        logger.info(f"Request processed in {elapsed.total_seconds():.3f} seconds")
    return response

@app.errorhandler(404)
def not_found_error(error):
    """Обработчик ошибки 404"""
    return jsonify({
        'status': 'error',
        'message': 'Resource not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Обработчик ошибки 500"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500

def main():
    """Точка входа для запуска веб-приложения"""
    port = int(os.environ.get('PORT', 5000))
    debug = config.get('web.debug', False)
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )

if __name__ == '__main__':
    main()
