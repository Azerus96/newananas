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

# Инициализация конфигурации
config = Config()

# Создаем необходимые директории из конфигурации
REQUIRED_DIRS = [
    config.get('paths.models'),
    config.get('paths.logs'),
    config.get('paths.replays'),
    config.get('paths.checkpoints')
]

for dir_path in REQUIRED_DIRS:
    Path(dir_path).mkdir(parents=True, exist_ok=True)

# Настройка логирования из конфигурации
log_config = config.get('logging')
dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': log_config.get('format')
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
            'filename': os.path.join(config.get('paths.logs'), log_config.get('file')),
            'maxBytes': 1024 * 1024,
            'backupCount': 10,
            'formatter': 'default'
        }
    },
    'root': {
        'level': log_config.get('level'),
        'handlers': ['wsgi', 'file']
    }
})

logger = get_logger(__name__)

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
app = Flask(__name__,
    static_folder=config.get('web.static_folder'),
    template_folder=config.get('web.template_folder')
)
app.config.update(
    JSON_SORT_KEYS=False,
    PROPAGATE_EXCEPTIONS=True,
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
    DEBUG=config.get('web.debug', False)
)

# Глобальные переменные
current_game: Optional[Game] = None
current_training_session: Optional[TrainingSession] = None

# ... (предыдущая часть кода) ...

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
    try:
        agents_list = [
            {
                'id': agent_id,
                'name': agent_class.__name__,
                'description': agent_class.__doc__
            }
            for agent_id, agent_class in AVAILABLE_AGENTS.items()
        ]
        logger.info(f"Returning available agents: {agents_list}")
        return jsonify({'agents': agents_list})
    except Exception as e:
        logger.error(f"Error getting agents list: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/new_game', methods=['POST'])
def new_game():
    """Создает новую игру"""
    global current_game
    
    try:
        data = request.get_json()
        logger.info(f"Creating new game with data: {data}")
        
        opponent_type = data.get('opponent_type', 'random')
        fantasy_mode = FantasyMode.PROGRESSIVE if data.get('progressive_fantasy') else FantasyMode.NORMAL
        
        if opponent_type not in AVAILABLE_AGENTS:
            return jsonify({
                'status': 'error',
                'message': f'Unknown opponent type: {opponent_type}'
            }), 400
            
        # Создаем агента в зависимости от типа
        if opponent_type == 'random':
            opponent = RandomAgent.load_latest(name=f"{opponent_type}_opponent")
        else:
            # Получаем конфигурацию для конкретного типа агента
            agent_config = config.get_agent_config(opponent_type)
            state_size = config.get('state.size')
            action_size = config.get('action.size')
            
            opponent = AVAILABLE_AGENTS[opponent_type].load_latest(
                name=f"{opponent_type}_opponent",
                state_size=state_size,
                action_size=action_size,
                config=agent_config
            )
        
        logger.info(f"Created opponent agent: {opponent}")
        
        # Создаем новую игру с настройками из конфигурации
        game_config = {
            'fantasy_mode': fantasy_mode,
            'think_time': config.get('game.think_time', 1000),
            'save_replays': config.get('game.save_replays', False)
        }
        
        current_game = Game(
            player1=None,  # Человек
            player2=opponent,
            **game_config
        )
        
        current_game.start()
        GAME_METRICS.labels(type='new_game').inc()
        
        game_state = current_game.get_state()
        logger.info(f"Game started with state: {game_state}")
        
        return jsonify({
            'status': 'ok',
            'game_state': game_state
        })
        
    except Exception as e:
        logger.error(f"Error creating new game: {e}", exc_info=True)
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
        logger.info(f"Making move with data: {data}")
        
        card_data = data.get('card')
        street = data.get('street')
        
        # Создаем объект карты из данных
        from core.card import Card
        card = Card(rank=card_data['rank'], suit=card_data['suit'])
        
        success = current_game.make_move(1, card, street)
        if not success:
            return jsonify({
                'status': 'error',
                'message': 'Invalid move'
            }), 400

        # Ход AI
        if not current_game.is_game_over():
            ai_move = current_game.get_ai_move()
            current_game.make_move(2, *ai_move)
            logger.info(f"AI made move: {ai_move}")

        game_state = current_game.get_state()
        GAME_METRICS.labels(type='move').inc()
        
        logger.info(f"Updated game state: {game_state}")

        return jsonify({
            'status': 'ok',
            'game_state': game_state
        })

    except Exception as e:
        logger.error(f"Error making move: {e}", exc_info=True)
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
        training_config = TrainingConfig(
            fantasy_mode=data.get('fantasy_mode', config.get('game.fantasy_mode')),
            progressive_fantasy=data.get('progressive_fantasy', config.get('game.progressive_fantasy')),
            time_limit=data.get('time_limit', config.get('game.think_time') / 1000)  # конвертируем в секунды
        )
        
        current_training_session = TrainingSession(training_config)
        GAME_METRICS.labels(type='training_start').inc()
        
        return jsonify({
            'status': 'ok',
            'session_id': current_training_session.id
        })
        
    except Exception as e:
        logger.error(f"Error starting training session: {e}", exc_info=True)
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
        logger.info(f"Distributing cards with data: {data}")
        
        input_cards = data.get('input_cards', [])
        removed_cards = data.get('removed_cards', [])
        
        # Преобразуем данные карт в объекты
        from core.card import Card
        input_cards = [Card(rank=c['rank'], suit=c['suit']) for c in input_cards]
        removed_cards = [Card(rank=c['rank'], suit=c['suit']) for c in removed_cards]
        
        move_result = current_training_session.make_move(
            input_cards=input_cards,
            removed_cards=removed_cards
        )
        
        logger.info(f"Move result: {move_result}")
        
        return jsonify({
            'status': 'ok',
            'move': move_result,
            'statistics': current_training_session.get_statistics()
        })
        
    except Exception as e:
        logger.error(f"Error in training mode: {e}", exc_info=True)
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
        
    try:
        stats = current_training_session.get_statistics()
        logger.info(f"Retrieved training stats: {stats}")
        return jsonify({
            'status': 'ok',
            'statistics': stats
        })
    except Exception as e:
        logger.error(f"Error getting training stats: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/game/state')
def get_game_state():
    """Получает текущее состояние игры"""
    if not current_game:
        return jsonify({
            'status': 'error',
            'message': 'No active game'
        }), 400
        
    try:
        game_state = current_game.get_state()
        logger.info(f"Retrieved game state: {game_state}")
        return jsonify({
            'status': 'ok',
            'game_state': game_state
        })
    except Exception as e:
        logger.error(f"Error getting game state: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/health')
def health_check():
    """Проверка здоровья приложения"""
    try:
        tf.keras.backend.clear_session()
        
        status = {
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'game_active': current_game is not None,
            'training_active': current_training_session is not None,
            'tensorflow_status': 'ok',
            'environment': app.env,
            'available_agents': list(AVAILABLE_AGENTS.keys()),
            'config_loaded': config.validate(),
            'required_dirs': {
                dir_path: os.path.exists(dir_path)
                for dir_path in REQUIRED_DIRS
            }
        }
        
        logger.info(f"Health check: {status}")
        return jsonify(status)
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.errorhandler(404)
def not_found_error(error):
    logger.warning(f"404 error: {request.url}")
    return jsonify({
        'status': 'error',
        'message': 'Resource not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {error}", exc_info=True)
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500

if __name__ == '__main__':
    try:
        # Проверяем конфигурацию
        if not config.validate():
            raise ValueError("Invalid configuration")
            
        # Проверяем наличие всех необходимых директорий
        for dir_path in REQUIRED_DIRS:
            if not os.path.exists(dir_path):
                raise ValueError(f"Required directory not found: {dir_path}")
        
        port = config.get('web.port', 5000)
        host = config.get('web.host', '0.0.0.0')
        debug = config.get('web.debug', False)
        
        logger.info(f"Starting server on {host}:{port} (debug={debug})")
        app.run(host=host, port=port, debug=debug)
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)
