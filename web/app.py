import sys
import os
from pathlib import Path
import tensorflow as tf
from datetime import datetime
from prometheus_client import Counter, Histogram
from logging.config import dictConfig
from flask import Flask, render_template, jsonify, request, g
from typing import Optional

# Настройка TensorFlow
tf.get_logger().setLevel('ERROR')
tf.config.set_visible_devices([], 'GPU')

# Добавляем корневую директорию проекта в PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

# Импорты
from core.game import Game, GameState, GameResult
from core.fantasy import FantasyMode
from agents.random import RandomAgent
from agents.rl.dqn import DQNAgent
from agents.rl.a3c import A3CAgent
from agents.rl.ppo import PPOAgent
from agents.base import BaseAgent
from training.training_mode import TrainingSession, TrainingConfig
from utils.config import Config
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

# Инициализация конфигурации
config = Config()

# Метрики Prometheus
REQUESTS = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
RESPONSE_TIME = Histogram('http_response_time_seconds', 'HTTP response time')
GAME_METRICS = Counter('game_metrics_total', 'Game related metrics', ['type'])

# Доступные агенты
AVAILABLE_AGENTS = {
    'random': RandomAgent,
    'dqn': DQNAgent,
    'a3c': A3CAgent,
    'ppo': PPOAgent
}

# Инициализация Flask
app = Flask(__name__)
app.config.update(
    JSON_SORT_KEYS=False,
    PROPAGATE_EXCEPTIONS=True,
    MAX_CONTENT_LENGTH=16 * 1024 * 1024
)

# Глобальные переменные
current_game: Optional[Game] = None
current_training_session: Optional[TrainingSession] = None

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

@app.route('/')
def index():
    """Отображает главную страницу"""
    return render_template('index.html')

@app.route('/training')
def training():
    """Отображает страницу режима тренировки"""
    return render_template('training.html')

@app.route('/api/agents')
def get_available_agents():
    """Возвращает список доступных агентов"""
    return jsonify({
        'agents': [
            {
                'id': agent_id,
                'name': agent_class.__name__,
                'description': agent_class.__doc__
            }
            for agent_id, agent_class in AVAILABLE_AGENTS.items()
        ]
    })

@app.route('/api/new_game', methods=['POST'])
def new_game():
    """Создает новую игру"""
    global current_game
    
    try:
        data = request.get_json()
        opponent_type = data.get('opponent_type', 'random')
        fantasy_mode = FantasyMode.PROGRESSIVE if data.get('progressive_fantasy') else FantasyMode.NORMAL
        
        if opponent_type not in AVAILABLE_AGENTS:
            return jsonify({
                'status': 'error',
                'message': f'Unknown opponent type: {opponent_type}'
            }), 400
            
        # Создаем агента
        agent_class = AVAILABLE_AGENTS[opponent_type]
        opponent = agent_class.load_latest(
            name=opponent_type,
            state_size=config.get('state_size'),
            action_size=config.get('action_size'),
            config=config.get('agent_config')
        )
        
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
            'game_state': current_game.get_state()
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

        success = current_game.make_move(1, card, street)
        if not success:
            return jsonify({
                'status': 'error',
                'message': 'Invalid move'
            }), 400

        if not current_game.is_game_over():
            ai_move = current_game.get_ai_move()
            current_game.make_move(2, *ai_move)

        game_state = current_game.get_state()
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

@app.route('/api/training/distribute', methods=['POST'])
def distribute_cards():
    """Распределяет карты в тренировочном режиме"""
    try:
        if not current_training_session:
            return jsonify({
                'status': 'error',
                'message': 'No active training session'
            }), 400

        data = request.get_json()
        input_cards = data.get('input_cards', [])
        removed_cards = data.get('removed_cards', [])
        
        move_result = current_training_session.make_move()
        
        return jsonify({
            'status': 'ok',
            'move': move_result,
            'statistics': current_training_session.get_statistics()
        })
        
    except Exception as e:
        logger.error(f"Error in training mode: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/training/stats')
def get_training_stats():
    """Получает статистику тренировки"""
    if not current_training_session:
        return jsonify({
            'status': 'error',
            'message': 'No active training session'
        }), 400
        
    return jsonify({
        'status': 'ok',
        'statistics': current_training_session.get_statistics()
    })

@app.route('/api/game/state')
def get_game_state():
    """Получает текущее состояние игры"""
    if not current_game:
        return jsonify({
            'status': 'error',
            'message': 'No active game'
        }), 400
        
    return jsonify({
        'status': 'ok',
        'game_state': current_game.get_state()
    })

@app.route('/api/health')
def health_check():
    """Проверка здоровья приложения"""
    try:
        tf.keras.backend.clear_session()
        
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'game_active': current_game is not None,
            'training_active': current_training_session is not None,
            'tensorflow_status': 'ok',
            'environment': app.env,
            'available_agents': list(AVAILABLE_AGENTS.keys())
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
