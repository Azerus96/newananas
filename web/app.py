from gevent import monkey
monkey.patch_all()

import sys
import os
from pathlib import Path
import tensorflow as tf
from datetime import datetime
from prometheus_client import Counter, Histogram
from logging.config import dictConfig
from flask import Flask, render_template, jsonify, request, g, session, redirect, url_for, make_response, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from typing import Optional, Dict, Any, List
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import json
from time import time

# Настройка TensorFlow
tf.get_logger().setLevel('ERROR')
tf.config.set_visible_devices([], 'GPU')

# Добавляем корневую директорию проекта в PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

# Импорты из проекта
from core.game import Game, GameState, GameResult, Card, Street
from core.fantasy import FantasyMode, FantasyManager
from core.board import Board
from agents.random import RandomAgent
from agents.rl.dqn import DQNAgent
from agents.rl.a3c import A3CAgent
from agents.rl.ppo import PPOAgent
from agents.base import BaseAgent
from training.training_mode import TrainingSession, TrainingConfig
from utils.config import Config
from utils.logger import get_logger
from utils.app_state import AppState
from analytics.analytics_manager import AnalyticsManager

# Инициализация конфигурации
config = Config()

# Создаем необходимые директории
REQUIRED_DIRS = [
    config.get('paths.models'),
    config.get('paths.logs'),
    config.get('paths.replays'),
    config.get('paths.checkpoints')
]

for dir_path in REQUIRED_DIRS:
    Path(dir_path).mkdir(parents=True, exist_ok=True)

# Настройка логирования
log_config = config.get('logging')
dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': log_config.get('format')
        },
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
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
            'formatter': 'detailed'
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
WEBSOCKET_CONNECTIONS = Counter('websocket_connections_total', 'WebSocket connections')
WEBSOCKET_ERRORS = Counter('websocket_errors_total', 'WebSocket errors', ['type'])
AI_METRICS = Counter('ai_metrics_total', 'AI related metrics', ['agent', 'action'])
CONNECTION_LATENCY = Histogram('connection_latency_seconds', 'Connection latency')

# Доступные агенты
AVAILABLE_AGENTS = {
    'random': {'class': RandomAgent, 'display_name': 'Random'},
    'dqn': {'class': DQNAgent, 'display_name': 'DQN'},
    'a3c': {'class': A3CAgent, 'display_name': 'A3C'},
    'ppo': {'class': PPOAgent, 'display_name': 'PPO'}
}

# Настройки по умолчанию
DEFAULT_PREFERENCES = {
    'theme': 'light',
    'animation_speed': 'normal',
    'sound_enabled': True,
    'language': 'en',
    'notifications_enabled': True,
    'auto_save': True,
    'keyboard_shortcuts': True,
    'accessibility_mode': False
}

# Инициализация Flask и SocketIO
app = Flask(__name__,
    static_folder=config.get('web.static_folder'),
    template_folder=config.get('web.template_folder')
)

# Расширенная конфигурация приложения
app.config.update(
    JSON_SORT_KEYS=False,
    PROPAGATE_EXCEPTIONS=True,
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
    DEBUG=config.get('web.debug', False),
    SECRET_KEY=config.get('security.secret_key', os.urandom(24)),
    PERMANENT_SESSION_LIFETIME=config.get('web.session_lifetime', 3600),
    SOCKETIO_PING_TIMEOUT=60,
    SOCKETIO_PING_INTERVAL=25,
    SOCKETIO_ASYNC_MODE='gevent',
    SOCKETIO_LOGGER=True,
    SOCKETIO_ENGINEIO_LOGGER=True
)

# Инициализация SocketIO
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    async_mode='gevent',
    ping_timeout=60,
    ping_interval=25,
    logger=True,
    engineio_logger=True,
    async_handlers=True,
    reconnection=True,
    reconnection_attempts=5,
    reconnection_delay=1000,
    reconnection_delay_max=5000
)

# Инициализация глобальных объектов
app_state = AppState()
analytics_manager = AnalyticsManager()
executor = ThreadPoolExecutor(max_workers=4)

# Состояние подключений
connections = {
    'active': 0,
    'total': 0,
    'errors': 0,
    'last_error': None
}

################
#### Функции для работы с preferences ####
################

def get_client_preferences() -> dict:
    """Получает настройки клиента из сессии"""
    if 'preferences' not in session:
        session['preferences'] = DEFAULT_PREFERENCES.copy()
    return session['preferences']

