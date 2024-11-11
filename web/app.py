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

# Инициализация SocketIO с расширенными настройками
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

# Вспомогательные функции для работы с агентами
def create_agent(agent_type: str, position: int, think_time: int) -> BaseAgent:
    """Создает агента нужного типа с правильными настройками"""
    if agent_type not in AVAILABLE_AGENTS:
        raise ValueError(f"Unknown agent type: {agent_type}")
        
    agent_info = AVAILABLE_AGENTS[agent_type]
    agent_class = agent_info['class']
    display_name = agent_info['display_name']
    
    return agent_class(
        name=f"{display_name}_{position}",
        think_time=think_time
    )

def get_agent_display_name(agent: BaseAgent) -> str:
    """Возвращает отображаемое имя агента"""
    for agent_type, info in AVAILABLE_AGENTS.items():
        if isinstance(agent, info['class']):
            return info['display_name']
    return "Unknown"

# Глобальные настройки сессии
def init_session():
    """Инициализирует сессию пользователя"""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
        session.permanent = True
        logger.info(f"New session created: {session['user_id']}")
    
    if 'preferences' not in session:
        session['preferences'] = {
            'theme': 'light',
            'animation_speed': 'normal',
            'sound_enabled': True
        }
    
    if 'connection_time' not in session:
        session['connection_time'] = time()

# Декораторы
def require_game(f):
    """Декоратор для проверки наличия активной игры"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        game_id = session.get('current_game_id')
        if not game_id:
            logger.warning(f"No active game for user {session.get('user_id')}")
            return jsonify({'error': 'No active game'}), 400
            
        game = app_state.get_game(game_id)
        if not game:
            logger.warning(f"Game {game_id} not found")
            return jsonify({'error': 'Game not found'}), 404
            
        return f(*args, game=game, **kwargs)
    return decorated_function

def handle_errors(f):
    """Декоратор для обработки ошибок"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {e}", exc_info=True)
            error_id = str(uuid.uuid4())
            analytics_manager.track_error(error_id, e)
            return jsonify({
                'error': str(e),
                'error_id': error_id
            }), 500
    return decorated_function

