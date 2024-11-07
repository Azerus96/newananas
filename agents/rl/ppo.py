import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense
from tensorflow.keras.optimizers import Adam
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
import json
import time

from agents.rl.base import RLAgent
from utils.logger import get_logger
from core.board import Board, Street
from core.card import Card

logger = get_logger(__name__)

class PPOAgent(RLAgent):
    """Proximal Policy Optimization агент"""
    
    def __init__(self, name: str, state_size: int, action_size: int, config: dict, think_time: int = 30):
        super().__init__(name, state_size, action_size, config, think_time=think_time)
        
        # Параметры PPO
        self.clip_ratio = config.get('clip_ratio', 0.2)
        self.policy_epochs = config.get('policy_epochs', 10)
        self.value_epochs = config.get('value_epochs', 10)
        self.target_kl = config.get('target_kl', 0.01)
        self.value_loss_coef = config.get('value_loss_coef', 0.5)
        
        # Создаем отдельные модели для политики и значения
        self.policy_model = self._build_policy_model()
        self.value_model = self._build_value_model()
        
        # Счетчик шагов и обновлений
        self.steps = 0
        self.updates = 0

    @classmethod
    def load_latest(cls, name: str = "PPO", state_size: int = None, 
                   action_size: int = None, config: dict = None,
                   think_time: int = 30):
        """Загружает последнюю сохраненную модель PPO"""
        try:
            # Определяем директорию моделей PPO
            model_dir = Path("models") / "ppo"
            if not model_dir.exists():
                model_dir.mkdir(parents=True)

            # Ищем последний чекпоинт
            checkpoints = list(model_dir.glob("*_policy.h5"))  # Ищем по файлу политики
            if not checkpoints:
                logger.warning("No saved PPO models found")
                if not all([state_size, action_size, config]):
                    raise ValueError("Need state_size, action_size and config for new model")
                return cls(name, state_size, action_size, config, think_time=think_time)

            # Находим самую свежую модель
            latest_model = max(checkpoints, key=lambda p: p.stat().st_mtime)
            base_path = str(latest_model).replace('_policy.h5', '')
            
            # Загружаем конфигурацию
            config_path = Path(base_path + '_metadata.json')
            if config_path.exists():
                with open(config_path, 'r') as f:
                    saved_config = json.load(f)
                    state_size = saved_config.get('state_size')
                    action_size = saved_config.get('action_size')
                    config = saved_config.get('config', {})
                    think_time = saved_config.get('think_time', think_time)

            # Создаем и загружаем агента
            agent = cls(name, state_size, action_size, config, think_time=think_time)
            agent.load(base_path)
            
            logger.info(f"Loaded PPO model: {latest_model}")
            return agent

        except Exception as e:
            logger.error(f"Error loading PPO model: {e}")
            if not all([state_size, action_size, config]):
                raise ValueError("Need state_size, action_size and config for new model")
            return cls(name, state_size, action_size, config, think_time=think_time)
        
    def _build_policy_model(self):
        """Создает модель политики"""
        inputs = Input(shape=(self.state_size,))
        x = Dense(256, activation='relu')(inputs)
        x = Dense(256, activation='relu')(x)
        x = Dense(128, activation='relu')(x)
        outputs = Dense(self.action_size, activation='softmax')(x)
        
        model = Model(inputs=inputs, outputs=outputs)
        model.compile(optimizer=Adam(learning_rate=self.learning_rate))
        return model
        
    def _build_value_model(self):
        """Создает модель ценности"""
        inputs = Input(shape=(self.state_size,))
        x = Dense(256, activation='relu')(inputs)
        x = Dense(256, activation='relu')(x)
        x = Dense(128, activation='relu')(x)
        outputs = Dense(1, activation='linear')(x)
        
        model = Model(inputs=inputs, outputs=outputs)
        model.compile(optimizer=Adam(learning_rate=self.learning_rate), loss='mse')
        return model

    def encode_state(self, board: Board, cards: List[Card], 
                    opponent_board: Board) -> np.ndarray:
        """Кодирует состояние игры в вектор признаков"""
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
        encoding = np.zeros(52)
        for card in cards:
            idx = (card.rank.value - 2) * 4 + card.suit.value - 1
            encoding[idx] = 1
        padding = np.zeros(52 * (max_cards - len(cards)))
        return np.concatenate([encoding, padding])
        
    def choose_move(self, board: Board, cards: List[Card],
                   legal_moves: List[Tuple[Card, Street]],
                   opponent_board: Board = None,
                   think_time: Optional[int] = None) -> Tuple[Card, Street]:
        """Выбирает действие используя текущую политику"""
        # Используем переданное время или значение по умолчанию
        current_think_time = think_time or self.think_time
        
        start_time = time.time()
        
        state = self.encode_state(board, cards, opponent_board)
        policy = self.policy_model.predict(
            state.reshape(1, -1),
            timeout=current_think_time
        )[0]
        
        # Применяем маску легальных ходов
        legal_mask = self._get_legal_action_mask(legal_moves)
        masked_policy = policy * legal_mask
        
        # Нормализуем вероятности
        masked_policy = masked_policy / np.sum(masked_policy)
        
        # Проверяем время
        elapsed_time = time.time() - start_time
        if elapsed_time > current_think_time:
            logger.warning(f"Think time exceeded: {elapsed_time:.2f}s > {current_think_time}s")
        
        # Выбираем действие
        if np.random.random() < self.epsilon:
            action_idx = np.random.choice(len(legal_moves))
        else:
            action_idx = np.random.choice(
                self.action_size,
                p=masked_policy
            )
            
        return legal_moves[action_idx]

    def train_on_batch(self, states, actions, advantages, returns, old_policies):
        """Обучает модели на батче данных"""
        # Обучаем политику
        with tf.GradientTape() as tape:
            new_policies = self.policy_model(states)
            loss = self._compute_policy_loss(
                actions, advantages, old_policies, new_policies
            )
            
        grads = tape.gradient(loss, self.policy_model.trainable_variables)
        self.policy_model.optimizer.apply_gradients(
            zip(grads, self.policy_model.trainable_variables)
        )
        
        # Обучаем модель ценности
        value_loss = self.value_model.train_on_batch(states, returns)
        
        # Обновляем счетчики
        self.steps += len(states)
        self.updates += 1
        
        return {
            'policy_loss': loss.numpy(),
            'value_loss': value_loss,
            'steps': self.steps,
            'updates': self.updates
        }
        
    def _compute_policy_loss(self, actions, advantages, old_policies, new_policies):
        """Вычисляет функцию потерь PPO"""
        actions_one_hot = tf.one_hot(actions, self.action_size)
        
        # Вероятности действий
        old_probs = tf.reduce_sum(actions_one_hot * old_policies, axis=1)
        new_probs = tf.reduce_sum(actions_one_hot * new_policies, axis=1)
        
        # Отношение новой и старой политик
        ratio = new_probs / (old_probs + 1e-10)
        
        # Clipped surrogate objective
        clipped_ratio = tf.clip_by_value(
            ratio,
            1 - self.clip_ratio,
            1 + self.clip_ratio
        )
        
        surrogate1 = ratio * advantages
        surrogate2 = clipped_ratio * advantages
        
        # Добавляем энтропию для исследования
        entropy = -tf.reduce_mean(
            tf.reduce_sum(new_policies * tf.math.log(new_policies + 1e-10), axis=1)
        )
        
        return -tf.reduce_mean(tf.minimum(surrogate1, surrogate2)) - 0.01 * entropy

    def save(self, filepath: str) -> None:
        """Сохраняет модели и метаданные"""
        # Сохраняем модели
        self.policy_model.save(filepath + '_policy.h5')
        self.value_model.save(filepath + '_value.h5')
        
        # Сохраняем метаданные
        metadata = {
            'epsilon': self.epsilon,
            'steps': self.steps,
            'updates': self.updates,
            'state_size': self.state_size,
            'action_size': self.action_size,
            'config': self.config,
            'training_history': self.training_history,
            'think_time': self.think_time  # Добавляем think_time
        }
        
        with open(filepath + '_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=4)

    def load(self, filepath: str) -> None:
        """Загружает модели и метаданные"""
        # Загружаем модели
        self.policy_model = tf.keras.models.load_model(filepath + '_policy.h5')
        self.value_model = tf.keras.models.load_model(filepath + '_value.h5')
        
        # Загружаем метаданные
        try:
            with open(filepath + '_metadata.json', 'r') as f:
                metadata = json.load(f)
                self.epsilon = metadata.get('epsilon', self.epsilon_min)
                self.steps = metadata.get('steps', 0)
                self.updates = metadata.get('updates', 0)
                self.training_history = metadata.get('training_history', [])
                self.think_time = metadata.get('think_time', self.think_time)  # Загружаем think_time
                self.config.update(metadata.get('config', {}))
        except FileNotFoundError:
            logger.warning(f"No metadata file found for {filepath}")

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает расширенную статистику агента"""
        base_stats = super().get_stats()
        ppo_stats = {
            'steps': self.steps,
            'updates': self.updates,
            'clip_ratio': self.clip_ratio,
            'policy_epochs': self.policy_epochs,
            'value_epochs': self.value_epochs,
            'policy_model_summary': str(self.policy_model.summary()),
            'value_model_summary': str(self.value_model.summary()),
            'latest_losses': self.training_history[-10:] if self.training_history else [],
            'think_time': self.think_time  # Добавляем think_time
        }
        return {**base_stats, **ppo_stats}
