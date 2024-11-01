# utils/app_state.py

from typing import Dict, Optional
from threading import Lock

class AppState:
    """Управляет глобальным состоянием приложения"""
    
    def __init__(self):
        self._training_sessions: Dict[str, TrainingSession] = {}
        self._games: Dict[str, Game] = {}
        self._lock = Lock()
        
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
            return session
    
    def remove_training_session(self, session_id: str):
        """Удаляет сессию тренировки"""
        with self._lock:
            if session_id in self._training_sessions:
                session = self._training_sessions[session_id]
                session.save_progress()
                del self._training_sessions[session_id]
    
    def get_game(self, game_id: str) -> Optional[Game]:
        """Получает игру по ID"""
        with self._lock:
            return self._games.get(game_id)
    
    def create_game(self