def require_websocket(f):
    """Декоратор для проверки WebSocket соединения"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.environ.get('wsgi.websocket'):
            logger.warning("WebSocket connection required")
            return jsonify({'error': 'WebSocket connection required'}), 400
        return f(*args, **kwargs)
    return decorated_function

# Вспомогательные функции
def emit_game_update(game: Game, event_type: str = 'game_state'):
    """Отправляет обновление состояния игры через WebSocket"""
    room = session.get('user_id')
    if room:
        try:
            state = game.get_state()
            state['event_type'] = event_type
            state['timestamp'] = datetime.now().isoformat()
            state['connection_status'] = {
                'latency': socketio.server.manager.get_latency(room),
                'connected': True
            }
            socketio.emit('game_update', state, room=room)
            logger.debug(f"Game update emitted: {event_type}")
        except Exception as e:
            logger.error(f"Error emitting game update: {e}", exc_info=True)
            socketio.emit('error', {
                'message': 'Failed to update game state',
                'error': str(e)
            }, room=room)
            WEBSOCKET_ERRORS.labels(type='emit_error').inc()

def save_game_progress(game: Game):
    """Сохраняет прогресс игры"""
    try:
        state = game.save_state()
        session['saved_game_state'] = state
        analytics_manager.track_game_save(game)
        logger.info(f"Game progress saved for game {game.id}")
        return True
    except Exception as e:
        logger.error(f"Error saving game progress: {e}", exc_info=True)
        return False

def load_game_progress():
    """Загружает сохраненный прогресс игры"""
    try:
        saved_state = session.get('saved_game_state')
        if not saved_state:
            return None
            
        game_id = str(uuid.uuid4())
        game = app_state.create_game(game_id, saved_state['config'])
        game.load_state(saved_state)
        session['current_game_id'] = game_id
        logger.info(f"Game progress loaded: {game_id}")
        
        return game
    except Exception as e:
        logger.error(f"Error loading game progress: {e}", exc_info=True)
        return None

async def process_ai_move(game: Game):
    """Асинхронная обработка хода AI"""
    try:
        # Показываем, что AI думает
        emit_game_update(game, 'ai_thinking')
        start_time = time()
        
        # Получаем ход AI в отдельном потоке
        ai_move = await asyncio.get_event_loop().run_in_executor(
            executor,
            game.get_ai_move
        )
        
        think_time = time() - start_time
        logger.debug(f"AI think time: {think_time:.2f}s")
        
        # Применяем ход
        success = game.make_move(game.current_player, *ai_move)
        if success:
            AI_METRICS.labels(
                agent=get_agent_display_name(game.current_agent),
                action='move_success'
            ).inc()
            
            # Проверяем на фолы и скупы
            if ai_move.is_foul:
                game.state.fouls += 1
            if ai_move.is_scoop:
                game.state.scoops += 1
            game.state.totalMoves += 1
            
            # Обновляем статистику AI
            analytics_manager.track_ai_move(
                game.current_agent,
                ai_move,
                think_time
            )
        else:
            AI_METRICS.labels(
                agent=get_agent_display_name(game.current_agent),
                action='move_failed'
            ).inc()
            logger.warning(f"AI move failed for agent {game.current_agent.name}")
            
        # Отправляем обновление
        emit_game_update(game)
        
        return success
    except Exception as e:
        logger.error(f"Error processing AI move: {e}", exc_info=True)
        WEBSOCKET_ERRORS.labels(type='ai_move_error').inc()
        return False

def check_game_over(game: Game):
    """Проверяет окончание игры и обрабатывает его"""
    if game.is_game_over():
        try:
            result = game.get_result()
            room = session.get('user_id')
            if room:
                socketio.emit('game_over', {
                    'result': result,
                    'timestamp': datetime.now().isoformat(),
                    'statistics': game.get_statistics()
                }, room=room)
            
            # Сохраняем статистику
            analytics_manager.track_game_end(game, result)
            logger.info(f"Game {game.id} finished. Winner: {result.winner}")
            
            # Очищаем состояние
            app_state.remove_game(session.get('current_game_id'))
            session.pop('current_game_id', None)
            session.pop('saved_game_state', None)
            
            return True
        except Exception as e:
            logger.error(f"Error handling game over: {e}", exc_info=True)
            WEBSOCKET_ERRORS.labels(type='game_over_error').inc()
    
    return False

def is_mobile():
    """Проверяет, является ли клиент мобильным устройством"""
    return request.user_agent.platform in ['android', 'iphone', 'ipad']

def get_client_preferences():
    """Получает предпочтения клиента"""
    return {
        'is_mobile': is_mobile(),
        'theme': session.get('preferences', {}).get('theme', 'light'),
        'animation_speed': session.get('preferences', {}).get('animation_speed', 'normal'),
        'sound_enabled': session.get('preferences', {}).get('sound_enabled', True),
        'connection_time': session.get('connection_time'),
        'websocket_connected': bool(request.environ.get('wsgi.websocket'))
    }

def check_connection_health():
    """Проверяет здоровье соединения"""
    try:
        room = session.get('user_id')
        if room:
            latency = socketio.server.manager.get_latency(room)
            connected = socketio.server.manager.is_connected(room)
            return {
                'status': 'healthy' if connected and latency < 1000 else 'degraded',
                'latency': latency,
                'connected': connected,
                'uptime': time() - session.get('connection_time', time())
            }
    except Exception as e:
        logger.error(f"Error checking connection health: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }

# Middleware
@app.before_request
def before_request():
    """Выполняется перед каждым запросом"""
    g.start_time = datetime.now()
    REQUESTS.labels(
        method=request.method,
        endpoint=request.endpoint or 'unknown'
    ).inc()
    
    logger.info(f'Request: {request.method} {request.url}')
    init_session()
    app_state.register_user_activity(session['user_id'])

@app.after_request
def after_request(response):
    """Выполняется после каждого запроса"""
    if hasattr(g, 'start_time'):
        elapsed = datetime.now() - g.start_time
        RESPONSE_TIME.observe(elapsed.total_seconds())
        logger.info(f'Response: {response.status} - {elapsed.total_seconds():.3f}s')
    
    return response

# Периодические задачи
def cleanup_task():
    """Периодическая очистка неактивных сессий"""
    while True:
        try:
            app_state.cleanup_inactive_sessions()
            # Проверяем здоровье соединений
            for room in socketio.server.manager.get_rooms():
                health = check_connection_health()
                if health['status'] != 'healthy':
                    logger.warning(f"Unhealthy connection in room {room}: {health}")
            socketio.sleep(300)  # Каждые 5 минут
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}", exc_info=True)
            socketio.sleep(60)

# Запуск периодических задач
socketio.start_background_task(cleanup_task)

# WebSocket обработчики
@socketio.on('connect')
def handle_connect():
    """Обработка подключения WebSocket"""
    WEBSOCKET_CONNECTIONS.inc()
    connections['active'] += 1
    connections['total'] += 1
    
    logger.info(f"WebSocket connected: {request.sid}")
    
    room = session.get('user_id')
    if room:
        join_room(room)
        emit('connection_established', {
            'status': 'connected',
            'user_id': room,
            'timestamp': datetime.now().isoformat(),
            'connection_info': {
                'sid': request.sid,
                'transport': request.environ.get('wsgi.websocket_version'),
                'latency': socketio.server.manager.get_latency(room)
            }
        })
    
    game_id = session.get('current_game_id')
    if game_id:
        game = app_state.get_game(game_id)
        if game:
            emit('game_state', game.get_state())
            
    emit('client_preferences', get_client_preferences())

@socketio.on('disconnect')
def handle_disconnect():
    """Обработка отключения WebSocket"""
    logger.info(f"WebSocket disconnected: {request.sid}")
    connections['active'] -= 1
    
    game_id = session.get('current_game_id')
    if game_id:
        game = app_state.get_game(game_id)
        if game:
            save_game_progress(game)
    
    room = session.get('user_id')
    if room:
        leave_room(room)

@socketio.on('connect_error')
def handle_connect_error(error):
    """Обработка ошибок подключения"""
    connections['errors'] += 1
    connections['last_error'] = str(error)
    logger.error(f"WebSocket connection error: {error}")
    WEBSOCKET_ERRORS.labels(type='connection_error').inc()
    emit('connection_status', {
        'status': 'error',
        'message': str(error),
        'timestamp': datetime.now().isoformat()
    })

@socketio.on('game_action')
@handle_errors
def handle_game_action(data):
    """Обработка игровых действий"""
    game_id = session.get('current_game_id')
    if not game_id:
        emit('error', {'message': 'No active game'})
        return
    
    game = app_state.get_game(game_id)
    if not game:
        emit('error', {'message': 'Game not found'})
        return
        
    action_type = data.get('type')
    logger.debug(f"Game action received: {action_type}")
    
    try:
        if action_type == 'select_mode':
            game.set_mode(data.get('mode'))
            logger.info(f"Game mode changed to: {data.get('mode')}")
        elif action_type == 'set_think_time':
            game.set_think_time(data.get('time'))
            logger.info(f"AI think time changed to: {data.get('time')}s")
        elif action_type == 'toggle_fantasy':
            game.toggle_fantasy_mode()
            logger.info("Fantasy mode toggled")
        elif action_type == 'select_players':
            game.set_players_count(data.get('count'))
            logger.info(f"Players count changed to: {data.get('count')}")
        
        emit_game_update(game)
        
    except Exception as e:
        logger.error(f"Error processing game action: {e}", exc_info=True)
        emit('error', {
            'message': 'Failed to process game action',
            'error': str(e)
        })
        WEBSOCKET_ERRORS.labels(type='game_action_error').inc()

@socketio.on('request_analysis')
@handle_errors
def handle_analysis_request(data):
    """Обработка запроса анализа позиции"""
    game_id = session.get('current_game_id')
    if not game_id:
        emit('error', {'message': 'No active game'})
        return
        
    game = app_state.get_game(game_id)
    if not game:
        emit('error', {'message': 'Game not found'})
        return
        
    try:
        analysis = game.analyze_position(data.get('position'))
        emit('position_analysis', {
            'analysis': analysis,
            'position': data.get('position'),
            'timestamp': datetime.now().isoformat()
        })
        logger.debug(f"Position analysis sent for position: {data.get('position')}")
    except Exception as e:
        logger.error(f"Error analyzing position: {e}", exc_info=True)
        emit('error', {
            'message': 'Failed to analyze position',
            'error': str(e)
        })
        WEBSOCKET_ERRORS.labels(type='analysis_error').inc()

@socketio.on('chat_message')
def handle_chat_message(data):
    """Обработка сообщений чата"""
    room = session.get('user_id')
    if room:
        try:
            socketio.emit('chat_message', {
                'user': session.get('user_id'),
                'message': data.get('message'),
                'timestamp': datetime.now().isoformat()
            }, room=room)
            logger.debug(f"Chat message sent in room {room}")
        except Exception as e:
            logger.error(f"Error sending chat message: {e}", exc_info=True)
            WEBSOCKET_ERRORS.labels(type='chat_error').inc()

@socketio.on_error()
def handle_error(e):
    """Глобальный обработчик ошибок WebSocket"""
    logger.error(f"WebSocket error: {e}", exc_info=True)
    WEBSOCKET_ERRORS.labels(type='general_error').inc()
    emit('error', {
        'message': 'Internal server error',
        'error': str(e),
        'timestamp': datetime.now().isoformat()
    })

# API маршруты
@app.route('/')
def index():
    """Главная страница"""
    preferences = get_client_preferences()
    connection_health = check_connection_health()
    return render_template(
        'index.html',
        preferences=preferences,
        agents=AVAILABLE_AGENTS,
        connection_status=connection_health
    )

@app.route('/api/health')
def health_check():
    """Проверка здоровья приложения"""
    health_status = {
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'websocket': {
            'active_connections': connections['active'],
            'total_connections': connections['total'],
            'errors': connections['errors'],
            'last_error': connections['last_error']
        },
        'server': {
            'uptime': time() - app.start_time if hasattr(app, 'start_time') else 0,
            'memory_usage': os.getpid(),
            'active_games': len(app_state.games)
        }
    }
    
    connection_health = check_connection_health()
    if connection_health['status'] != 'healthy':
        health_status['status'] = 'degraded'
        health_status['websocket']['health'] = connection_health
    
    return jsonify(health_status)

@app.route('/api/new_game', methods=['POST'])
@handle_errors
def new_game():
    """Создает новую игру"""
    data = request.get_json()
    game_id = str(uuid.uuid4())
    
    try:
        game_config = {
            'players': data.get('players', 2),
            'fantasy_mode': (FantasyMode.PROGRESSIVE 
                            if data.get('progressive_fantasy') 
                            else FantasyMode.NORMAL),
            'think_time': data.get('aiThinkTime', 30),
            'agents': [],
            'is_mobile': is_mobile()
        }
        
        # Создаем AI агентов
        for i in range(game_config['players'] - 1):
            agent_type = data.get(f'agent_{i}', 'random')
            agent = create_agent(
                agent_type=agent_type,
                position=i+1,
                think_time=game_config['think_time']
            )
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
        return jsonify({
            'error': 'Failed to create game',
            'message': str(e)
        }), 500

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
            # Проверяем на фолы и скупы
            if data.get('is_foul'):
                game.state.fouls += 1
            if data.get('is_scoop'):
                game.state.scoops += 1
            game.state.totalMoves += 1
            
            emit_game_update(game)
            logger.debug(f"Move made: {data.get('card')} to position {data.get('position')}")
            
            # Обрабатываем ход AI если игра не закончена
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

async def process_ai_moves(game):
    """Обрабатывает ходы AI последовательно"""
    while not game.is_game_over() and game.current_player != 1:
        success = await process_ai_move(game)
        if not success:
            break
        if game.is_game_over():
            check_game_over(game)
            break

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

@app.route('/api/game/save', methods=['POST'])
@require_game
@handle_errors
def save_game(game):
    """Сохраняет текущую игру"""
    if save_game_progress(game):
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'Failed to save game'}), 500

@app.route('/api/game/load', methods=['POST'])
@handle_errors
def load_game():
    """Загружает сохраненную игру"""
    game = load_game_progress()
    if game:
        emit_game_update(game, 'game_loaded')
        return jsonify({
            'status': 'ok',
            'game_state': game.get_state()
        })
    return jsonify({'error': 'No saved game found'}), 404

@app.route('/api/settings', methods=['GET', 'POST'])
@handle_errors
def handle_settings():
    """Обработка пользовательских настроек"""
    if request.method == 'POST':
        settings = request.get_json()
        session['preferences'].update({
            'theme': settings.get('theme', 'light'),
            'animation_speed': settings.get('animation_speed', 'normal'),
            'sound_enabled': settings.get('sound_enabled', True)
        })
        return jsonify({'status': 'ok'})
    
    return jsonify({
        'status': 'ok',
        'preferences': get_client_preferences()
    })

@app.route('/api/statistics', methods=['GET'])
@handle_errors
def get_statistics():
    """Получение статистики"""
    return jsonify({
        'status': 'ok',
        'statistics': analytics_manager.get_full_statistics(),
        'server_stats': {
            'connections': connections,
            'active_games': len(app_state.games),
            'uptime': time() - app.start_time if hasattr(app, 'start_time') else 0
        }
    })

# Обработка ошибок
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

# Запуск приложения
if __name__ == '__main__':
    try:
        # Установка времени запуска
        app.start_time = time()
        
        # Получение настроек из конфигурации
        port = int(os.environ.get('PORT', config.get('web.port', 5000)))
        debug = config.get('web.debug', False)
        
        logger.info(f"Starting server on port {port} (debug={debug})")
        logger.info(f"Available agents: {list(AVAILABLE_AGENTS.keys())}")
        logger.info(f"Application version: {config.get('app.version', 'unknown')}")
        
        # Запуск сервера
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

