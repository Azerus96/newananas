import random
from typing import Tuple, List, Optional
import json
import os

from agents.base import BaseAgent
from core.card import Card
from core.board import Street, Board

class RandomAgent(BaseAgent):
    """Агент, делающий случайные ходы"""
    
    def __init__(self, name: str = "RandomAgent", seed: Optional[int] = None):
        super().__init__(name)
        if seed is not None:
            random.seed(seed)
        self.history = []
        self.save_path = f"agents/saved_states/{name}_latest.json"
            
    def choose_move(self,
                   board: Board,
                   cards: List[Card],
                   legal_moves: List[Tuple[Card, Street]],
                   opponent_board: Optional[Board] = None) -> Tuple[Card, Street]:
        """Выбирает случайный ход из доступных"""
        move = random.choice(legal_moves)
        # Сохраняем ход в историю
        self.history.append({
            'board_state': board.to_dict(),
            'cards': [card.to_dict() for card in cards],
            'chosen_move': {
                'card': move[0].to_dict(),
                'street': move[1].value
            }
        })
        self.save_latest()
        return move

    def load_latest(self) -> None:
        """Загружает последнее состояние агента"""
        try:
            if os.path.exists(self.save_path):
                with open(self.save_path, 'r') as f:
                    data = json.load(f)
                self.history = data.get('history', [])
                # Восстанавливаем seed если он был сохранен
                if 'seed' in data:
                    random.seed(data['seed'])
        except Exception as e:
            print(f"Error loading latest state for {self.name}: {e}")
            self.history = []

    def save_latest(self) -> None:
        """Сохраняет текущее состояние агента"""
        try:
            os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
            with open(self.save_path, 'w') as f:
                json.dump({
                    'history': self.history,
                    'seed': random.getstate()  # Сохраняем текущее состояние генератора случайных чисел
                }, f)
        except Exception as e:
            print(f"Error saving state for {self.name}: {e}")

    def reset(self) -> None:
        """Сбрасывает состояние агента"""
        self.history = []
        self.save_latest()
