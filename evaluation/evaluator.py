from typing import List, Dict, Optional
from functools import lru_cache

from core.card import Card, Rank, Suit

class HandEvaluator:
    """Оценщик покерных комбинаций"""
    
    HAND_RANKINGS = {
        'High Card': 1,
        'Pair': 2,
        'Two Pair': 3,
        'Three of a Kind': 4,
        'Straight': 5,
        'Flush': 6,
        'Full House': 7,
        'Four of a Kind': 8,
        'Straight Flush': 9,
        'Royal Flush': 10
    }

    @classmethod
    @lru_cache(maxsize=100000)
    def evaluate(cls, cards: tuple[Card, ...]) -> int:
        """
        Оценивает комбинацию карт.
        Возвращает число, где меньшее значение = более сильная комбинация
        """
        if not cards:
            return float('inf')
            
        cards = list(cards)
        
        # Проверяем комбинации от сильнейшей к слабейшей
        if cls._is_royal_flush(cards):
            return 1
        if cls._is_straight_flush(cards):
            return cls._get_high_card_value(cards)
        if cls._is_four_of_kind(cards):
            return 10 + cls._get_kicker_value(cards)
        if cls._is_full_house(cards):
            return 166 + cls._get_kicker_value(cards)
        if cls._is_flush(cards):
            return 322 + cls._get_high_card_value(cards)
        if cls._is_straight(cards):
            return 1599 + cls._get_high_card_value(cards)
        if cls._is_three_of_kind(cards):
            return 1609 + cls._get_kicker_value(cards)
        if cls._is_two_pair(cards):
            return 2467 + cls._get_kicker_value(cards)
        if cls._is_pair(cards):
            return 3325 + cls._get_kicker_value(cards)
            
        return 6185 + cls._get_high_card_value(cards)

    @staticmethod
    def _get_rank_counts(cards: List[Card]) -> Dict[Rank, int]:
        """Подсчитывает количество карт каждого ранга"""
        counts = {}
        for card in cards:
            counts[card.rank] = counts.get(card.rank, 0) + 1
        return counts

    @staticmethod
    def _is_flush(cards: List[Card]) -> bool:
        """Проверяет, является ли комбинация флешем"""
        if len(cards) < 5:
            return False
        return len(set(card.suit for card in cards)) == 1

    @staticmethod
    def _is_straight(cards: List[Card]) -> bool:
        """Проверяет, является ли комбинация стритом"""
        if len(cards) < 5:
            return False
            
        ranks = sorted([card.rank.value for card in cards])
        
        # Проверка на стрит с тузом внизу
        if ranks == [2, 3, 4, 5, 14]:
            return True
            
        # Обычная проверка на стрит
        return ranks == list(range(min(ranks), max(ranks) + 1))

    @classmethod
    def _is_straight_flush(cls, cards: List[Card]) -> bool:
        """Проверяет, является ли комбинация стрит-флешем"""
        return cls._is_flush(cards) and cls._is_straight(cards)

    @classmethod
    def _is_royal_flush(cls, cards: List[Card]) -> bool:
        """Проверяет, является ли комбинация роял-флешем"""
        if not cls._is_straight_flush(cards):
            return False
        return max(card.rank.value for card in cards) == 14

    @classmethod
    def _is_four_of_kind(cls, cards: List[Card]) -> bool:
        """Проверяет, есть ли каре"""
        return 4 in cls._get_rank_counts(cards).values()

    @classmethod
    def _is_full_house(cls, cards: List[Card]) -> bool:
        """Проверяет, есть ли фулл-хаус"""
        values = list(cls._get_rank_counts(cards).values())
        return 3 in values and 2 in values

    @classmethod
    def _is_three_of_kind(cls, cards: List[Card]) -> bool:
        """Проверяет, есть ли тройка"""
        return 3 in cls._get_rank_counts(cards).values()

    @classmethod
    def _is_two_pair(cls, cards: List[Card]) -> bool:
        """Проверяет, есть ли две пары"""
        values = list(cls._get_rank_counts(cards).values())
        return values.count(2) == 2

    @classmethod
    def _is_pair(cls, cards: List[Card]) -> bool:
        """Проверяет, есть ли пара"""
        return 2 in cls._get_rank_counts(cards).values()

    @staticmethod
    def _get_high_card_value(cards: List[Card]) -> int:
        """Возвращает значение старшей карты"""
        return min(card.rank.value for card in cards)

    @classmethod
    def _get_kicker_value(cls, cards: List[Card]) -> int:
        """Вычисляет значение кикера"""
        rank_counts = cls._get_rank_counts(cards)
        kicker_ranks = sorted(
            [rank.value for rank, count in rank_counts.items()],
            reverse=True
        )
        return sum(r * (15 ** i) for i, r in enumerate(kicker_ranks))
