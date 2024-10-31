import random
from typing import List, Optional
from .card import Card, Rank, Suit

class Deck:
    """Колода карт с методами для перемешивания и раздачи"""
    
    def __init__(self, seed: Optional[int] = None):
        self._cards = self._create_deck()
        self._original_cards = self._cards.copy()
        if seed is not None:
            random.seed(seed)
            
    @staticmethod
    def _create_deck() -> List[Card]:
        """Создает новую колоду из 52 карт"""
        return [
            Card(rank=rank, suit=suit)
            for rank in Rank
            for suit in Suit
        ]
    
    def shuffle(self, seed: Optional[int] = None) -> None:
        """Перемешивает колоду"""
        if seed is not None:
            random.seed(seed)
        random.shuffle(self._cards)
        
    def reset(self) -> None:
        """Возвращает колоду в исходное состояние"""
        self._cards = self._original_cards.copy()
        
    def draw(self, count: int = 1) -> List[Card]:
        """Берет указанное количество карт сверху колоды"""
        if count > len(self._cards):
            raise ValueError(f"Cannot draw {count} cards, only {len(self._cards)} remaining")
        drawn = self._cards[:count]
        self._cards = self._cards[count:]
        return drawn
    
    def draw_one(self) -> Card:
        """Берет одну карту сверху колоды"""
        return self.draw(1)[0]
    
    def cards_remaining(self) -> int:
        """Возвращает количество оставшихся карт"""
        return len(self._cards)
    
    def peek(self, count: int = 1) -> List[Card]:
        """Просматривает верхние карты колоды без их извлечения"""
        if count > len(self._cards):
            raise ValueError(f"Cannot peek {count} cards, only {len(self._cards)} remaining")
        return self._cards[:count]
    
    def insert(self, cards: List[Card], position: int = 0) -> None:
        """Вставляет карты в указанную позицию колоды"""
        if position > len(self._cards):
            raise ValueError(f"Invalid position {position}")
        self._cards = self._cards[:position] + cards + self._cards[position:]
        
    def remove(self, cards: List[Card]) -> None:
        """Удаляет указанные карты из колоды"""
        for card in cards:
            try:
                self._cards.remove(card)
            except ValueError:
                raise ValueError(f"Card {card} not in deck")
                
    def __len__(self) -> int:
        return len(self._cards)
    
    def __str__(self) -> str:
        return f"Deck({len(self._cards)} cards)"
    
    def __repr__(self) -> str:
        return f"Deck(cards={self._cards})"
