import sys
import os
from pathlib import Path
import tensorflow as tf
from datetime import datetime
from prometheus_client import Counter, Histogram
from logging.config import dictConfig
from flask import Flask, render_template, jsonify, request, g, session, redirect, url_for, make_response, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from typing import Optional, Dict, Any, List
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

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
WEBSOCKET_CONNECTIONS = Counter('websocket_connections_total', 'WebSocket connections')
AI_METRICS = Counter('ai_metrics_total', 'AI related metrics', ['agent', 'action'])

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

app.config.update(
    JSON_SORT_KEYS=False,
    PROPAGATE_EXCEPTIONS=True,
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
    DEBUG=config.get('web.debug', False),
    SECRET_KEY=config.get('security.secret_key', os.urandom(24)),
    PERMANENT_SESSION_LIFETIME=config.get('web.session_lifetime', 3600)
)

# Инициализация SocketIO с поддержкой асинхронности
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    async_mode='gevent',
    ping_timeout=60,
    ping_interval=25
)

# Инициализация глобальных объектов
app_state = AppState()
analytics_manager = AnalyticsManager()
executor = ThreadPoolExecutor(max_workers=4)

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
    if 'preferences' not in session:
        session['preferences'] = {
            'theme': 'light',
            'animation_speed': 'normal',
            'sound_enabled': True
        }