def update_client_preferences(updates: dict) -> dict:
    """Обновляет настройки клиента"""
    preferences = get_client_preferences()
    preferences.update(updates)
    session['preferences'] = preferences
    return preferences

def save_preferences_to_cookies(preferences: dict, response):
    """Сохраняет настройки в cookies"""
    for key, value in preferences.items():
        response.set_cookie(
            f'pref_{key}',
            str(value),
            max_age=31536000,  # 1 год
            httponly=True,
            secure=True,
            samesite='Lax'
        )

def load_preferences_from_cookies() -> dict:
    """Загружает настройки из cookies"""
    preferences = DEFAULT_PREFERENCES.copy()
    for key in DEFAULT_PREFERENCES.keys():
        cookie_value = request.cookies.get(f'pref_{key}')
        if cookie_value is not None:
            if isinstance(DEFAULT_PREFERENCES[key], bool):
                preferences[key] = cookie_value.lower() == 'true'
            else:
                preferences[key] = type(DEFAULT_PREFERENCES[key])(cookie_value)
    return preferences

################
#### Вспомогательные функции ####
################

def create_agent(agent_type: str, position: int, think_time: int) -> BaseAgent:
    """Создает агента нужного типа с правильными настройками"""
    if agent_type not in AVAILABLE_AGENTS:
        raise ValueError(f"Unknown agent type: {agent_type}")
    agent_info = AVAILABLE_AGENTS[agent_type]
    agent_class = agent_info['class']
    display_name = agent_info['display_name']
    return agent_class(name=f"{display_name}_{position}", think_time=think_time)

def get_agent_display_name(agent: BaseAgent) -> str:
    """Возвращает отображаемое имя агента"""
    for agent_type, info in AVAILABLE_AGENTS.items():
        if isinstance(agent, info['class']):
            return info['display_name']
    return "Unknown"

async def process_ai_move(game: Game):
    """Асинхронная обработка хода AI"""
    try:
        emit_game_update(game, 'ai_thinking')
        start_time = time()
        ai_move = await asyncio.get_event_loop().run_in_executor(executor, game.get_ai_move)
        think_time = time() - start_time
        logger.debug(f"AI think time: {think_time:.2f}s")
        success = game.make_move(game.current_player, *ai_move)
        if success:
            AI_METRICS.labels(agent=get_agent_display_name(game.current_agent), action='move_success').inc()
            if ai_move.is_foul:
                game.state.fouls += 1
            if ai_move.is_scoop:
                game.state.scoops += 1
            game.state.totalMoves += 1
            analytics_manager.track_ai_move(game.current_agent, ai_move, think_time)
        else:
            AI_METRICS.labels(agent=get_agent_display_name(game.current_agent), action='move_failed').inc()
            logger.warning(f"AI move failed for agent {game.current_agent.name}")
        emit_game_update(game)
        return success
    except Exception as e:
        logger.error(f"Error processing AI move: {e}", exc_info=True)
        WEBSOCKET_ERRORS.labels(type='ai_move_error').inc()
        return False

async def process_ai_moves(game: Game):
    """Обработка всех ходов AI"""
    while game.current_player != 0 and not game.is_game_over():
        success = await process_ai_move(game)
        if not success:
            break

def emit_game_update(game: Game, event_type: str = 'game_update'):
    """Отправляет обновление состояния игры"""
    socketio.emit(
        event_type,
        {
            'game_state': game.get_state(),
            'current_player': game.current_player,
            'is_game_over': game.is_game_over(),
            'timestamp': datetime.now().isoformat()
        },
        room=str(game.id)
    )

def check_game_over(game: Game):
    """Проверяет окончание игры и отправляет результаты"""
    if game.is_game_over():
        result = game.get_result()
        analytics_manager.track_game_end(game, result)
        socketio.emit('game_over', {
            'result': result.to_dict(),
            'statistics': analytics_manager.get_game_statistics(game)
        }, room=str(game.id))
        GAME_METRICS.labels(type='game_completed').inc()

def check_connection_health():
    """Проверяет состояние подключения"""
    return {
        'status': 'healthy' if connections['errors'] == 0 else 'degraded',
        'active_connections': connections['active'],
        'total_connections': connections['total'],
        'error_rate': connections['errors'] / max(connections['total'], 1),
        'last_error': connections['last_error']
    }

def is_mobile():
    """Проверяет, является ли клиент мобильным устройством"""
    user_agent = request.headers.get('User-Agent', '').lower()
    return any(device in user_agent for device in ['mobile', 'android', 'iphone', 'ipad', 'ipod'])

