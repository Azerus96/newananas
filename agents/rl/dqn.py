import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.optimizers import Adam
from typing import List, Tuple, Dict, Any, Optional
import os
import time
from pathlib import Path

from agents.rl.base import RLAgent
from core.board import Board, Street
from core.card import Card
from utils.logger import get_logger

logger = get_logger(__name__)

class DQNAgent(RLAgent):
    """Deep Q-Network агент"""
    
    def __init__(self, name: str, state_size: int, action_size: int, config: dict, think_time: int = 30):
        super().__init__(name, state_size, action_size, config, think_time=think_time)
        
        # Дополнительные параметры DQN
        self.batch_size = config.get('batch_size', 32)
        self.target_update_freq = config.get('target_update_freq', 1000)
        self.steps = 0
        
        # Создаем основную и целевую сети
        self.model = self._build_model()
        self.target_model = self._build_model()
        self.update_target_model()

    def _build_model(self):
        """Создает нейронную сеть для DQN"""
        model = Sequential([
            Dense(256, input_dim=self.state_size, activation='relu'),
            Dropout(0.2),
            Dense(256, activation='relu'),
            Dropout(0.2),
            Dense(128, activation='relu'),
            Dense(self.action_size, activation='linear')
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=self.learning_rate),
            loss='mse'
        )
        return model

    @classmethod
    def load_latest(cls, name: str = "DQN", state_size: int = None, 
                   action_size: int = None, config: dict = None,
                   think_time: int = 30):
        """Загружает последнюю сохраненную модель DQN"""
        try:
            # Определяем директорию моделей DQN
            model_dir = Path("models") / "dqn"
            if not model_dir.exists():
                model_dir.mkdir(parents=True)

            # Ищем последний чекпоинт
            checkpoints = list(model_dir.glob("*.h5"))
            if not checkpoints:
                logger.warning("No saved DQN models found")
                if not all([state_size, action_size, config]):
                    raise ValueError("Need state_size, action_size and config for new model")
                return cls(name, state_size, action_size, config, think_time=think_time)

            # Находим самую свежую модель
            latest_model = max(checkpoints, key=lambda p: p.stat().st_mtime)
            
            # Загружаем конфигурацию
            config_path = latest_model.with_suffix('.json')
            if config_path.exists():
                import json
                with open(config_path, 'r') as f:
                    saved_config = json.load(f)
                    state_size = saved_config.get('state_size')
                    action_size = saved_config.get('action_size')
                    config = saved_config.get('config', {})
                    think_time = saved_config.get('think_time', think_time)

            # Создаем и загружаем агента
            agent = cls(name, state_size, action_size, config, think_time=think_time)
            agent.load(str(latest_model))
            
            logger.info(f"Loaded DQN model: {latest_model}")
            return agent

        except Exception as e:
            logger.error(f"Error loading DQN model: {e}")
            if not all([state_size, action_size, config]):
                raise ValueError("Need state_size, action_size and config for new model")
            return cls(name, state_size, action_size, config, think_time=think_time)
        
    def encode_state(self, board: Board, cards: List[Card], 
                    opponent_board: Board) -> np.ndarray:
        """
        Кодирует состояние игры в вектор признаков.
        Включает:
        - Карты на каждой улице
        - Карты в руке
        - Карты противника (если видны)
        - Доступные улицы
        """
        # Кодируем карты на улицах
        front_cards = self._encode_cards(board.front.cards, 3)
        middle_cards = self._encode_cards(board.middle.cards, 5)
        back_cards = self._encode_cards(board.back.cards, 5)
        
        # Кодируем карты в руке
        hand_cards = self._encode_cards(cards, len(cards))
        
        # Кодируем доступные улицы
        free_streets = np.array([
            1 if street in board.get_free_streets() else 0
            for street in Street
        ])
        
        # Объединяем все признаки
        state = np.concatenate([
            front_cards,
            middle_cards,
            back_cards,
            hand_cards,
            free_streets
        ])
        
        return state
        
    def _encode_cards(self, cards: List[Card], max_cards: int) -> np.ndarray:
        """Кодирует список карт в бинарный вектор"""
        # 52 бита для каждой карты (1 если карта присутствует)
        encoding = np.zeros(52)
        
        for card in cards:
            # Индекс карты = ранг * 4 + масть
            idx = (card.rank.value - 2) * 4 + card.suit.value - 1
            encoding[idx] = 1
            
        # Дополняем нулями до максимального количества карт
        padding = np.zeros(52 * (max_cards - len(cards)))
        return np.concatenate([encoding, padding])

    def choose_move(self, board: Board, cards: List[Card],
                   legal_moves: List[Tuple[Card, Street]],
                   opponent_board: Board = None,
                   think_time: Optional[int] = None) -> Tuple[Card, Street]:
        """Выбирает действие с помощью epsilon-greedy стратегии"""
        # Используем переданное время или значение по умолчанию
        current_think_time = think_time or self.think_time
        
        start_time = time.time()
        
        state = self.encode_state(board, cards, opponent_board)
        
        if np.random.random() <= self.epsilon:
            # Случайное действие
            return np.random.choice(legal_moves)
            
        # Жадное действие с учетом времени
        q_values = self.model.predict(
            state.reshape(1, -1),
            timeout=current_think_time
        )[0]
        
        legal_actions = self._get_legal_action_mask(legal_moves)
        q_values = q_values * legal_actions
        
        # Проверяем время
        elapsed_time = time.time() - start_time
        if elapsed_time > current_think_time:
            logger.warning(f"Think time exceeded: {elapsed_time:.2f}s > {current_think_time}s")
        
        best_action_idx = np.argmax(q_values)
        return legal_moves[best_action_idx]

    def update_target_model(self):
        """Обновляет веса целевой сети"""
        self.target_model.set_weights(self.model.get_weights())

    def replay(self, batch_size: int) -> Dict[str, float]:
        """Обучает модель на батче из памяти"""
        if len(self.memory) < batch_size:
            return {}
            
        # Выбираем случайный батч из памяти
        indices = np.random.choice(len(self.memory), batch_size, replace=False)
        batch = [self.memory[i] for i in indices]
        
        states = np.array([x[0] for x in batch])
        actions = np.array([x[1] for x in batch])
        rewards = np.array([x[2] for x in batch])
        next_states = np.array([x[3] for x in batch])
        dones = np.array([x[4] for x in batch])
        
        # Получаем предсказания для текущих состояний
        targets = self.model.predict(states)
        
        # Получаем Q-значения следующих состояний от целевой сети
        next_q_values = self.target_model.predict(next_states)
        
        # Обновляем целевые значения
        for i in range(batch_size):
            if dones[i]:
                targets[i][actions[i]] = rewards[i]
            else:
                targets[i][actions[i]] = rewards[i] + self.gamma * np.max(next_q_values[i])
                
        # Обучаем модель
        history = self.model.fit(states, targets, epochs=1, verbose=0)
        
        # Обновляем epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
            
        # Обновляем целевую сеть при необходимости
        self.steps += 1
        if self.steps % self.target_update_freq == 0:
            self.update_target_model()
            
        return history.history

    def save(self, filepath: str) -> None:
        """Сохраняет модель и дополнительные данные"""
        # Сохраняем основную модель
        self.model.save(filepath + '_main.h5')
        # Сохраняем целевую модель
        self.target_model.save(filepath + '_target.h5')
        
        # Сохраняем метаданные
        metadata = {
            'epsilon': self.epsilon,
            'steps': self.steps,
            'state_size': self.state_size,
            'action_size': self.action_size,
            'config': self.config,
            'training_history': self.training_history,
            'think_time': self.think_time  # Добавляем think_time
        }
        
        with open(filepath + '_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=4)

    def load(self, filepath: str) -> None:
        """Загружает модель и дополнительные данные"""
        # Загружаем основную модель
        self.model.load_weights(filepath + '_main.h5')
        # Загружаем целевую модель
        self.target_model.load_weights(filepath + '_target.h5')
        
        # Загружаем метаданные
        try:
            with open(filepath + '_metadata.json', 'r') as f:
                metadata = json.load(f)
                self.epsilon = metadata.get('epsilon', self.epsilon_min)
                self.steps = metadata.get('steps', 0)
                self.training_history = metadata.get('training_history', [])
                self.think_time = metadata.get('think_time', self.think_time)  # Загружаем think_time
                self.config.update(metadata.get('config', {}))
        except FileNotFoundError:
            logger.warning(f"No metadata file found for {filepath}")

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает расширенную статистику агента"""
        base_stats = super().get_stats()
        dqn_stats = {
            'steps': self.steps,
            'target_update_freq': self.target_update_freq,
            'batch_size': self.batch_size,
            'model_summary': str(self.model.summary()),
            'latest_losses': self.training_history[-10:] if self.training_history else [],
            'think_time': self.think_time  # Добавляем think_time в статистику
        }
        return {**base_stats, **dqn_stats}