# Декораторы
def require_game(f):
    """Декоратор для проверки наличия активной игры"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        game_id = session.get('current_game_id')
        if not game_id:
            return jsonify({'error': 'No active game'}), 400
            
        game = app_state.get_game(game_id)
        if not game:
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
            return jsonify({'error': str(e)}), 500
    return decorated_function

# Вспомогательные функции
def emit_game_update(game: Game, event_type: str = 'game_state'):
    """Отправляет обновление состояния игры через WebSocket"""
    room = session.get('user_id')
    if room:
        state = game.get_state()
        state['event_type'] = event_type
        socketio.emit('game_update', state, room=room)

def save_game_progress(game: Game):
    """Сохраняет прогресс игры"""
    try:
        state = game.save_state()
        session['saved_game_state'] = state
        analytics_manager.track_game_save(game)
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
        
        return game
    except Exception as e:
        logger.error(f"Error loading game progress: {e}", exc_info=True)
        return None

async def process_ai_move(game: Game):
    """Асинхронная обработка хода AI"""
    try:
        # Показываем, что AI думает
        emit_game_update(game, 'ai_thinking')
        
        # Получаем ход AI в отдельном потоке
        ai_move = await asyncio.get_event_loop().run_in_executor(
            executor,
            game.get_ai_move
        )
        
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
        else:
            AI_METRICS.labels(
                agent=get_agent_display_name(game.current_agent),
                action='move_failed'
            ).inc()
            
        # Отправляем обновление
        emit_game_update(game)
        
        return success
    except Exception as e:
        logger.error(f"Error processing AI move: {e}", exc_info=True)
        return False

def check_game_over(game: Game):
    """Проверяет окончание игры и обрабатывает его"""
    if game.is_game_over():
        try:
            result = game.get_result()
            room = session.get('user_id')
            if room:
                socketio.emit('game_over', result, room=room)
            
            # Сохраняем статистику
            analytics_manager.track_game_end(game, result)
            
            # Очищаем состояние
            app_state.remove_game(session.get('current_game_id'))
            session.pop('current_game_id', None)
            session.pop('saved_game_state', None)
            
            return True
        except Exception as e:
            logger.error(f"Error handling game over: {e}", exc_info=True)
    
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
        'sound_enabled': session.get('preferences', {}).get('sound_enabled', True)
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
            socketio.sleep(300)  # Каждые 5 минут
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}", exc_info=True)
            socketio.sleep(60)

# Запуск периодических задач
socketio.start_background_task(cleanup_task)

# Основные маршруты
@app.route('/')
def index():
    """Главная страница"""
    preferences = get_client_preferences()
    return render_template(
        'index.html',
        preferences=preferences,
        agents=AVAILABLE_AGENTS
    )

@app.route('/tutorial')
def tutorial():
    """Страница обучения"""
    return render_template(
        'tutorial.html',
        preferences=get_client_preferences()
    )

@app.route('/training')
def training():
    """Страница режима тренировки"""
    preferences = get_client_preferences()
    return render_template(
        'training.html',
        preferences=preferences,
        agents=AVAILABLE_AGENTS
    )

@app.route('/statistics')
def statistics():
    """Страница статистики"""
    try:
        full_stats = analytics_manager.get_full_statistics()
        return render_template(
            'statistics.html',
            statistics=full_stats,
            preferences=get_client_preferences()
        )
    except Exception as e:
        logger.error(f"Error getting statistics: {e}", exc_info=True)
        return render_template(
            'error.html',
            error="Failed to load statistics",
            preferences=get_client_preferences()
        )

# API маршруты
@app.route('/api/new_game', methods=['POST'])
@handle_errors
def new_game():
    """Создает новую игру"""
    data = request.get_json()
    game_id = str(uuid.uuid4())
    
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
    
    return jsonify({
        'status': 'ok',
        'game_id': game_id,
        'game_state': game.get_state()
    })

@app.route('/api/game/move', methods=['POST'])
@require_game
@handle_errors
def make_move(game):
    """Выполняет ход игрока"""
    data = request.get_json()
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
        
        # Обрабатываем ход AI если игра не закончена
        if not game.is_game_over():
            asyncio.create_task(process_ai_moves(game))
        else:
            check_game_over(game)
            
        return jsonify({
            'status': 'ok',
            'game_state': game.get_state()
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

@app.route('/api/game/fantasy', methods=['GET', 'POST'])
@require_game
@handle_errors
def handle_fantasy(game):
    """Обработка фантазии"""
    if request.method == 'POST':
        success = game.check_fantasy_entry(request.get_json().get('player'))
        return jsonify({
            'status': 'ok',
            'fantasy_active': success,
            'game_state': game.get_state()
        })
    else:
        return jsonify({
            'status': 'ok',
            'fantasy_status': game.get_fantasy_status(),
            'statistics': game.get_fantasy_statistics()
        })

@app.route('/api/game/undo', methods=['POST'])
@require_game
@handle_errors
def undo_move(game):
    """Отменяет последний ход"""
    if game.undo_last_move():
        emit_game_update(game)
        return jsonify({
            'status': 'ok',
            'game_state': game.get_state()
        })
    return jsonify({'error': 'Cannot undo move'}), 400

@app.route('/api/training/start', methods=['POST'])
@handle_errors
def start_training():
    """Начинает тренировочную сессию"""
    data = request.get_json()
    session_id = str(uuid.uuid4())
    
    config = TrainingConfig(
        fantasy_mode=data.get('fantasy_mode', False),
        progressive_fantasy=data.get('progressive_fantasy', False),
        think_time=data.get('think_time', 30)
    )
    
    training_session = app_state.create_training_session(session_id, config)
    session['training_session_id'] = session_id
    
    return jsonify({
        'status': 'ok',
        'session_id': session_id,
        'initial_state': training_session.get_state()
    })

@app.route('/api/training/analyze', methods=['POST'])
@handle_errors
def analyze_training_position():
    """Анализирует позицию в режиме тренировки"""
    session_id = session.get('training_session_id')
    if not session_id:
        return jsonify({'error': 'No active training session'}), 400
        
    training_session = app_state.get_training_session(session_id)
    if not training_session:
        return jsonify({'error': 'Training session not found'}), 404
        
    analysis = training_session.analyze_position(
        request.get_json().get('board_state')
    )
    
    return jsonify({
        'status': 'ok',
        'analysis': analysis
    })

@app.route('/api/settings', methods=['GET', 'POST'])
@handle_errors
def handle_settings():
    """Обработка пользовательских настроек"""
    if request.method == 'POST':
        settings = request.get_json()
        session['preferences'] = {
            'theme': settings.get('theme', 'light'),
            'animation_speed': settings.get('animation_speed', 'normal'),
            'sound_enabled': settings.get('sound_enabled', True)
        }
        return jsonify({'status': 'ok'})
    
    return jsonify({
        'status': 'ok',
        'preferences': get_client_preferences()
    })

@app.route('/api/statistics/full')
@handle_errors
def get_full_statistics():
    """Возвращает полную статистику"""
    stats = analytics_manager.get_full_statistics()
    return jsonify({
        'status': 'ok',
        'statistics': stats
    })

@app.route('/manifest.json')
def manifest():
    """PWA manifest"""
    return jsonify({
        "name": "Open Face Chinese Poker",
        "short_name": "OFC Poker",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#007bff",
        "icons": [
            {
                "src": url_for('static', filename='images/icon-192.png'),
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": url_for('static', filename='images/icon-512.png'),
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    })

@app.route('/service-worker.js')
def service_worker():
    """Service Worker для PWA"""
    response = make_response(
        send_from_directory('static', 'js/service-worker.js')
    )
    response.headers['Content-Type'] = 'application/javascript'
    return response

@app.route('/offline')
def offline():
    """Страница для оффлайн режима"""
    return render_template(
        'offline.html',
        preferences=get_client_preferences()
    )

# WebSocket обработчики
@socketio.on('connect')
def handle_connect():
    """Обработка подключения WebSocket"""
    WEBSOCKET_CONNECTIONS.inc()
    logger.info(f"WebSocket connected: {request.sid}")
    
    room = session.get('user_id')
    if room:
        join_room(room)
    
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
    
    game_id = session.get('current_game_id')
    if game_id:
        game = app_state.get_game(game_id)
        if game:
            save_game_progress(game)
    
    room = session.get('user_id')
    if room:
        leave_room(room)

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
        
    analysis = game.analyze_position(data.get('position'))
    emit('position_analysis', {
        'analysis': analysis,
        'position': data.get('position')
    })

@socketio.on('chat_message')
def handle_chat_message(data):
    """Обработка сообщений чата"""
    room = session.get('user_id')
    if room:
        socketio.emit('chat_message', {
            'user': session.get('user_id'),
            'message': data.get('message'),
            'timestamp': datetime.now().isoformat()
        }, room=room)

@socketio.on_error()
def handle_error(e):
    """Глобальный обработчик ошибок WebSocket"""
    logger.error(f"WebSocket error: {e}", exc_info=True)
    emit('error', {'message': 'Internal server error'})

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
    port = int(os.environ.get('PORT', 5000))
    debug = config.get('web.debug', False)
    
    logger.info(f"Starting server on port {port} (debug={debug})")
    logger.info(f"Available agents: {list(AVAILABLE_AGENTS.keys())}")
    logger.info(f"Application version: {config.get('app.version', 'unknown')}")
    
    try:
        socketio.run(
            app,
            host='0.0.0.0',
            port=port,
            debug=debug,
            use_reloader=debug,
            log_output=True
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)
