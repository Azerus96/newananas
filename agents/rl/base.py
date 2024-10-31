from abc import abstractmethod
from typing import List, Tuple, Dict, Any
import numpy as np

from ..base import BaseAgent
from ...core.card import Card
from ...core.board import Board, Street
from ...utils.logger import get_logger

logger = get_logger(__name__)

class RLAgent(BaseAgent):
    """Базовый класс для RL агентов"""
    
    def __init__(self, name: str, state_size: int, action_size: int, config: dict):
        super().__init__(name)
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
                   opponent_board: Board = None) -> Tuple[Card, Street]:
        """Выбирает действие с помощью epsilon-greedy стратегии"""
        state = self.encode_state(board, cards, opponent_board)
        
        if np.random.random() <= self.epsilon:
            # Случайное действие
            return np.random.choice(legal_moves)
            
        # Жадное действие
        q_values = self.model.predict(state.reshape(1, -1))[0]
        legal_actions = self._get_legal_action_mask(legal_moves)
        q_values = q_values * legal_actions
        
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
        
    def replay(self, batch_size: int) -> Dict[str, float]:
        """Обучает модель на батче из памяти"""
        if len(self.memory) < batch_size:
            return {}
            
        batch = np.random.choice(self.memory, batch_size, replace=False)
        states = np.array([x[0] for x in batch])
        actions = np.array([x[1] for x in batch])
        rewards = np.array([x[2] for x in batch])
        next_states = np.array([x[3] for x in batch])
        dones = np.array([x[4] for x in batch])
        
        # Обучение модели
        targets = self.model.predict(states)
        next_q_values = self.model.predict(next_states)
        
        for i in range(batch_size):
            if dones[i]:
                targets[i][actions[i]] = rewards[i]
            else:
                targets[i][actions[i]] = rewards[i] + self.gamma * np.max(next_q_values[i])
                
        history = self.model.fit(states, targets, epochs=1, verbose=0)
        
        # Обновление epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
            
        return history.history
        
    def save(self, filepath: str) -> None:
        """Сохраняет модель"""
        self.model.save(filepath)
        
    def load(self, filepath: str) -> None:
        """Загружает модель"""
        self.model.load_weights(filepath)