################
#### Декораторы ####
################

def handle_errors(f):
    """Декоратор для обработки ошибок"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    return decorated_function

def require_game(f):
    """Декоратор для проверки наличия активной игры"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        game_id = session.get('current_game_id')
        game = app_state.get_game(game_id) if game_id else None
        
        if not game:
            return jsonify({'error': 'No active game'}), 404
            
        return f(game, *args, **kwargs)
    return decorated_function

##################
#### Middleware ####
##################

@app.before_request
def initialize_session():
    """Инициализация сессии перед каждым запросом"""
    if 'preferences' not in session:
        session['preferences'] = load_preferences_from_cookies()
    g.language = session['preferences'].get('language', 'en')

@app.after_request
def after_request(response):
    """Обработка после каждого запроса"""
    if 'preferences' in session:
        save_preferences_to_cookies(session['preferences'], response)
    return response

###############
#### Роуты ####
###############

@app.route('/')
def index():
    """Главная страница"""
    return render_template(
        'index.html',
        preferences=get_client_preferences(),
        agents=AVAILABLE_AGENTS
    )

@app.route('/api/new_game', methods=['POST'])
@handle_errors
def new_game():
    """Создает новую игру"""
    data = request.get_json()
    game_id = str(uuid.uuid4())
    try:
        game_config = {
            'players': data.get('players', 2),
            'fantasy_mode': (FantasyMode.PROGRESSIVE if data.get('progressive_fantasy') else FantasyMode.NORMAL),
            'think_time': data.get('aiThinkTime', 30),
            'agents': [],
            'is_mobile': is_mobile()
        }

        # Создаем AI агентов
        for i in range(game_config['players'] - 1):
            agent_type = data.get(f'agent_{i}', 'random')
            agent = create_agent(agent_type=agent_type, position=i+1, think_time=game_config['think_time'])
            game_config['agents'].append(agent)

        game = app_state.create_game(game_id, game_config)
        game.start()

        session['current_game_id'] = game_id
        emit_game_update(game, 'game_started')

        GAME_METRICS.labels(type='new_game').inc()
        logger.info(f"New game created: {game_id}")

        return jsonify({
            'status': 'ok',
            'game_id': game_id,
            'game_state': game.get_state(),
            'connection_status': check_connection_health()
        })
    except Exception as e:
        logger.error(f"Error creating new game: {e}", exc_info=True)
        return jsonify({'error': 'Failed to create game', 'message': str(e)}), 500

@app.route('/api/game/move', methods=['POST'])
@require_game
@handle_errors
def make_move(game):
    """Выполняет ход игрока"""
    data = request.get_json()
    try:
        success = game.make_move(
            card=Card.from_dict(data.get('card')),
            position=data.get('position')
        )

        if success:
            if data.get('is_foul'):
                game.state.fouls += 1
            if data.get('is_scoop'):
                game.state.scoops += 1
            game.state.totalMoves += 1

            emit_game_update(game)
            logger.debug(f"Move made: {data.get('card')} to position {data.get('position')}")
            
            if not game.is_game_over():
                asyncio.create_task(process_ai_moves(game))
            else:
                check_game_over(game)
                
            return jsonify({
                'status': 'ok',
                'game_state': game.get_state(),
                'connection_status': check_connection_health()
            })

        return jsonify({'error': 'Invalid move'}), 400
    except Exception as e:
        logger.error(f"Error making move: {e}", exc_info=True)
        return jsonify({'error': 'Failed to make move', 'message': str(e)}), 500

@app.route('/api/game/state', methods=['GET'])
@require_game
@handle_errors
def get_game_state(game):
    """Получает текущее состояние игры"""
    return jsonify({
        'status': 'ok',
        'game_state': game.get_state(),
        'connection_status': check_connection_health()
    })

