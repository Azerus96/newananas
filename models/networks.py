import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import (
    Input, Dense, Conv2D, Flatten, concatenate,
    BatchNormalization, Dropout, LeakyReLU
)

class NetworkFactory:
    """Фабрика для создания различных архитектур нейронных сетей"""
    
    @staticmethod
    def create_mlp(input_dim: int, output_dim: int, config: dict) -> Model:
        """Создает многослойный перцептрон"""
        inputs = Input(shape=(input_dim,))
        
        # Параметры сети
        hidden_layers = config.get('hidden_layers', [256, 256, 128])
        dropout_rate = config.get('dropout_rate', 0.2)
        use_batch_norm = config.get('use_batch_norm', True)
        
        x = inputs
        # Скрытые слои
        for units in hidden_layers:
            x = Dense(units)(x)
            if use_batch_norm:
                x = BatchNormalization()(x)
            x = LeakyReLU()(x)
            x = Dropout(dropout_rate)(x)
            
        outputs = Dense(output_dim, activation='linear')(x)
        
        return Model(inputs=inputs, outputs=outputs)
    
    @staticmethod
    def create_conv_net(input_shape: tuple, output_dim: int, config: dict) -> Model:
        """Создает сверточную нейронную сеть"""
        inputs = Input(shape=input_shape)
        
        # Параметры сети
        conv_layers = config.get('conv_layers', [
            {'filters': 32, 'kernel_size': 3},
            {'filters': 64, 'kernel_size': 3},
            {'filters': 64, 'kernel_size': 3}
        ])
        dense_layers = config.get('dense_layers', [256, 128])
        dropout_rate = config.get('dropout_rate', 0.2)
        use_batch_norm = config.get('use_batch_norm', True)
        
        x = inputs
        # Сверточные слои
        for conv_params in conv_layers:
            x = Conv2D(**conv_params, padding='same')(x)
            if use_batch_norm:
                x = BatchNormalization()(x)
            x = LeakyReLU()(x)
            
        x = Flatten()(x)
        
        # Полносвязные слои
        for units in dense_layers:
            x = Dense(units)(x)
            if use_batch_norm:
                x = BatchNormalization()(x)
            x = LeakyReLU()(x)
            x = Dropout(dropout_rate)(x)
            
        outputs = Dense(output_dim, activation='linear')(x)
        
        return Model(inputs=inputs, outputs=outputs)
    
    @staticmethod
    def create_dual_network(state_dim: int, action_dim: int, config: dict) -> tuple[Model, Model]:
        """Создает две сети для Actor-Critic архитектуры"""
        # Актор (политика)
        actor = NetworkFactory.create_mlp(
            input_dim=state_dim,
            output_dim=action_dim,
            config=config.get('actor_config', {})
        )
        
        # Критик (ценность)
        critic = NetworkFactory.create_mlp(
            input_dim=state_dim,
            output_dim=1,
            config=config.get('critic_config', {})
        )
        
        return actor, critic

class NetworkUtils:
    """Утилиты для работы с нейронными сетями"""
    
    @staticmethod
    def get_trainable_params(model: Model) -> int:
        """Возвращает количество обучаемых параметров"""
        return sum([
            tf.keras.backend.count_params(w) 
            for w in model.trainable_weights
        ])
    
    @staticmethod
    def copy_weights(source_model: Model, target_model: Model) -> None:
        """Копирует веса из одной модели в другую"""
        target_model.set_weights(source_model.get_weights())
    
    @staticmethod
    def soft_update(source_model: Model, target_model: Model, tau: float) -> None:
        """Выполняет мягкое обновление весов"""
        source_weights = source_model.get_weights()
        target_weights = target_model.get_weights()
        
        for i in range(len(target_weights)):
            target_weights[i] = (
                tau * source_weights[i] + 
                (1 - tau) * target_weights[i]
            )
            
        target_model.set_weights(target_weights)
