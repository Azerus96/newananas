import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.optimizers import Adam

from agents.rl.base import RLAgent
from core.board import Board, Street # или откуда у вас импортируется Board
from typing import List
from core.card import Card

class DQNAgent(RLAgent):
    """Deep Q-Network агент"""
    
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
            idx = (card.rank.value - 2) * 4 + card.suit.value
            encoding[idx] = 1
            
        # Дополняем нулями до максимального количества карт
        padding = np.zeros(52 * (max_cards - len(cards)))
        return np.concatenate([encoding, padding])
