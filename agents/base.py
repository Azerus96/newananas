from abc import ABC, abstractmethod
from typing import Tuple, List, Optional

from core.card import Card
from core.board import Street, Board

class BaseAgent(ABC):
    """Базовый класс для всех агентов"""
    
    def __init__(self, name: str = "Agent"):
        self.name = name
        self.reset_stats()
        
    @abstractmethod
    def choose_move(self, 
                   board: Board,
                   cards: List[Card],
                   legal_moves: List[Tuple[Card, Street]],
                   opponent_board: Optional[Board] = None) -> Tuple[Card, Street]:
        """
        Выбирает ход из списка доступных
        
        Args:
            board: Текущая доска агента
            cards: Карты в руке агента
            legal_moves: Список доступных ходов
            opponent_board: Доска противника (если видима)
            
        Returns:
            Tuple[Card, Street]: Выбранные карта и улица для хода
        """
        pass
        
    def notify_game_start(self) -> None:
        """Уведомляет агента о начале новой игры"""
        self.reset_stats()
        
    def notify_opponent_move(self, card: Car
