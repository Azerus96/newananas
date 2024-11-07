import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense, Lambda
from tensorflow.keras.optimizers import Adam
import threading
import time
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path
import json

from agents.rl.base import RLAgent
from core.board import Board, Street
from core.card import Card
from utils.logger import get_logger

logger = get_logger(__name__)

class A3CAgent(RLAgent):
    """Asynchronous Advantage Actor-Critic агент"""
    
    def __init__(self, name: str, state_size: int, action_size: int, config: dict, think_time: int = 30):
        super().__init__(name, state_size, action_size, config, think_time=think_time)
        
        # Дополнительные параметры A3C
        self.num_workers = config.get('num_workers', 4)
        self.value_loss_coef = config.get('value_loss_coef', 0.5)
        self.entropy_coef = config.get('entropy_coef', 0.01)
        
        # Создаем глобальную модель
        self.global_model = self._build_model()
        self.global_optimizer = Adam(learning_rate=self.learning_rate)
        
        # Создаем воркеров
        self.workers = []
        for i in range(self.num_workers):
            worker = A3CWorker(
                f"{name}_worker_{i}",
                state_size,
                action_size,
                self.global_model,
                self.global_optimizer,
                config,
                think_time=think_time  # Передаем think_time воркерам
            )
            self.workers.append(worker)

        # Счетчики для отслеживания прогресса
        self.total_steps = 0
        self.total_updates = 0
            
    @classmethod
    def load_latest(cls, name: str = "A3C", state_size: int = None, 
                   action_size: int = None, config: dict = None, 
                   think_time: int = 30):  # Добавляем параметр think_time
        """Загружает последнюю сохраненную модель A3C"""
        try:
            # Определяем директорию моделей A3C
            model_dir = Path("models") / "a3c"
            if not model_dir.exists():
                model_dir.mkdir(parents=True)

            # Ищем последний чекпоинт
            checkpoints = list(model_dir.glob("*_global.h5"))
            if not checkpoints:
                logger.warning("No saved A3C models found")
                if not all([state_size, action_size, config]):
                    raise ValueError("Need state_size, action_size and config for new model")
                return cls(name, state_size, action_size, config, think_time=think_time)

            # Находим самую свежую модель
            latest_model = max(checkpoints, key=lambda p: p.stat().st_mtime)
            base_path = str(latest_model).replace('_global.h5', '')
            
            # Загружаем конфигурацию
            config_path = Path(base_path + '_metadata.json')
            if config_path.exists():
                with open(config_path, 'r') as f:
                    saved_config = json.load(f)
                    state_size = saved_config.get('state_size')
                    action_size = saved_config.get('action_size')
                    config = saved_config.get('config', {})
                    think_time = saved_config.get('think_time', think_time)  # Загружаем сохраненный think_time

            # Создаем и загружаем агента
            agent = cls(name, state_size, action_size, config, think_time=think_time)
            agent.load(base_path)
            
            logger.info(f"Loaded A3C model: {latest_model}")
            return agent

        except Exception as e:
            logger.error(f"Error loading A3C model: {e}")
            if not all([state_size, action_size, config]):
                raise ValueError("Need state_size, action_size and config for new model")
            return cls(name, state_size, action_size, config, think_time=think_time)
            
    def _build_model(self):
        """Создает модель актора и критика"""
        # Входной слой
        input_layer = Input(shape=(self.state_size,))
        
        # Общие слои
        dense1 = Dense(256, activation='relu')(input_layer)
        dense2 = Dense(256, activation='relu')(dense1)
        
        # Выход политики (актор)
        policy_dense = Dense(128, activation='relu')(dense2)
        policy_output = Dense(self.action_size, activation='softmax')(policy_dense)
        
        # Выход значения (критик)
        value_dense = Dense(128, activation='relu')(dense2)
        value_output = Dense(1, activation='linear')(value_dense)
        
        # Создаем модель
        model = Model(
            inputs=input_layer,
            outputs=[policy_output, value_output]
        )
        
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
        """Выбирает действие используя обученную политику"""
        # Используем переданное время или значение по умолчанию
        current_think_time = think_time or self.think_time
        
        start_time = time.time()
        
        state = self.encode_state(board, cards, opponent_board)
        policy, _ = self.global_model.predict(
            state.reshape(1, -1),
            timeout=current_think_time
        )
        
        # Применяем маску легальных ходов
        legal_mask = self._get_legal_action_mask(legal_moves)
        masked_policy = policy * legal_mask
        
        # Нормализуем вероятности
        masked_policy = masked_policy / np.sum(masked_policy)
        
        # Проверяем оставшееся время
        elapsed_time = time.time() - start_time
        if elapsed_time > current_think_time:
            logger.warning(f"Think time exceeded: {elapsed_time:.2f}s > {current_think_time}s")
        
        # Выбираем действие
        action_idx = np.random.choice(self.action_size, p=masked_policy[0])
        return legal_moves[action_idx]

    def train(self, env, max_episodes: int):
        """Запускает асинхронное обучение"""
        # Запускаем воркеров
        threads = []
        for worker in self.workers:
            thread = threading.Thread(
                target=worker.train,
                args=(env, max_episodes)
            )
            thread.start()
            threads.append(thread)
            
        # Ждем завершения всех воркеров
        for thread in threads:
            thread.join()
            
        # Обновляем общую статистику
        self.total_steps = sum(worker.steps for worker in self.workers)
        self.total_updates = sum(worker.updates for worker in self.workers)

    def save(self, filepath: str) -> None:
        """Сохраняет модель и метаданные"""
        # Сохраняем глобальную модель
        self.global_model.save(filepath + '_global.h5')
        
        # Сохраняем метаданные
        metadata = {
            'epsilon': self.epsilon,
            'total_steps': self.total_steps,
            'total_updates': self.total_updates,
            'state_size': self.state_size,
            'action_size': self.action_size,
            'config': self.config,
            'training_history': self.training_history,
            'think_time': self.think_time  # Сохраняем think_time
        }
        
        with open(filepath + '_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=4)

    def load(self, filepath: str) -> None:
        """Загружает модель и метаданные"""
        # Загружаем глобальную модель
        self.global_model = tf.keras.models.load_model(filepath + '_global.h5')
        
        # Обновляем модели воркеров
        for worker in self.workers:
            worker.local_model.set_weights(self.global_model.get_weights())
        
        # Загружаем метаданные
        try:
            with open(filepath + '_metadata.json', 'r') as f:
                metadata = json.load(f)
                self.epsilon = metadata.get('epsilon', self.epsilon_min)
                self.total_steps = metadata.get('total_steps', 0)
                self.total_updates = metadata.get('total_updates', 0)
                self.training_history = metadata.get('training_history', [])
                self.think_time = metadata.get('think_time', self.think_time)  # Загружаем think_time
                self.config.update(metadata.get('config', {}))
        except FileNotFoundError:
            logger.warning(f"No metadata file found for {filepath}")

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает расширенную статистику агента"""
        base_stats = super().get_stats()
        a3c_stats = {
            'total_steps': self.total_steps,
            'total_updates': self.total_updates,
            'num_workers': self.num_workers,
            'value_loss_coef': self.value_loss_coef,
            'entropy_coef': self.entropy_coef,
            'model_summary': str(self.global_model.summary()),
            'worker_stats': [worker.get_stats() for worker in self.workers],
            'latest_losses': self.training_history[-10:] if self.training_history else [],
            'think_time': self.think_time  # Добавляем think_time в статистику
        }
        return {**base_stats, **a3c_stats}


class A3CWorker(RLAgent):
    """Рабочий поток для A3C"""
    
    def __init__(self, name: str, state_size: int, action_size: int,
                 global_model: Model, global_optimizer: Adam, config: dict,
                 think_time: int = 30):  # Добавляем параметр think_time
        super().__init__(name, state_size, action_size, config, think_time=think_time)
        
        self.global_model = global_model
        self.global_optimizer = global_optimizer
        self.local_model = self._build_model()
        self.value_loss_coef = config.get('value_loss_coef', 0.5)
        self.entropy_coef = config.get('entropy_coef', 0.01)
        
        # Счетчики для статистики
        self.steps = 0
        self.updates = 0
        
    def train(self, env, max_episodes: int):
        """Обучает локальную модель и обновляет глобальную"""
        for episode in range(max_episodes):
            state = env.reset()
            done = False
            episode_reward = 0
            
            # Сохраняем траекторию
            states, actions, rewards = [], [], []
            
            while not done:
                # Получаем действие от локальной модели с учетом think_time
                start_time = time.time()
                policy, value = self.local_model.predict(
                    state.reshape(1, -1),
                    timeout=self.think_time
                )
                action = np.random.choice(self.action_size, p=policy[0])
                
                # Делаем шаг в среде
                next_state, reward, done, _ = env.step(action)
                
                # Сохраняем опыт
                states.append(state)
                actions.append(action)
                rewards.append(reward)
                
                state = next_state
                episode_reward += reward
                self.steps += 1
                
                # Проверяем время
                elapsed_time = time.time() - start_time
                if elapsed_time > self.think_time:
                    logger.warning(f"Worker {self.name} think time exceeded: {elapsed_time:.2f}s > {self.think_time}s")
                
            # Обучаем на собранной траектории
            self._train_trajectory(states, actions, rewards)
            self.updates += 1
            
            logger.info(f"Worker {self.name} Episode {episode}: reward={episode_reward}")
            
    def _train_trajectory(self, states, actions, rewards):
        """Обучает на одной траектории"""
        # Конвертируем в numpy массивы
        states = np.array(states)
        actions = np.array(actions)
        rewards = np.array(rewards)
        
        # Вычисляем возвраты
        returns = self._compute_returns(rewards)
        
        with tf.GradientTape() as tape:
            # Получаем предсказания модели
            policies, values = self.local_model(states)
            
            # Вычисляем преимущества
            advantages = returns - values

            # Считаем функцию потерь
            policy_loss = self._compute_policy_loss(policies, actions, advantages)
            value_loss = self._compute_value_loss(values, returns)
            entropy_loss = self._compute_entropy_loss(policies)
            
            # Общая функция потерь
            total_loss = (policy_loss + 
                         self.value_loss_coef * value_loss + 
                         self.entropy_coef * entropy_loss)
        
        # Вычисляем градиенты
        grads = tape.gradient(total_loss, self.local_model.trainable_variables)
        
        # Применяем градиенты к глобальной модели
        self.global_optimizer.apply_gradients(
            zip(grads, self.global_model.trainable_variables)
        )
        
        # Синхронизируем локальную модель с глобальной
        self.local_model.set_weights(self.global_model.get_weights())
        
    def _compute_returns(self, rewards: np.ndarray) -> np.ndarray:
        """Вычисляет возвраты для каждого шага"""
        returns = np.zeros_like(rewards)
        running_return = 0
        
        for t in reversed(range(len(rewards))):
            running_return = rewards[t] + self.gamma * running_return
            returns[t] = running_return
            
        return returns
        
    def _compute_policy_loss(self, policies, actions, advantages):
        """Вычисляет функцию потерь политики"""
        actions_one_hot = tf.one_hot(actions, self.action_size)
        action_probs = tf.reduce_sum(actions_one_hot * policies, axis=1)
        log_probs = tf.math.log(action_probs + 1e-10)
        
        return -tf.reduce_mean(log_probs * advantages)
        
    def _compute_value_loss(self, values, returns):
        """Вычисляет функцию потерь значения"""
        return tf.reduce_mean(tf.square(returns - values))
        
    def _compute_entropy_loss(self, policies):
        """Вычисляет энтропию политики"""
        log_policies = tf.math.log(policies + 1e-10)
        return -tf.reduce_mean(tf.reduce_sum(policies * log_policies, axis=1))
        
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику воркера"""
        base_stats = super().get_stats()
        worker_stats = {
            'steps': self.steps,
            'updates': self.updates,
            'think_time': self.think_time  # Добавляем think_time в статистику
        }
        return {**base_stats, **worker_stats}
