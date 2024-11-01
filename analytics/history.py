# analytics/history.py

from dataclasses import dataclass
from typing import List, Dict, Optional
from collections import defaultdict

@dataclass
class GameHistory:
    cards_played: List[Card]
    combinations_formed: List[Tuple[List[Card], str]]  # карты и тип комбинации
    result: str
    fantasy_achieved: bool
    score: int

class HistoryAnalyzer:
    def __init__(self):
        self.game_histories: List[GameHistory] = []
        self.combination_success_rate = defaultdict(lambda: {'success': 0, 'total': 0})
        
    def add_game(self, history: GameHistory):
        self.game_histories.append(history)
        self._update_statistics(history)
    
    def get_combination_probability(self, cards: List[Card], target_combination: str) -> float:
        """Возвращает вероятность успеха комбинации на основе истории игр"""
        stats = self.combination_success_rate[self._cards_to_key(cards)]
        return stats['success'] / stats['total'] if stats['total'] > 0 else 0
    
    def _update_statistics(self, history: GameHistory):
        for cards, combo_type in history.combinations_formed:
            key = self._cards_to_key(cards)
            self.combination_success_rate[key]['total'] += 1
            if history.result == 'win':
                self.combination_success_rate[key]['success'] += 1
    
    @staticmethod
    def _cards_to_key(cards: List[Card]) -> str:
        """Преобразует список карт в уникальный ключ"""
        return '_'.join(sorted(str(card) for card in cards))
