import sys
import os
from pathlib import Path
import tensorflow as tf
from datetime import datetime
from prometheus_client import Counter, Histogram
from logging.config import dictConfig
from flask import Flask, render_template, jsonify, request, g, session
from flask_socketio import SocketIO, emit
from typing import Optional, Dict
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

# Создаем необходимые директории из конфигурации
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

# Доступные агенты
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
    SECRET_KEY=config.get('web.secret_key', os.urandom(24))
)

socketio = SocketIO(app, cors_allowed_origins="*")
app_state = AppState()
analytics_manager = AnalyticsManager()

@app.before_request
def before_request():
    """Выполняется перед каждым запросом"""
    g.start_time = datetime.now()
    REQUESTS.labels(method=request.method, endpoint=request.endpoint).inc()
    app.logger.info(f'Request: {request.method} {request.url}')
    
    # Инициализация сессии если её нет
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())

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
    return render_template('index.html', 
                         is_mobile=request.user_agent.platform in ['android', 'iphone', 'ipad'])

@app.route('/mobile')
def mobile():
    """Мобильная версия"""
    return render_template('mobile.html')

@app.route('/training')
def training():
    """Отображает страницу режима тренировки"""
    return render_template('training.html',
                         is_mobile=request.user_agent.platform in ['android', 'iphone', 'ipad'])

@app.route('/api/statistics')
def get_statistics():
    """Возвращает глобальную статистику"""
    try:
        stats = analytics_manager.get_global_statistics()
        return jsonify(stats)
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
        
        # Создаем уникальный ID для игры
        game_id = str(uuid.uuid4())
        
        # Настройки игры
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
            
            # Создаем агента с учетом параметров
            if agent_type == 'random':
                agent = RandomAgent.load_latest(
                    name=f"{agent_type}_opponent_{i}",
                    think_time=game_config['think_time']
                )
            else:
                agent_config = config.get_agent_config(agent_type)
                state_size = config.get('state.size')
                action_size = config.get('action.size')
                
                agent = agent_class.load_latest(
                    name=f"{agent_type}_opponent_{i}",
                    state_size=state_size,
                    action_size=action_size,
                    config=agent_config,
                    think_time=game_config['think_time']
                ) if use_latest else agent_class(
                    name=f"{agent_type}_opponent_{i}",
                    state_size=state_size,
                    action_size=action_size,
                    config=agent_config,
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

@app.route('/api/training/start', methods=['POST'])
def start_training():
    """Начинает новую сессию тренировки"""
    try:
        data = request.get_json()
        
        # Создаем ID сессии
        session_id = str(uuid.uuid4())
        
        training_config = TrainingConfig(
            fantasy_mode=data.get('fantasy_mode', config.get('game.fantasy_mode')),
            progressive_fantasy=data.get('progressive_fantasy', config.get('game.progressive_fantasy')),
            time_limit=data.get('time_limit', config.get('game.think_time'))
        )
        
        # Создаем сессию
        training_session = app_state.create_training_session(session_id, training_config)
        
        # Сохраняем ID сессии
        session['training_session_id'] = session_id
        
        GAME_METRICS.labels(type='training_start').inc()
        
        return jsonify({
            'status': 'ok',
            'session_id': session_id
        })
        
    except Exception as e:
        logger.error(f"Error starting training session: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/training/distribute', methods=['POST'])
def distribute_cards():
    """Распределяет карты в тренировочном режиме"""
    try:
        session_id = session.get('training_session_id')
        if not session_id:
            return jsonify({'error': 'No active training session'}), 400
            
        training_session = app_state.get_training_session(session_id)
        if not training_session:
            return jsonify({'error': 'Training session not found'}), 404

        data = request.get_json()
        logger.info(f"Distributing cards with data: {data}")
        
        # Преобразуем данные карт в объекты
        from core.card import Card
        input_cards = [Card(rank=c['rank'], suit=c['suit']) for c in data.get('input_cards', [])]
        removed_cards = [Card(rank=c['rank'], suit=c['suit']) for c in data.get('removed_cards', [])]
        
        # Распределяем карты
        move_result = training_session.make_move(
            input_cards=input_cards,
            removed_cards=removed_cards
        )
        
        # Отправляем результат через WebSocket
        socketio.emit('training_move', move_result, room=session['user_id'])
        
        return jsonify({
            'status': 'ok',
            'move': move_result,
            'statistics': training_session.get_statistics()
        })
        
    except Exception as e:
        logger.error(f"Error in training mode: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/training/stats')
def get_training_stats():
    """Получает статистику тренировки"""
    try:
        session_id = session.get('training_session_id')
        if not session_id:
            return jsonify({'error': 'No active training session'}), 400
            
        training_session = app_state.get_training_session(session_id)
        if not training_session:
            return jsonify({'error': 'Training session not found'}), 404
            
        stats = training_session.get_statistics()
        logger.info(f"Retrieved training stats: {stats}")
        return jsonify({
            'status': 'ok',
            'statistics': stats
        })
    except Exception as e:
        logger.error(f"Error getting training stats: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/game/state')
def get_game_state():
    """Получает текущее состояние игры"""
    try:
        game_id = session.get('current_game_id')
        if not game_id:
            return jsonify({'error': 'No active game'}), 400
            
        game = app_state.get_game(game_id)
        if not game:
            return jsonify({'error': 'Game not found'}), 404
            
        game_state = game.get_state()
        logger.info(f"Retrieved game state: {game_state}")
        return jsonify({
            'status': 'ok',
            'game_state': game_state
        })
    except Exception as e:
        logger.error(f"Error getting game state: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/game/ai_vs_ai', methods=['POST'])
def create_ai_vs_ai_game():
    """Создает игру AI против AI"""
    try:
        data = request.get_json()
        game_id = str(uuid.uuid4())
        
        # Создаем агентов
        agent1_type = data.get('agent1', 'random')
        agent2_type = data.get('agent2', 'random')
        think_time = data.get('think_time', 30)
        
        agents = []
        for agent_type in [agent1_type, agent2_type]:
            if agent_type not in AVAILABLE_AGENTS:
                return jsonify({'error': f'Unknown agent type: {agent_type}'}), 400
                
            agent_class = AVAILABLE_AGENTS[agent_type]
            agent = agent_class.load_latest(
                name=f"{agent_type}_ai_vs_ai",
                think_time=think_time
            )
            agents.append(agent)
            
        # Создаем игру
        game_config = {
            'players': 2,
            'fantasy_mode': FantasyMode.NORMAL,
            'think_time': think_time,
            'agents': agents
        }
        
        game = app_state.create_game(game_id, game_config)
        game.start()
        
        # Сохраняем ID игры
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

# WebSocket события
@socketio.on('connect')
def handle_connect():
    """Обработка подключения WebSocket"""
    WEBSOCKET_CONNECTIONS.inc()
    logger.info(f"WebSocket connected: {request.sid}")
    
    # Присоединяем клиента к комнате
    room = session.get('user_id')
    if room:
        socketio.join_room(room)
    
    # Отправляем текущее состояние если есть активная игра
    game_id = session.get('current_game_id')
    if game_id:
        game = app_state.get_game(game_id)
        if game:
            emit('game_state', game.get_state())

@socketio.on('disconnect')
def handle_disconnect():
    """Обработка отключения WebSocket"""
    logger.info(f"WebSocket disconnected: {request.sid}")
    
    # Очищаем состояние если нужно
    room = session.get('user_id')
    if room:
        socketio.leave_room(room)

if __name__ == '__main__':
    socketio.run(
        app,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=config.get('web.debug', False)
    )
