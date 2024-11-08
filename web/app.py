import sys
import os
from pathlib import Path
import tensorflow as tf
from datetime import datetime
from prometheus_client import Counter, Histogram
from logging.config import dictConfig
from flask import Flask, render_template, jsonify, request, g, session, redirect, url_for
from flask_socketio import SocketIO, emit
from typing import Optional, Dict, Any
import uuid

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

# Доступные агенты (убрано слово "Agent" из названий)
AVAILABLE_AGENTS = {
    'random': RandomAgent,
    'dqn': DQNAgent,
    'a3c': A3CAgent,
    'ppo': PPOAgent
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

socketio = SocketIO(app, cors_allowed_origins="*")
app_state = AppState()
analytics_manager = AnalyticsManager()

@app.before_request
def before_request():
    """Выполняется перед каждым запросом"""
    g.start_time = datetime.now()
    REQUESTS.labels(method=request.method, endpoint=request.endpoint).inc()
    logger.info(f'Request: {request.method} {request.url}')
    
    # Инициализация сессии если её нет
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
        session.permanent = True

@app.after_request
def after_request(response):
    """Выполняется после каждого запроса"""
    if hasattr(g, 'start_time'):
        elapsed = datetime.now() - g.start_time
        RESPONSE_TIME.observe(elapsed.total_seconds())
        logger.info(f'Response: {response.status} - {elapsed.total_seconds():.3f}s')
    return response

@app.route('/')
def index():
    """Отображает главную страницу"""
    is_mobile = request.user_agent.platform in ['android', 'iphone', 'ipad']
    return render_template('index.html', is_mobile=is_mobile)

@app.route('/mobile')
def mobile():
    """Мобильная версия"""
    return render_template('mobile.html')

@app.route('/training')
def training():
    """Отображает страницу режима тренировки"""
    is_mobile = request.user_agent.platform in ['android', 'iphone', 'ipad']
    return render_template('training.html', is_mobile=is_mobile)

@app.route('/api/statistics')
def get_statistics():
    """Возвращает глобальную статистику"""
    try:
        stats = analytics_manager.get_global_statistics()
        return jsonify({
            'status': 'ok',
            'statistics': stats
        })
    except Exception as e:
        logger.error(f"Error getting statistics: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/agents')
def get_available_agents():
    """Возвращает список доступных агентов"""
    try:
        agents_list = [
            {
                'id': agent_id,
                'name': agent_class.__name__.replace('Agent', ''),
                'description': agent_class.__doc__
            }
            for agent_id, agent_class in AVAILABLE_AGENTS.items()
        ]
        logger.info(f"Returning available agents: {agents_list}")
        return jsonify({'agents': agents_list})
    except Exception as e:
        logger.error(f"Error getting agents list: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/new_game', methods=['POST'])
def new_game():
    """Создает новую игру"""
    try:
        data = request.get_json()
        logger.info(f"Creating new game with data: {data}")
        
        game_id = str(uuid.uuid4())
        
        game_config = {
            'players': data.get('players', 2),
            'fantasy_mode': (FantasyMode.PROGRESSIVE 
                           if data.get('progressive_fantasy') 
                           else FantasyMode.NORMAL),
            'think_time': data.get('aiThinkTime', 30),
            'agents': []
        }
        
        # Создаем AI агентов
        for i in range(game_config['players'] - 1):
            agent_type = data.get(f'agent_{i}', 'random')
            use_latest = data.get(f'use_latest_{i}', True)
            
            if agent_type not in AVAILABLE_AGENTS:
                return jsonify({
                    'error': f'Unknown agent type: {agent_type}'
                }), 400
                
            agent_class = AVAILABLE_AGENTS[agent_type]
            agent_name = f"{agent_type}_{i+1}"
            
            # Создаем агента с учетом параметров
            agent = agent_class.load_latest(
                name=agent_name,
                think_time=game_config['think_time']
            ) if use_latest else agent_class(
                name=agent_name,
                think_time=game_config['think_time']
            )
                
            game_config['agents'].append(agent)
        
        # Создаем игру
        game = app_state.create_game(game_id, game_config)
        game.start()
        
        # Сохраняем ID игры в сессии
        session['current_game_id'] = game_id
        
        # Отправляем начальное состояние через WebSocket
        socketio.emit('game_state', game.get_state(), room=session['user_id'])
        
        GAME_METRICS.labels(type='new_game').inc()
        
        return jsonify({
            'status': 'ok',
            'game_id': game_id,
            'game_state': game.get_state()
        })
        
    except Exception as e:
        logger.error(f"Error creating new game: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/make_move', methods=['POST'])
def make_move():
    """Выполняет ход в игре"""
    try:
        game_id = session.get('current_game_id')
        if not game_id:
            return jsonify({'error': 'No active game'}), 400
            
        game = app_state.get_game(game_id)
        if not game:
            return jsonify({'error': 'Game not found'}), 404
            
        data = request.get_json()
        logger.info(f"Making move with data: {data}")
        
        card_data = data.get('card')
        street = data.get('street')
        
        # Создаем объект карты из данных
        from core.card import Card
        card = Card(rank=card_data['rank'], suit=card_data['suit'])
        
        # Делаем ход
        success = game.make_move(1, card, street)
        if not success:
            return jsonify({'error': 'Invalid move'}), 400

        # Обновляем состояние через WebSocket
        socketio.emit('game_state', game.get_state(), room=session['user_id'])

        # Ход AI если игра не закончена
        if not game.is_game_over():
            # Показываем что AI думает
            socketio.emit('ai_thinking', {'player': game.current_player}, room=session['user_id'])
            
            # Получаем и делаем ход AI
            ai_move = game.get_ai_move()
            game.make_move(game.current_player, *ai_move)
            
            # Отправляем обновленное состояние
            socketio.emit('game_state', game.get_state(), room=session['user_id'])
            
        # Проверяем окончание игры
        if game.is_game_over():
            result = game.get_result()
            socketio.emit('game_over', result, room=session['user_id'])
            app_state.remove_game(game_id)
            session.pop('current_game_id', None)

        GAME_METRICS.labels(type='move').inc()
        
        return jsonify({
            'status': 'ok',
            'game_state': game.get_state()
        })

    except Exception as e:
        logger.error(f"Error making move: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai_vs_ai', methods=['POST'])
def create_ai_vs_ai_game():
    """Создает игру AI против AI"""
    try:
        data = request.get_json()
        game_id = str(uuid.uuid4())
        
        agent1_type = data.get('agent1', 'random')
        agent2_type = data.get('agent2', 'random')
        think_time = data.get('think_time', 30)
        
        if agent1_type not in AVAILABLE_AGENTS or agent2_type not in AVAILABLE_AGENTS:
            return jsonify({'error': 'Invalid agent type'}), 400
        
        # Создаем агентов
        agent1 = AVAILABLE_AGENTS[agent1_type](
            name=f"{agent1_type}_1",
            think_time=think_time
        )
        agent2 = AVAILABLE_AGENTS[agent2_type](
            name=f"{agent2_type}_2",
            think_time=think_time
        )
        
        game_config = {
            'players': 2,
            'fantasy_mode': FantasyMode.NORMAL,
            'think_time': think_time,
            'agents': [agent1, agent2]
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
        
    except Exception as e:
        logger.error(f"Error creating AI vs AI game: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

def run_ai_vs_ai_game(game_id: str):
    """Запускает процесс игры AI против AI"""
    try:
        game = app_state.get_game(game_id)
        if not game:
            return
            
        while not game.is_game_over():
            # Получаем ход текущего AI
            ai_move = game.get_ai_move()
            
            # Делаем ход
            game.make_move(game.current_player, *ai_move)
            
            # Отправляем обновление состояния
            socketio.emit('game_state', game.get_state(), room=session['user_id'])
            
            # Небольшая задержка для визуализации
            socketio.sleep(1)
            
        # Игра закончена
        result = game.get_result()
        socketio.emit('game_over', result, room=session['user_id'])
        app_state.remove_game(game_id)
        
    except Exception as e:
        logger.error(f"Error in AI vs AI game: {e}", exc_info=True)
        socketio.emit('error', {'message': str(e)}, room=session['user_id'])

@app.route('/api/save_game_state', methods=['POST'])
def save_game_state():
    """Сохраняет состояние текущей игры"""
    try:
        game_id = session.get('current_game_id')
        if not game_id:
            return jsonify({'error': 'No active game'}), 400
            
        game = app_state.get_game(game_id)
        if not game:
            return jsonify({'error': 'Game not found'}), 404
            
        state = game.save_state()
        session['saved_game_state'] = state
        
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Error saving game state: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/load_game_state', methods=['POST'])
def load_game_state():
    """Загружает сохраненное состояние игры"""
    try:
        saved_state = session.get('saved_game_state')
        if not saved_state:
            return jsonify({'error': 'No saved game state'}), 400
            
        game_id = str(uuid.uuid4())
        game = app_state.create_game(game_id, saved_state['config'])
        game.load_state(saved_state)
        
        session['current_game_id'] = game_id
        
        return jsonify({
            'status': 'ok',
            'game_id': game_id,
            'game_state': game.get_state()
        })
        
    except Exception as e:
        logger.error(f"Error loading game state: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# WebSocket события
@socketio.on('connect')
def handle_connect():
    """Обработка подключения WebSocket"""
    WEBSOCKET_CONNECTIONS.inc()
    logger.info(f"WebSocket connected: {request.sid}")
    
    room = session.get('user_id')
    if room:
        socketio.join_room(room)
    
    game_id = session.get('current_game_id')
    if game_id:
        game = app_state.get_game(game_id)
        if game:
            emit('game_state', game.get_state())

@socketio.on('disconnect')
def handle_disconnect():
    """Обработка отключения WebSocket"""
    logger.info(f"WebSocket disconnected: {request.sid}")
    
    # Сохраняем состояние игры при отключении
    game_id = session.get('current_game_id')
    if game_id:
        game = app_state.get_game(game_id)
        if game:
            state = game.save_state()
            session['saved_game_state'] = state
    
    # Очищаем комнату
    room = session.get('user_id')
    if room:
        socketio.leave_room(room)

@app.errorhandler(404)
def not_found_error(error):
    """Обработка ошибки 404"""
    logger.warning(f"404 error: {request.url}")
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Обработка ошибки 500"""
    logger.error(f"500 error: {error}", exc_info=True)
    return jsonify({'error': 'Internal server error'}), 500

@app.route('/health')
def health_check():
    """Проверка здоровья приложения"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_games': len(app_state.get_active_games()),
        'active_training_sessions': len(app_state.get_active_training_sessions())
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = config.get('web.debug', False)
    
    logger.info(f"Starting server on port {port} (debug={debug})")
    
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=debug,
        use_reloader=debug
    )