@app.route('/api/preferences', methods=['GET', 'POST'])
def handle_preferences():
    """Обработка настроек пользователя"""
    if request.method == 'POST':
        try:
            updates = request.get_json()
            valid_updates = {
                k: v for k, v in updates.items() 
                if k in DEFAULT_PREFERENCES
            }
            preferences = update_client_preferences(valid_updates)
            return jsonify({
                'status': 'ok',
                'preferences': preferences
            })
        except Exception as e:
            logger.error(f"Error updating preferences: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 400
    
    # GET запрос
    return jsonify({
        'status': 'ok',
        'preferences': get_client_preferences()
    })

@app.route('/api/preferences/reset', methods=['POST'])
def reset_preferences():
    """Сброс настроек к значениям по умолчанию"""
    session['preferences'] = DEFAULT_PREFERENCES.copy()
    response = jsonify({
        'status': 'ok',
        'preferences': DEFAULT_PREFERENCES
    })
    # Очищаем все cookies с настройками
    for key in DEFAULT_PREFERENCES.keys():
        response.delete_cookie(f'pref_{key}')
    return response

@app.route('/api/game/save', methods=['POST'])
@require_game
@handle_errors
def save_game(game):
    """Сохраняет текущую игру"""
    try:
        game_state = game.get_state()
        session['saved_game'] = game_state
        return jsonify({
            'status': 'ok',
            'message': 'Game saved successfully'
        })
    except Exception as e:
        logger.error(f"Error saving game: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to save game'
        }), 500

@app.route('/api/game/load', methods=['POST'])
@handle_errors
def load_game():
    """Загружает сохраненную игру"""
    saved_game = session.get('saved_game')
    if not saved_game:
        return jsonify({
            'status': 'error',
            'message': 'No saved game found'
        }), 404

    try:
        game_id = str(uuid.uuid4())
        game = app_state.create_game(game_id, saved_game)
        session['current_game_id'] = game_id
        emit_game_update(game, 'game_loaded')
        
        return jsonify({
            'status': 'ok',
            'game_id': game_id,
            'game_state': game.get_state()
        })
    except Exception as e:
        logger.error(f"Error loading game: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to load game'
        }), 500

@app.route('/api/statistics', methods=['GET'])
@handle_errors
def get_statistics():
    """Получение статистики"""
    return jsonify({
        'status': 'ok',
        'statistics': analytics_manager.get_full_statistics(),
        'server_stats': {
            'connections': connections,
            'active_games': len(app_state.get_active_games()),
            'uptime': time() - app.start_time if hasattr(app, 'start_time') else 0
        }
    })

##################
#### WebSocket события ####
##################

@socketio.on('connect')
def handle_connect():
    """Обработка подключения клиента"""
    connections['active'] += 1
    connections['total'] += 1
    WEBSOCKET_CONNECTIONS.inc()
    logger.info(f"Client connected. Active connections: {connections['active']}")

@socketio.on('disconnect')
def handle_disconnect():
    """Обработка отключения клиента"""
    connections['active'] -= 1
    logger.info(f"Client disconnected. Active connections: {connections['active']}")

@socketio.on('join_game')
def handle_join_game(game_id):
    """Обработка присоединения к игре"""
    join_room(str(game_id))
    logger.debug(f"Client joined game room: {game_id}")

@socketio.on('leave_game')
def handle_leave_game(game_id):
    """Обработка выхода из игры"""
    leave_room(str(game_id))
    logger.debug(f"Client left game room: {game_id}")

@socketio.on_error()
def handle_error(e):
    """Обработка ошибок WebSocket"""
    connections['errors'] += 1
    connections['last_error'] = str(e)
    WEBSOCKET_ERRORS.labels(type='general').inc()
    logger.error(f"WebSocket error: {e}")

##################
#### Обработка ошибок ####
##################

@app.errorhandler(404)
def not_found_error(error):
    """Обработка ошибки 404"""
    logger.warning(f"404 error: {request.url}")
    if request.is_json:
        return jsonify({'error': 'Not found'}), 404
    return render_template(
        'error.html',
        error="Page not found",
        preferences=get_client_preferences()
    ), 404

@app.errorhandler(500)
def internal_error(error):
    """Обработка ошибки 500"""
    logger.error(f"500 error: {error}", exc_info=True)
    if request.is_json:
        return jsonify({'error': 'Internal server error'}), 500
    return render_template(
        'error.html',
        error="Internal server error",
        preferences=get_client_preferences()
    ), 500

if __name__ == '__main__':
    try:
        app.start_time = time()
        port = int(os.environ.get('PORT', config.get('web.port', 5000)))
        debug = config.get('web.debug', False)

        logger.info(f"Starting server on port {port} (debug={debug})")
        logger.info(f"Available agents: {list(AVAILABLE_AGENTS.keys())}")
        logger.info(f"Application version: {config.get('app.version', 'unknown')}")

        socketio.run(
            app,
            host='0.0.0.0',
            port=port,
            debug=debug,
            use_reloader=debug,
            log_output=True,
            cors_allowed_origins=config.get('web.cors_origins', "*")
        )
    except Exception as e:
        logger.critical(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)
