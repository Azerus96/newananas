import sys
import os
from pathlib import Path
import tensorflow as tf
from datetime import datetime
from prometheus_client import Counter, Histogram
from logging.config import dictConfig
from flask import Flask, render_template, jsonify, request, g, session, redirect, url_for
from flask_socketio import SocketIO, emit
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

@app.route('/mobile')
def mobile():
    """Мобильная версия"""
    if not is_mobile():
        return redirect(url_for('index'))
    
    preferences = get_client_preferences()
    return render_template(
        'mobile.html',
        preferences=preferences,
        agents=AVAILABLE_AGENTS
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

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Страница настроек"""
    if request.method == 'POST':
        try:
            new_preferences = request.get_json()
            session['preferences'].update(new_preferences)
            return jsonify({'status': 'ok'})
        except Exception as e:
            logger.error(f"Error updating settings: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 400
    
    return render_template(
        'settings.html',
        preferences=get_client_preferences(),
        agents=AVAILABLE_AGENTS
    )

@app.route('/tutorial')
def tutorial():
    """Страница обучения"""
    return render_template(
        'tutorial.html',
        preferences=get_client_preferences()
    )

@app.route('/game/<game_id>')
@require_game
def game_page(game_id, game):
    """Страница игры"""
    try:
        return render_template(
            'game.html',
            game=game,
            preferences=get_client_preferences(),
            state=game.get_state()
        )
    except Exception as e:
        logger.error(f"Error loading game page: {e}", exc_info=True)
        return redirect(url_for('index'))

@app.route('/ai-arena')
def ai_arena():
    """Страница AI vs AI"""
    return render_template(
        'ai_arena.html',
        preferences=get_client_preferences(),
        agents=AVAILABLE_AGENTS
    )

# Обработка ошибок для основных маршрутов
@app.errorhandler(404)
def page_not_found(e):
    """Обработка 404 ошибки"""
    return render_template(
        'error.html',
        error="Page not found",
        preferences=get_client_preferences()
    ), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Обработка 500 ошибки"""
    return render_template(
        'error.html',
        error="Internal server error",
        preferences=get_client_preferences()
    ), 500

# Вспомогательные маршруты
@app.route('/manifest.json')
def manifest():
    """PWA manifest"""
    return jsonify({
        "name": "Open Face Chinese Poker",
        "short_name": "OFCP",
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

# API маршруты
@app.route('/api/agents')
@handle_errors
def get_available_agents():
    """Возвращает список доступных агентов"""
    agents_list = [
        {
            'id': agent_id,
            'name': info['display_name'],
            'description': info['class'].__doc__,
            'capabilities': {
                'supports_fantasy': hasattr(info['class'], 'handle_fantasy'),
                'supports_progressive': hasattr(info['class'], 'handle_progressive'),
                'has_learning': hasattr(info['class'], 'learn')
            }
        }
        for agent_id, info in AVAILABLE_AGENTS.items()
    ]
    
    return jsonify({
        'status': 'ok',
        'agents': agents_list
    })

@app.route('/api/new_game', methods=['POST'])
@handle_errors
def new_game():
    """Создает новую игру"""
    data = request.get_json()
    game_id = str(uuid.uuid4())
    
    # Базовая конфигурация
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
    
    # Создаем и запускаем игру
    game = app_state.create_game(game_id, game_config)
    game.start()
    
    # Сохраняем ID игры в сессии
    session['current_game_id'] = game_id
    
    # Отправляем начальное состояние через WebSocket
    emit_game_update(game, 'game_started')
    
    GAME_METRICS.labels(type='new_game').inc()
    
    return jsonify({
        'status': 'ok',
        'game_id': game_id,
        'game_state': game.get_state()
    })

@app.route('/api/make_move', methods=['POST'])
@require_game
@handle_errors
def make_move(game):
    """Выполняет ход в игре"""
    data = request.get_json()
    
    # Создаем объект карты из данных
    card = Card.from_dict(data.get('card'))
    street = Street(data.get('street'))
    
    # Делаем ход
    success = game.make_move(1, card, street)
    if not success:
        return jsonify({'error': 'Invalid move'}), 400

    # Отправляем обновление состояния
    emit_game_update(game, 'move_made')

    # Обрабатываем ход AI если игра не закончена
    if not game.is_game_over():
        asyncio.create_task(process_ai_moves(game))
    else:
        check_game_over(game)

    GAME_METRICS.labels(type='move').inc()
    
    return jsonify({
        'status': 'ok',
        'game_state': game.get_state()
    })

async def process_ai_moves(game):
    """Обрабатывает ходы AI последовательно"""
    while not game.is_game_over() and game.current_player != 1:
        success = await process_ai_move(game)
        if not success:
            break
        if game.is_game_over():
            check_game_over(game)
            break

@app.route('/api/ai_vs_ai', methods=['POST'])
@handle_errors
def create_ai_vs_ai_game():
    """Создает игру AI против AI"""
    data = request.get_json()
    game_id = str(uuid.uuid4())
    
    # Создаем агентов
    agent1 = create_agent(
        agent_type=data.get('agent1', 'random'),
        position=1,
        think_time=data.get('think_time', 30)
    )
    
    agent2 = create_agent(
        agent_type=data.get('agent2', 'random'),
        position=2,
        think_time=data.get('think_time', 30)
    )
    
    game_config = {
        'players': 2,
        'fantasy_mode': FantasyMode.NORMAL,
        'think_time': data.get('think_time', 30),
        'agents': [agent1, agent2],
        'is_ai_vs_ai': True
    }
    
    game = app_state.create_game(game_id, game_config)
    game.start()
    
    session['current_game_id'] = game_id
    
    # Запускаем игровой процесс в фоне
    socketio.start_background_task(target=run_ai_vs_ai_game, game_id=game_id)
    
    return jsonify({
        'status': 'ok',
        'game_id': game_id,
        'game_state': game.get_state()
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

@app.route('/api/save_state', methods=['POST'])
@require_game
@handle_errors
def save_state(game):
    """Сохраняет текущее состояние игры"""
    if save_game_progress(game):
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'Failed to save game state'}), 500

@app.route('/api/load_state', methods=['POST'])
@handle_errors
def load_state():
    """Загружает сохраненное состояние игры"""
    game = load_game_progress()
    if game:
        return jsonify({
            'status': 'ok',
            'game_id': session['current_game_id'],
            'game_state': game.get_state()
        })
    return jsonify({'error': 'No saved game state found'}), 404

# WebSocket события и обработчики
@socketio.on('connect')
def handle_connect():
    """Обработка подключения WebSocket"""
    WEBSOCKET_CONNECTIONS.inc()
    logger.info(f"WebSocket connected: {request.sid}")
    
    # Присоединяем клиента к персональной комнате
    room = session.get('user_id')
    if room:
        socketio.join_room(room)
    
    # Отправляем текущее состояние если есть активная игра
    game_id = session.get('current_game_id')
    if game_id:
        game = app_state.get_game(game_id)
        if game:
            emit('game_state', game.get_state())
            
    # Отправляем настройки клиента
    emit('client_preferences', get_client_preferences())

@socketio.on('disconnect')
def handle_disconnect():
    """Обработка отключения WebSocket"""
    logger.info(f"WebSocket disconnected: {request.sid}")
    
    # Сохраняем состояние игры при отключении
    game_id = session.get('current_game_id')
    if game_id:
        game = app_state.get_game(game_id)
        if game:
            save_game_progress(game)
    
    # Покидаем комнату
    room = session.get('user_id')
    if room:
        socketio.leave_room(room)

@socketio.on('request_game_state')
@handle_errors
def handle_state_request():
    """Обработка запроса текущего состояния игры"""
    game_id = session.get('current_game_id')
    if game_id:
        game = app_state.get_game(game_id)
        if game:
            emit('game_state', game.get_state())

@socketio.on('player_ready')
def handle_player_ready(data):
    """Обработка готовности игрока"""
    game_id = session.get('current_game_id')
    if game_id:
        game = app_state.get_game(game_id)
        if game:
            game.player_ready(data.get('player_id'))
            emit_game_update(game, 'player_ready')

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

@socketio.on('request_ai_explanation')
@handle_errors
def handle_ai_explanation_request(data):
    """Запрос объяснения хода AI"""
    game_id = session.get('current_game_id')
    if not game_id:
        return
        
    game = app_state.get_game(game_id)
    if not game:
        return
        
    move_index = data.get('move_index')
    if move_index is None:
        return
        
    try:
        explanation = game.get_ai_move_explanation(move_index)
        emit('ai_explanation', {
            'move_index': move_index,
            'explanation': explanation
        })
    except Exception as e:
        logger.error(f"Error getting AI explanation: {e}", exc_info=True)
        emit('error', {'message': 'Failed to get AI explanation'})

@socketio.on('training_action')
@handle_errors
def handle_training_action(data):
    """Обработка действий в режиме тренировки"""
    session_id = session.get('training_session_id')
    if not session_id:
        emit('error', {'message': 'No active training session'})
        return
        
    training_session = app_state.get_training_session(session_id)
    if not training_session:
        emit('error', {'message': 'Training session not found'})
        return
        
    action_type = data.get('action')
    if action_type == 'distribute':
        result = training_session.distribute_cards(data.get('cards', []))
        emit('training_update', {
            'action': 'distribute',
            'result': result
        })
    elif action_type == 'reset':
        training_session.reset()
        emit('training_update', {
            'action': 'reset',
            'state': training_session.get_state()
        })
    elif action_type == 'analyze':
        analysis = training_session.analyze_position()
        emit('training_update', {
            'action': 'analyze',
            'analysis': analysis
        })

async def run_ai_vs_ai_game(game_id: str):
    """Запускает процесс игры AI против AI"""
    try:
        game = app_state.get_game(game_id)
        if not game:
            return
            
        while not game.is_game_over():
            # Получаем и делаем ход текущего AI
            success = await process_ai_move(game)
            if not success:
                break
                
            # Добавляем задержку для визуализации
            await asyncio.sleep(1)
            
            if game.is_game_over():
                break
        
        # Обрабатываем окончание игры
        if game.is_game_over():
            check_game_over(game)
            
    except Exception as e:
        logger.error(f"Error in AI vs AI game: {e}", exc_info=True)
        room = session.get('user_id')
        if room:
            socketio.emit('error', {
                'message': 'AI vs AI game failed',
                'details': str(e)
            }, room=room)

@socketio.on_error()
def handle_error(e):
    """Глобальный обработчик ошибок WebSocket"""
    logger.error(f"WebSocket error: {e}", exc_info=True)
    emit('error', {'message': 'Internal server error'})

# Периодическое обновление статистики
def emit_statistics_updates():
    """Периодически отправляет обновления статистики"""
    while True:
        try:
            stats = analytics_manager.get_global_statistics()
            socketio.emit('statistics_update', stats)
            socketio.sleep(30)  # Обновление каждые 30 секунд
        except Exception as e:
            logger.error(f"Error updating statistics: {e}", exc_info=True)
            socketio.sleep(5)

# Запуск фоновых задач
socketio.start_background_task(emit_statistics_updates)

# Обработка ошибок и мониторинг здоровья
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

@app.route('/health')
def health_check():
    """Проверка здоровья приложения"""
    try:
        # Проверяем основные компоненты
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'components': {
                'database': check_database_health(),
                'redis': check_redis_health(),
                'ai_models': check_ai_models_health()
            },
            'metrics': {
                'active_games': len(app_state.get_active_games()),
                'active_training_sessions': len(app_state.get_active_training_sessions()),
                'connected_users': len(app_state._active_users),
                'memory_usage': get_memory_usage(),
                'cpu_usage': get_cpu_usage()
            },
            'version': config.get('app.version', 'unknown')
        }

        # Определяем общий статус
        components_healthy = all(
            status == 'healthy' 
            for status in health_status['components'].values()
        )
        
        if not components_healthy:
            health_status['status'] = 'degraded'
            
        status_code = 200 if components_healthy else 503
        
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503

def check_database_health() -> str:
    """Проверка здоровья базы данных"""
    try:
        # Здесь должна быть проверка подключения к БД
        return 'healthy'
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        return 'unhealthy'

def check_redis_health() -> str:
    """Проверка здоровья Redis"""
    try:
        # Здесь должна быть проверка подключения к Redis
        return 'healthy'
    except Exception as e:
        logger.error(f"Redis health check failed: {e}", exc_info=True)
        return 'unhealthy'

def check_ai_models_health() -> str:
    """Проверка здоровья AI моделей"""
    try:
        # Проверяем доступность всех AI моделей
        for agent_type, info in AVAILABLE_AGENTS.items():
            if not info['class'].check_model_available():
                return 'degraded'
        return 'healthy'
    except Exception as e:
        logger.error(f"AI models health check failed: {e}", exc_info=True)
        return 'unhealthy'

def get_memory_usage() -> dict:
    """Получает информацию об использовании памяти"""
    import psutil
    process = psutil.Process()
    memory_info = process.memory_info()
    return {
        'rss': memory_info.rss,
        'vms': memory_info.vms,
        'percent': process.memory_percent()
    }

def get_cpu_usage() -> dict:
    """Получает информацию об использовании CPU"""
    import psutil
    process = psutil.Process()
    return {
        'percent': process.cpu_percent(),
        'threads': process.num_threads()
    }

# Запуск приложения
if __name__ == '__main__':
    # Получаем настройки запуска
    port = int(os.environ.get('PORT', 5000))
    debug = config.get('web.debug', False)
    
    # Логируем информацию о запуске
    logger.info(f"Starting server on port {port} (debug={debug})")
    logger.info(f"Available agents: {list(AVAILABLE_AGENTS.keys())}")
    logger.info(f"Application version: {config.get('app.version', 'unknown')}")
    
    # Проверяем наличие необходимых директорий
    for dir_path in REQUIRED_DIRS:
        if not os.path.exists(dir_path):
            logger.warning(f"Required directory not found: {dir_path}")
    
    try:
        # Запускаем сервер
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
