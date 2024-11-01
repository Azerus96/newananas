# utils/game_state.py

from typing import List, Dict, Optional
from dataclasses import dataclass
from core.card import Card
from core.board import Board, Street

@dataclass
class GameState:
    """Представляет текущее состояние игры"""
    board: Board
    input_cards: List[Optional[Card]]
    removed_cards: List[Card]
    fantasy_mode: bool
    progressive_fantasy: bool
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GameState':
        """Создает состояние из словаря"""
        return cls(
            board=Board.from_dict(data['board']),
            input_cards=[
                Card.from_string(c) if c else None 
                for c in data['input_cards']
            ],
            removed_cards=[
                Card.from_string(c) for c in data['removed_cards']
            ],
            fantasy_mode=data['fantasy_mode'],
            progressive_fantasy=data['progressive_fantasy']
        )
    
    def to_dict(self) -> Dict:
        """Преобразует состояние в словарь"""
        return {
            'board': self.board.to_dict(),
            'input_cards': [
                str(c) if c else None 
                for c in self.input_cards
            ],
            'removed_cards': [str(c) for c in self.removed_cards],
            'fantasy_mode': self.fantasy_mode,
            'progressive_fantasy': self.progressive_fantasy
        }
    
    def is_valid(self) -> bool:
        """Проверяет валидность состояния"""
        # Проверяем количество карт
        all_cards = (
            [c for c in self.input_cards if c] +
            self.removed_cards +
            self.board.get_all_cards()
        )
        
        if len(set(all_cards)) != len(all_cards):
            return False
            
        # Проверяем валидность доски
        if not self.board.is_valid():
            return False
            
        return True
    
    def get_available_moves(self) -> List[Dict]:
        """Возвращает список доступных ходов"""
        moves = []
        cards = [c for c in self.input_cards if c]
        
        for card in cards:
            for street in Street:
                if not self.board._get_street(street).is_full():
                    moves.append({
                        'card': card,
                        'street': street
                    })
        
        return moves

    def apply_move(self, move: Dict) -> bool:
        """Применяет ход к текущему состоянию"""
        try:
            # Проверяем валидность хода
            if move['card'] not in self.input_cards:
                return False
                
            # Применяем ход
            self.board.place_card(move['card'], move['street'])
            self.input_cards.remove(move['card'])
            
            return True
        except Exception:
            return False
