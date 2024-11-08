# utils/app_state.py

from typing import Dict, Optional, List
from threading import Lock
from datetime import datetime

from core.game import Game
from training.training_mode import TrainingSession, TrainingConfig
from analytics.analytics_manager import AnalyticsManager
from utils.logger import get_logger

logger = get_logger(__name__)

class AppState:
    """Управляет глобальным состоянием приложения"""
    
    def __init__(self):
        self._training_sessions: Dict[str, TrainingSession] = {}
        self._games: Dict[str, Game] = {}
        self._analytics = AnalyticsManager()
        self._lock = Lock()
        self._active_users: Dict[str, datetime] = {}
        
    def get_training_session(self, session_id: str) -> Optional[TrainingSession]:
        """Получает сессию тренировки по ID"""
        with self._lock:
            return self._training_sessions.get(session_id)
    
    def create_training_session(self, session_id: str, config: TrainingConfig) -> TrainingSession:
        """Создает новую сессию тренировки"""
        with self._lock:
            if session_id in self._training_sessions:
                raise ValueError(f"Session {session_id} already exists")
                
            session = TrainingSession(config)
            self._training_sessions[session_id] = session
            logger.info(f"Created training session: {session_id}")
            return session
    
    def remove_training_session(self, session_id: str):
        """Удаляет сессию тренировки"""
        with self._lock:
            if session_id in self._training_sessions:
                session = self._training_sessions[session_id]
                session.save_progress()
                del self._training_sessions[session_id]
                logger.info(f"Removed training session: {session_id}")
    
    def get_game(self, game_id: str) -> Optional[Game]:
        """Получает игру по ID"""
        with self._lock:
            return self._games.get(game_id)
    
    def create_game(self, game_id: str, config: dict) -> Game:
        """Создает новую игру"""
        with self._lock:
            if game_id in self._games:
                raise ValueError(f"Game {game_id} already exists")
            
            game = Game(**config)
            self._games[game_id] = game
            logger.info(f"Created game: {game_id}")
            return game
    
    def remove_game(self, game_id: str):
        """Удаляет игру"""
        with self._lock:
            if game_id in self._games:
                game = self._games[game_id]
                self._analytics.save_game_stats(game)
                del self._games[game_id]
                logger.info(f"Removed game: {game_id}")
    
    def get_active_games(self) -> List[Game]:
        """Возвращает список активных игр"""
        with self._lock:
            return list(self._games.values())
    
    def get_active_training_sessions(self) -> List[TrainingSession]:
        """Возвращает список активных тренировочных сессий"""
        with self._lock:
            return list(self._training_sessions.values())
    
    def register_user_activity(self, user_id: str):
        """Регистрирует активность пользователя"""
        with self._lock:
            self._active_users[user_id] = datetime.now()
    
    def cleanup_inactive_sessions(self, timeout_minutes: int = 30):
        """Очищает неактивные сессии"""
        with self._lock:
            current_time = datetime.now()
            inactive_users = []
            
            for user_id, last_activity in self._active_users.items():
                if (current_time - last_activity).total_seconds() > timeout_minutes * 60:
                    inactive_users.append(user_id)
                    
            for user_id in inactive_users:
                self._cleanup_user_sessions(user_id)
                del self._active_users[user_id]
                logger.info(f"Cleaned up inactive user: {user_id}")
    
    def _cleanup_user_sessions(self, user_id: str):
        """Очищает все сессии пользователя"""
        # Очистка тренировочных сессий
        sessions_to_remove = [
            session_id for session_id, session in self._training_sessions.items()
            if session.user_id == user_id
        ]
        for session_id in sessions_to_remove:
            self.remove_training_session(session_id)
            
        # Очистка игр
        games_to_remove = [
            game_id for game_id, game in self._games.items()
            if game.user_id == user_id
        ]
        for game_id in games_to_remove:
            self.remove_game(game_id)
    
    def save_state(self):
        """Сохраняет состояние приложения"""
        with self._lock:
            # Сохранение тренировочных сессий
            for session in self._training_sessions.values():
                session.save_progress()
                
            # Сохранение статистики игр
            for game in self._games.values():
                self._analytics.save_game_stats(game)
                
            logger.info("Application state saved")
    
    def load_state(self):
        """Загружает состояние приложения"""
        # Здесь может быть код для загрузки сохраненного состояния
        pass
    
    def get_statistics(self) -> dict:
        """Возвращает общую статистику"""
        return self._analytics.get_global_statistics()
    
    def __str__(self) -> str:
        return f"AppState(games={len(self._games)}, training_sessions={len(self._training_sessions)})"
