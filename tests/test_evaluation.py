import pytest
from rlofc.evaluation.evaluator import HandEvaluator
from rlofc.evaluation.royalty import RoyaltyCalculator
from rlofc.core.card import Card

def test_hand_evaluation():
    """Тест оценки комбинаций"""
    # Роял-флеш
    royal_flush = [
        Card.from_string(c) for c in ["Ah", "Kh", "Qh", "Jh", "Th"]
    ]
    
    # Стрит-флеш
    straight_flush = [
        Card.from_string(c) for c in ["9h", "8h", "7h", "6h", "5h"]
    ]
    
    # Каре
    four_kind = [
        Card.from_string(c) for c in ["Ah", "Ad", "Ac", "As", "Kh"]
    ]
    
    assert HandEvaluator.evaluate(royal_flush) < HandEvaluator.evaluate(straight_flush)
    assert HandEvaluator.evaluate(straight_flush) < HandEvaluator.evaluate(four_kind)

def test_royalty_calculation():
    """Тест подсчета роялти"""
    # Тройка тузов на фронте
    front_aces = [
        Card.from_string(c) for c in ["Ah", "Ad", "Ac"]
    ]
    
    # Каре на миддле
    middle_quads = [
        Card.from_string(c) for c in ["Kh", "Kd", "Kc", "Ks", "2h"]
    ]
    
    # Роял-флеш на бэке
    back_royal = [
        Card.from_string(c) for c in ["Ah", "Kh", "Qh", "Jh", "Th"]
    ]
    
    assert RoyaltyCalculator.calculate_front(front_aces) == 22
    assert RoyaltyCalculator.calculate_middle(middle_quads) == 20
    assert RoyaltyCalculator.calculate_back(back_royal) == 25
