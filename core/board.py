from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum

from core.card import Card
from evaluation.evaluator import HandEvaluator
from evaluation.royalty import RoyaltyCalculator

class Street(Enum):
    FRONT = 0
    MIDDLE = 1
    BACK = 2

@dataclass
class StreetHand:
    """Представляет одну улицу (front/middle/back) на доске"""
    cards: List[Card] = field(default_factory=list)
    max_cards: int = field(default=5)
    
    def __post_init__(self):
        if len(self.cards) > self.max_cards:
            raise ValueError(f"Too many cards for street: {len(self.cards)} > {self.max_cards}")
    
    def add_card(self, card: Card) -> None:
        """Добавляет карту в улицу"""
        if len(self.cards) >= self.max_cards:
            raise ValueError("Street is full")
        self.cards.append(card)
        
    def is_full(self) -> bool:
        """Проверяет, заполнена ли улица"""
        return len(self.cards) == self.max_cards
    
    def get_rank(self) -> int:
        """Возвращает ранг комбинации"""
        return HandEvaluator.evaluate(self.cards)
    
    def clear(self) -> None:
        """Очищает улицу"""
        self.cards = []

    def to_dict(self) -> dict:
        """Преобразует улицу в словарь"""
        return {
            'cards': [card.to_dict() for card in self.cards],
            'max_cards': self.max_cards
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'StreetHand':
        """Создает объект StreetHand из словаря"""
        return cls(
            cards=[Card.from_dict(card_data) for card_data in data['cards']],
            max_cards=data['max_cards']
        )

@dataclass
class Board:
    """Представляет доску игрока с тремя улицами"""
    front: StreetHand = field(default_factory=lambda: StreetHand(max_cards=3))
    middle: StreetHand = field(default_factory=lambda: StreetHand(max_cards=5))
    back: StreetHand = field(default_factory=lambda: StreetHand(max_cards=5))
    
    def place_card(self, card: Card, street: Street) -> None:
        """Размещает карту на указанной улице"""
        street_hand = self._get_street(street)
        street_hand.add_card(card)
        
    def get_free_streets(self) -> List[Street]:
        """Возвращает список доступных для размещения улиц"""
        return [
            street for street in Street
            if not self._get_street(street).is_full()
        ]
    
    def is_complete(self) -> bool:
        """Проверяет, заполнена ли вся доска"""
        return all(self._get_street(street).is_full() for street in Street)
    
    def is_valid(self) -> bool:
        """Проверяет валидность расстановки (back >= middle >= front)"""
        if not self.is_complete():
            return False
            
        back_rank = self.back.get_rank()
        middle_rank = self.middle.get_rank()
        front_rank = self.front.get_rank()
        
        return back_rank <= middle_rank <= front_rank
    
    def get_royalties(self) -> int:
        """Подсчитывает роялти за комбинации"""
        if not self.is_complete():
            return 0
            
        return (
            RoyaltyCalculator.calculate_front(self.front.cards) +
            RoyaltyCalculator.calculate_middle(self.middle.cards) +
            RoyaltyCalculator.calculate_back(self.back.cards)
        )
    
    def _get_street(self, street: Street) -> StreetHand:
        """Возвращает объект улицы по enum"""
        if street == Street.FRONT:
            return self.front
        elif street == Street.MIDDLE:
            return self.middle
        else:
            return self.back
            
    def clear(self) -> None:
        """Очищает всю доску"""
        self.front.clear()
        self.middle.clear()
        self.back.clear()
        
    def pretty_print(self) -> None:
        """Красивый вывод доски"""
        print("Front:", " ".join(card.pretty_str() for card in self.front.cards))
        print("Middle:", " ".join(card.pretty_str() for card in self.middle.cards))
        print("Back:", " ".join(card.pretty_str() for card in self.back.cards))

    def to_dict(self) -> dict:
        """Преобразует доску в словарь"""
        return {
            'front': self.front.to_dict(),
            'middle': self.middle.to_dict(),
            'back': self.back.to_dict()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Board':
        """Создает объект Board из словаря"""
        return cls(
            front=StreetHand.from_dict(data['front']),
            middle=StreetHand.from_dict(data['middle']),
            back=StreetHand.from_dict(data['back'])
        )

    def get_state(self) -> dict:
        """Возвращает текущее состояние доски"""
        return {
            'front': {
                'cards': [card.to_dict() for card in self.front.cards],
                'is_complete': self.front.is_full()
            },
            'middle': {
                'cards': [card.to_dict() for card in self.middle.cards],
                'is_complete': self.middle.is_full()
            },
            'back': {
                'cards': [card.to_dict() for card in self.back.cards],
                'is_complete': self.back.is_full()
            },
            'is_complete': self.is_complete(),
            'is_valid': self.is_valid()
        }
