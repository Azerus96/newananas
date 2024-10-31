import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense, Lambda
from tensorflow.keras.optimizers import Adam
import threading

from .base import RLAgent
from ...utils.logger import get_logger

logger = get_logger(__name__)

class A3CAgent(RLAgent):
    """Asynchronous Advantage Actor-Critic агент"""
    
    def __init__(self, name: str, state_size: int, action_size: int, config: dict):
        super().__init__(name, state_size, action_size, config)
        
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
                config
            )
            self.workers.append(worker)
            
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
            
    def choose_move(self, board: Board, cards: List[Card],
                   legal_moves: List[Tuple[Card, Street]],
                   opponent_board: Board = None) -> Tuple[Card, Street]:
        """Выбирает действие используя обученную политику"""
        state = self.encode_state(board, cards, opponent_board)
        policy, _ = self.global_model.predict(state.reshape(1, -1))
        
        # Применяем маску легальных ходов
        legal_mask = self._get_legal_action_mask(legal_moves)
        masked_policy = policy * legal_mask
        
        # Нормализуем вероятности
        masked_policy = masked_policy / np.sum(masked_policy)
        
        # Выбираем действие
        action_idx = np.random.choice(self.action_size, p=masked_policy[0])
        return legal_moves[action_idx]

class A3CWorker(RLAgent):
    """Рабочий поток для A3C"""
    
    def __init__(self, name: str, state_size: int, action_size: int,
                 global_model: Model, global_optimizer: Adam, config: dict):
        super().__init__(name, state_size, action_size, config)
        
        self.global_model = global_model
        self.global_optimizer = global_optimizer
        self.local_model = self._build_model()
        self.value_loss_coef = config.get('value_loss_coef', 0.5)
        self.entropy_coef = config.get('entropy_coef', 0.01)
        
    def train(self, env, max_episodes: int):
        """Обучает локальную модель и обновляет глобальную"""
        for episode in range(max_episodes):
            state = env.reset()
            done = False
            episode_reward = 0
            
            # Сохраняем траекторию
            states, actions, rewards = [], [], []
            
            while not done:
                # Получаем действие от локальной модели
                policy, value = self.local_model.predict(state.reshape(1, -1))
                action = np.random.choice(self.action_size, p=policy[0])
                
                # Делаем шаг в среде
                next_state, reward, done, _ = env.step(action)
                
                # Сохраняем опыт
                states.append(state)
                actions.append(action)
                rewards.append(reward)
                
                state = next_state
                episode_reward += reward
                
            # Обучаем на собранной траектории
            self._train_trajectory(states, actions, rewards)
            
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
            
            total_loss = (policy_loss + 
                         self.value_loss_coef * value_loss -
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
        """Вычисляет возвраты с учетом дисконтирования"""
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
        return -tf.reduce_mean(
            tf.reduce_sum(policies * tf.math.log(policies + 1e-10), axis=1)
        )
        
