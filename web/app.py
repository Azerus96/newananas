import sys
import os
from pathlib import Path
import tensorflow as tf

# Настройка TensorFlow
tf.get_logger().setLevel('ERROR')
tf.config.set_visible_devices([], 'GPU')

# Добавляем корневую директорию проекта в PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from flask import Flask, render_template, jsonify, request, g
from typing import Optional, Dict
import json
from datetime import datetime
from prometheus_client import Counter, Histogram
from logging.config import dictConfig

# Абсолютные импорты
from core.game import Game, GameState, GameResult
from core.fantasy import FantasyMode
from agents.random import RandomAgent
from agents.rl.dqn import DQNAgent
from agents.rl.a3c import A3CAgent
from agents.rl.ppo import PPOAgent
from agents.rl.fantasy_agent import FantasyAgent
from training.training_mode import TrainingSession, TrainingConfig
from analytics.statistics import StatisticsManager
from utils.config import config
from utils.logger import get_logger

# Настройка логирования
dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }
    },
    'handlers': {
        'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(ROOT_DIR, 'logs', 'app.log'),
            'maxBytes': 1024 * 1024,
            'backupCount': 10,
            'formatter': 'default'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi', 'file']
    }
})

logger = get_logger(__name__)

# Метрики Prometheus
REQUESTS = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
RESPONSE_TIME = Histogram('http_response_time_seconds', 'HTTP response time')
GAME_METRICS = Counter('game_metrics_total', 'Game related metrics', ['type'])

# Инициализация Flask с правильными настройками
app = Flask(__name__)
app.config.update(
    JSON_SORT_KEYS=False,
    PROPAGATE_EXCEPTIONS=True,
    MAX_CONTENT_LENGTH=16 * 1024 * 1024  # 16MB max-limit
)

# Глобальные переменные для хранения состояния
current_game: Optional[Game] = None
current_training_session: Optional[TrainingSession] = None
statistics_manager = StatisticsManager()

# Middleware для логирования и метрик
@app.before_request
def before_request():
    """Выполняется перед каждым запросом"""
    g.start_time = datetime.now()
    REQUESTS.labels(method=request.method, endpoint=request.endpoint).inc()
    app.logger.info(f'Request: {request.method} {request.url}')

@app.after_request
def after_request(response):
    """Выполняется после каждого запроса"""
    if hasattr(g, 'start_time'):
        elapsed = datetime.now() - g.start_time
        RESPONSE_TIME.observe(elapsed.total_seconds())
        app.logger.info(
            f'Response: {response.status} - {elapsed.total_seconds():.3f}s'
        )
    return response

# Обработчики ошибок
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({
        'status': 'error',
        'message': 'Not Found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'Server Error: {error}')
    return jsonify({
        'status': 'error',
        'message': 'Internal Server Error'
    }), 500

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
        fantasy_mode = FantasyMode.PROGRESSIVE if data.get('progressive_fantasy') else FantasyMode.NORMAL
        
        # Создаем противника
        opponent = create_opponent(opponent_type)
        if not opponent:
            return jsonify({
                'status': 'error',
                'message': f'Unknown opponent type: {opponent_type}'
            }), 400

        # Создаем новую игру
        current_game = Game(
            player1=None,  # Человек
            player2=opponent,
            fantasy_mode=fantasy_mode
        )
        
        current_game.start()
        GAME_METRICS.labels(type='new_game').inc()
        
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

def create_opponent(opponent_type: str) -> Optional[BaseAgent]:
    """Создает противника заданного типа"""
    try:
        if opponent_type == 'random':
            return RandomAgent()
        elif opponent_type == 'dqn':
            return DQNAgent.load_latest()
        elif opponent_type == 'a3c':
            return A3CAgent.load_latest()
        elif opponent_type == 'ppo':
            return PPOAgent.load_latest()
        elif opponent_type == 'fantasy':
            return FantasyAgent.load_latest()
        return None
    except Exception as e:
        logger.error(f"Error creating opponent: {e}")
        return None

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

        game_state = _get_game_state()
        
        # Обновляем статистику
        statistics_manager.update_game_stats(game_state)
        GAME_METRICS.labels(type='move').inc()

        return jsonify({
            'status': 'ok',
            'game_state': game_state
        })

    except Exception as e:
        logger.error(f"Error making move: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/game/statistics')
def get_game_statistics():
    """Возвращает текущую статистику игры"""
    if current_game is None:
        return jsonify({
            'status': 'error',
            'message': 'No active game'
        }), 400

    try:
        statistics = statistics_manager.get_game_statistics()
        return jsonify({
            'status': 'ok',
            'statistics': statistics
        })
    except Exception as e:
        logger.error(f"Error getting game statistics: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/game/fantasy_status')
def get_fantasy_status():
    """Возвращает текущий статус фантазии"""
    if current_game is None:
        return jsonify({
            'status': 'error',
            'message': 'No active game'
        }), 400

    try:
        return jsonify({
            'status': 'ok',
            'fantasy_status': current_game.get_fantasy_status(),
            'fantasy_statistics': current_game.get_fantasy_statistics()
        })
    except Exception as e:
        logger.error(f"Error getting fantasy status: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/game/recommendations')
def get_move_recommendations():
    """Возвращает рекомендации по ходам"""
    if current_game is None:
        return jsonify({
            'status': 'error',
            'message': 'No active game'
        }), 400

    try:
        recommendations = current_game.get_move_recommendations()
        return jsonify({
            'status': 'ok',
            'recommendations': recommendations
        })
    except Exception as e:
        logger.error(f"Error getting move recommendations: {e}")
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
        GAME_METRICS.labels(type='training_start').inc()
        
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

@app.route('/api/health')
def health_check():
    """Расширенная проверка здоровья приложения"""
    try:
        # Проверяем TensorFlow
        tf.keras.backend.clear_session()
        
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'game_active': current_game is not None,
            'training_active': current_training_session is not None,
            'tensorflow_status': 'ok',
            'environment': app.env,
            'port': os.environ.get('PORT', 10000)
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
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
        'fantasy_mode': current_game.fantasy_mode.value,
        'removed_cards': [card.to_dict() for card in current_game.get_removed_cards()]
    }

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

# Точка входа для gunicorn
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
