import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense
from tensorflow.keras.optimizers import Adam

from base import RLAgent
from utils.logger import get_logger

logger = get_logger(__name__)

class PPOAgent(RLAgent):
    """Proximal Policy Optimization агент"""
    
    def __init__(self, name: str, state_size: int, action_size: int, config: dict):
        super().__init__(name, state_size, action_size, config)
        
        # Параметры PPO
        self.clip_ratio = config.get('clip_ratio', 0.2)
        self.policy_epochs = config.get('policy_epochs', 10)
        self.value_epochs = config.get('value_epochs', 10)
        self.target_kl = config.get('target_kl', 0.01)
        self.value_loss_coef = config.get('value_loss_coef', 0.5)
        
        # Создаем отдельные модели для политики и значения
        self.policy_model = self._build_policy_model()
        self.value_model = self._build_value_model()
        
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
        
        return {
            'policy_loss': loss.numpy(),
            'value_loss': value_loss
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
        
        return -tf.reduce_mean(tf.minimum(surrogate1, surrogate2))
        
    def choose_move(self, board: Board, cards: List[Card],
                   legal_moves: List[Tuple[Card, Street]],
                   opponent_board: Board = None) -> Tuple[Card, Street]:
        """Выбирает действие используя текущую политику"""
        state = self.encode_state(board, cards, opponent_board)
        policy = self.policy_model.predict(state.reshape(1, -1))[0]
        
        # Применяем маску легальных ходов
        legal_mask = self._get_legal_action_mask(legal_moves)
        masked_policy = policy * legal_mask
        
        # Нормализуем вероятности
        masked_policy = masked_policy / np.sum(masked_policy)
        
        # Выбираем действие
        if np.random.random() < self.epsilon:
            action_idx = np.random.choice(len(legal_moves))
        else:
            action_idx = np.random.choice(
                self.action_size,
                p=masked_policy
            )
            
        return legal_moves[action_idx]
        
    def save(self, filepath: str) -> None:
        """Сохраняет модели"""
        self.policy_model.save(f"{filepath}_policy")
        self.value_model.save(f"{filepath}_value")
        
    def load(self, filepath: str) -> None:
        """Загружает модели"""
        self.policy_model = tf.keras.models.load_model(f"{filepath}_policy")
        self.value_model = tf.keras.models.load_model(f"{filepath}_value")
