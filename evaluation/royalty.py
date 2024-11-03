from typing import List
from core.card import Card
from evaluation.evaluator import HandEvaluator

class RoyaltyCalculator:
    """Калькулятор бонусных очков (роялти)"""
    
    @classmethod
    def calculate_front(cls, cards: List[Card]) -> int:
        """Подсчитывает роялти для передней улицы"""
        if len(cards) != 3:
            return 0
            
        rank_counts = HandEvaluator._get_rank_counts(cards)
        max_count = max(rank_counts.values())
        
        if max_count == 3:  # Тройка
            rank = max(r for r, c in rank_counts.items() if c == 3)
            return 10 + rank.value
            
        if max_count == 2:  # Пара
            rank = max(r for r, c in rank_counts.items() if c == 2)
            return max(0, rank.value - 5)
            
        return 0

    @classmethod
    def calculate_middle(cls, cards: List[Card]) -> int:
        """Подсчитывает роялти для средней улицы"""
        if len(cards) != 5:
            return 0
            
        rank = HandEvaluator.evaluate(tuple(cards))
        
        if rank <= 1609:  # Тройка или лучше
            if rank <= 1:  # Роял-флеш
                return 50
            if rank <= 10:  # Стрит-флеш
                return 30
            if rank <= 166:  # Каре
                return 20
            if rank <= 322:  # Фулл-хаус
                return 12
            if rank <= 1599:  # Флеш или стрит
                return 8
            return 2  # Тройка
            
        return 0

    @classmethod
    def calculate_back(cls, cards: List[Card]) -> int:
        """Подсчитывает роялти для задней улицы"""
        if len(cards) != 5:
            return 0
            
        rank = HandEvaluator.evaluate(tuple(cards))
        
        if rank <= 1:  # Роял-флеш
            return 25
        if rank <= 10:  # Стрит-флеш
            return 15
        if rank <= 166:  # Каре
            return 10
        if rank <= 322:  # Фулл-хаус
            return 6
        if rank <= 1599:  # Флеш
            return 4
        if rank <= 1609:  # Стрит
            return 2
            
        return 0

    @classmethod
    def calculate_total(cls, front: List[Card], middle: List[Card], back: List[Card]) -> int:
        """Подсчитывает общую сумму роялти для всех улиц"""
        return (
            cls.calculate_front(front) +
            cls.calculate_middle(middle) +
            cls.calculate_back(back)
        )
