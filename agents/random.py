import random
from typing import Tuple, List, Optional

from .base import BaseAgent
from ..core.card import Card
from ..core.board import Street, Board

class RandomAgent(BaseAgent):
    """Агент, делающий случайные ходы"""
    
    def __init__(self, name: str = "RandomAgent", seed: Optional[int] = None):
        super().__init__(name)
        if seed is not None:
            random.seed(seed)
            
    def choose_move(self,
                   board: Board,
                   cards: List[Card],
                   legal_moves: List[Tuple[Card, Street]],
                   opponent_board: Optional[Board] = None) -> Tuple[Card, Street]:
        """Выбирает случайный ход из доступных"""
        return random.choice(legal_moves)
