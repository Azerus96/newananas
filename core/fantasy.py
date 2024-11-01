# core/fantasy.py

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional
from .card import Card

class FantasyMode(Enum):
    NORMAL = "normal"
    PROGRESSIVE = "progressive"

class FantasyTrigger(Enum):
    QQ = 14  # Количество карт при QQ
    KK = 15  # Количество карт при KK
    AA = 17  # Количество карт при AA
    THREE_OF_KIND = 18  # Количество карт при тройке

@dataclass
class FantasyState:
    active: bool = False
    cards_count: int = 13
    progressive_bonus: Optional[FantasyTrigger] = None
    consecutive_fantasies: int = 0

class FantasyManager:
    def __init__(self, mode: FantasyMode = FantasyMode.NORMAL):
        self.mode = mode
        self.state = FantasyState()
        self.history = []

    def check_fantasy_entry(self, board) -> bool:
        """Проверяет, попадает ли игрок в фантазию"""
        if not board.is_valid():
            return False
            
        top_combo = board.front.get_combination()
        if self.mode == FantasyMode.PROGRESSIVE:
            if top_combo.is_pair("Q"):
                self.state.progressive_bonus = FantasyTrigger.QQ
            elif top_combo.is_pair("K"):
                self.state.progressive_bonus = FantasyTrigger.KK
            elif top_combo.is_pair("A"):
                self.state.progressive_bonus = FantasyTrigger.AA
            elif top_combo.is_three_of_kind():
                self.state.progressive_bonus = FantasyTrigger.THREE_OF_KIND

        return board.get_royalties() >= 6

    def enter_fantasy(self) -> int:
        """Вход в фантазию, возвращает количество карт"""
        self.state.active = True
        self.state.consecutive_fantasies += 1
        
        if self.mode == FantasyMode.PROGRESSIVE and self.state.progressive_bonus:
            self.state.cards_count = self.state.progressive_bonus.value
        else:
            self.state.cards_count = 13
            
        return self.state.cards_count

    def exit_fantasy(self, success: bool):
        """Выход из фантазии"""
        self.history.append({
            'consecutive': self.state.consecutive_fantasies,
            'cards_count': self.state.cards_count,
            'success': success
        })
        
        if not success:
            self.state.consecutive_fantasies = 0
            
        self.state.active = False
        self.state.progressive_bonus = None
