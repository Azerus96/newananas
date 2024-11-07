from abc import abstractmethod
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from pathlib import Path
import os
import json
from datetime import datetime

from agents.base import BaseAgent
from core.card import Card
from core.board import Board, Street
from utils.logger import get_logger

logger = get_logger(__name__)

class RLAgent(BaseAgent):
    """Базовый класс для RL агентов"""
    
    def __init__(self, name: str, state_size: int, action_size: int, config: dict, think_time: int = 30):
        super().__init__(name, think_time=think_time)  # Передаем think_time в родительский класс
        self.state_size = state_size
        self.action_size = action_size
        self.config = config
        
        # Параметры обучения
        self.gamma = config.get('gamma', 0.99)
        self.learning_rate = config.get('learning_rate', 0.001)
        self.epsilon = config.get('epsilon_start', 1.0)
        self.epsilon_min = config.get('epsilon_end', 0.01)
        self.epsilon_decay = config.get('epsilon_decay', 0.995)
        
        # Память для experience replay
        self.memory = []
        self.max_memory_size = config.get('memory_size', 10000)
        
        self.model = self._build_model()
        self.training_history = []

    @classmethod
    def load_latest(cls, name: str, state_size: int, action_size: int, config: dict, think_time: int = 30):
        """Загружает последнюю сохраненную модель агента"""
        agent = cls(name, state_size, action_size, config, think_time=think_time)  # Передаем think_time
        
        try:
            # Определяем директорию с моделями для конкретного типа агента
            model_dir = Path("models") / cls.__name__.lower()
            if not model_dir.exists():
                model_dir.mkdir(parents=True)
                
            # Ищем последний чекпоинт
            checkpoints = list(model_dir.glob("*.h5"))
            if not checkpoints:
                logger.warning(f"No saved models found for {cls.__name__}")
                return agent
                
            # Находим самую свежую модель
            latest_model = max(checkpoints, key=lambda p: p.stat().st_mtime)
            
            # Загружаем модель
            agent.load(str(latest_model))
            
            # Пытаемся загрузить метаданные
            meta_path = latest_model.with_suffix('.json')
            if meta_path.exists():
                with open(meta_path, 'r') as f:
                    metadata = json.load(f)
                    agent.epsilon = metadata.get('epsilon', agent.epsilon_min)
                    agent.training_history = metadata.get('training_history', [])
                    agent.think_time = metadata.get('think_time', think_time)  # Загружаем think_time
            
            logger.info(f"Loaded model: {latest_model}")
            return agent
            
        except Exception as e:
            logger.error(f"Error loading model for {cls.__name__}: {e}")
            return agent

    @abstractmethod
    def _build_model(self):
        """Создает и возвращает модель"""
        pass
        
    @abstractmethod
    def encode_state(self, board: Board, cards: List[Card], 
                    opponent_board: Board) -> np.ndarray:
        """Кодирует состояние игры в вектор"""
        pass
        
    def choose_move(self, board: Board, cards: List[Card],
                   legal_moves: List[Tuple[Card, Street]],
                   opponent_board: Board = None,
                   think_time: Optional[int] = None) -> Tuple[Card, Street]:
        """Выбирает действие с помощью epsilon-greedy стратегии"""
        # Используем переданное время или значение по умолчанию
        current_think_time = think_time or self.think_time
        
        state = self.encode_state(board, cards, opponent_board)
        
        if np.random.random() <= self.epsilon:
            # Случайное действие
            return np.random.choice(legal_moves)
            
        # Жадное действие с учетом времени на размышление
        start_time = time.time()
        q_values = self.model.predict(state.reshape(1, -1), timeout=current_think_time)[0]
        legal_actions = self._get_legal_action_mask(legal_moves)
        q_values = q_values * legal_actions
        
        # Проверяем время
        elapsed_time = time.time() - start_time
        if elapsed_time > current_think_time:
            self.logger.warning(f"Think time exceeded: {elapsed_time:.2f}s > {current_think_time}s")
        
        best_action_idx = np.argmax(q_values)
        return legal_moves[best_action_idx]
        
    def _get_legal_action_mask(self, legal_moves: List[Tuple[Card, Street]]) -> np.ndarray:
        """Создает маску для допустимых действий"""
        mask = np.zeros(self.action_size)
        for i, move in enumerate(legal_moves):
            mask[i] = 1
        return mask
        
    def remember(self, state: np.ndarray, action: int, reward: float, 
                next_state: np.ndarray, done: bool) -> None:
        """Сохраняет опыт в памяти"""
        if len(self.memory) >= self.max_memory_size:
            self.memory.pop(0)
        self.memory.append((state, action, reward, next_state, done))
        
    def save(self, filepath: str) -> None:
        """Сохраняет модель и метаданные"""
        # Сохраняем модель
        self.model.save(filepath + '.h5')
        
        # Сохраняем метаданные
        metadata = {
            'epsilon': self.epsilon,
            'training_history': self.training_history,
            'timestamp': datetime.now().isoformat(),
            'config': self.config,
            'think_time': self.think_time  # Сохраняем think_time
        }
        
        with open(filepath + '.json', 'w') as f:
            json.dump(metadata, f, indent=4)
            
    def load(self, filepath: str) -> None:
        """Загружает модель и метаданные"""
        # Загружаем модель
        self.model.load_weights(filepath + '.h5')
        
        # Загружаем метаданные
        try:
            with open(filepath + '.json', 'r') as f:
                metadata = json.load(f)
                self.epsilon = metadata.get('epsilon', self.epsilon_min)
                self.training_history = metadata.get('training_history', [])
                self.config.update(metadata.get('config', {}))
                self.think_time = metadata.get('think_time', self.think_time)  # Загружаем think_time
        except FileNotFoundError:
            logger.warning(f"No metadata file found for {filepath}")

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает текущую статистику агента"""
        base_stats = super().get_stats()
        rl_stats = {
            'epsilon': self.epsilon,
            'memory_size': len(self.memory),
            'training_history': self.training_history,
            'model_summary': str(self.model.summary()),
            'learning_rate': self.learning_rate,
            'gamma': self.gamma,
            'think_time': self.think_time  # Добавляем think_time в статистику
        }
        return {**base_stats, **rl_stats}
