# core/fantasy.py

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Dict
from collections import defaultdict

from core.card import Card
from core.board import Board, Street
from utils.logger import get_logger

logger = get_logger(__name__)

class FantasyMode(Enum):
    NORMAL = "normal"
    PROGRESSIVE = "progressive"

class FantasyTrigger(Enum):
    QQ = {"cards": 14, "description": "Pair of Queens"}
    KK = {"cards": 15, "description": "Pair of Kings"}
    AA = {"cards": 17, "description": "Pair of Aces"}
    THREE_OF_KIND = {"cards": 18, "description": "Three of a Kind"}

@dataclass
class FantasyState:
    active: bool = False
    cards_count: int = 13
    progressive_bonus: Optional[FantasyTrigger] = None
    consecutive_fantasies: int = 0
    history: List[Dict] = None

    def __post_init__(self):
        self.history = []

class FantasyManager:
    """Управляет механикой фантазии"""

    def __init__(self, mode: FantasyMode = FantasyMode.NORMAL):
        self.mode = mode
        self.state = FantasyState()
        self.statistics = defaultdict(int)
        self.logger = get_logger(__name__)

    def check_fantasy_entry(self, board: Board) -> bool:
        """Проверяет возможность входа в фантазию"""
        if not board.is_valid():
            return False

        # Проверяем верхнюю улицу для прогрессивной фантазии
        if self.mode == FantasyMode.PROGRESSIVE:
            top_cards = board.front.cards
            trigger = self._check_progressive_trigger(top_cards)
            if trigger:
                self.state.progressive_bonus = trigger
                self.logger.info(f"Progressive fantasy triggered: {trigger.name}")

        # Проверяем общие условия фантазии
        royalties = board.get_royalties()
        is_fantasy = royalties >= 6

        if is_fantasy:
            self.logger.info(f"Fantasy achieved with {royalties} royalties")
            self.statistics['total_entries'] += 1

        return is_fantasy

    def _check_progressive_trigger(self, cards: List[Card]) -> Optional[FantasyTrigger]:
        """Проверяет триггеры прогрессивной фантазии"""
        if len(cards) < 2:
            return None

        # Проверяем пары
        ranks = [card.rank for card in cards]
        if ranks.count(ranks[0]) >= 2:
            if ranks[0] == 'Q':
                return FantasyTrigger.QQ
            elif ranks[0] == 'K':
                return FantasyTrigger.KK
            elif ranks[0] == 'A':
                return FantasyTrigger.AA

        # Проверяем тройку
        if len(cards) == 3 and ranks.count(ranks[0]) == 3:
            return FantasyTrigger.THREE_OF_KIND

        return None

    def enter_fantasy(self) -> int:
        """Вход в режим фантазии"""
        self.state.active = True
        self.state.consecutive_fantasies += 1

        cards_count = 13  # базовое количество карт

        if self.mode == FantasyMode.PROGRESSIVE and self.state.progressive_bonus:
            cards_count = self.state.progressive_bonus.value['cards']
            self.statistics[f'progressive_{self.state.progressive_bonus.name}'] += 1

        self.state.cards_count = cards_count
        self.state.history.append({
            'trigger': self.state.progressive_bonus.name if self.state.progressive_bonus else 'normal',
            'cards_count': cards_count,
            'consecutive': self.state.consecutive_fantasies
        })

        self.logger.info(f"Entering fantasy with {cards_count} cards")
        return cards_count

    def exit_fantasy(self, success: bool):
        """Выход из режима фантазии"""
        if success:
            self.statistics['successful_exits'] += 1
            if self.state.consecutive_fantasies > self.statistics['max_consecutive']:
                self.statistics['max_consecutive'] = self.state.consecutive_fantasies
        else:
            self.state.consecutive_fantasies = 0
            self.statistics['failed_exits'] += 1

        self.state.active = False
        self.state.progressive_bonus = None
        self.logger.info(f"Exiting fantasy (success: {success})")

    def get_statistics(self) -> Dict:
        """Возвращает статистику фантазий"""
        total_entries = self.statistics['total_entries']
        return {
            'total_entries': total_entries,
            'success_rate': (self.statistics['successful_exits'] / total_entries 
                           if total_entries > 0 else 0),
            'max_consecutive': self.statistics['max_consecutive'],
            'progressive_triggers': {
                trigger.name: self.statistics[f'progressive_{trigger.name}']
                for trigger in FantasyTrigger
            },
            'history': self.state.history
        }

class FantasyStrategy:
    """Стратегия игры в фантазии"""

    def __init__(self, fantasy_manager: FantasyManager):
        self.fantasy_manager = fantasy_manager
        self.statistics = defaultdict(lambda: defaultdict(int))

    def evaluate_move(self, board: Board, card: Card, street: Street) -> float:
        """Оценивает ход с точки зрения сохранения в фантазии"""
        if not self.fantasy_manager.state.active:
            return 0.0

        # Создаем копию доски для симуляции хода
        test_board = board.copy()
        test_board.place_card(card, street)

        # Базовая оценка - валидность расстановки
        if not test_board.is_valid():
            return 0.0

        score = 1.0

        # Бонус за роялти (но не главный приоритет)
        royalties = test_board.get_royalties()
        score += min(royalties / 12.0, 0.5)  # максимум +0.5 за роялти

        # Проверяем историческую успешность похожих расстановок
        historical_success = self._get_historical_success(test_board, street)
        score += historical_success * 0.3  # вес исторической статистики

        return score

    def _get_historical_success(self, board: Board, street: Street) -> float:
        """Получает историческую успешность похожей расстановки"""
        pattern = self._get_board_pattern(board, street)
        stats = self.statistics[pattern]
        
        if stats['total'] == 0:
            return 0.5  # нейтральная оценка для новых паттернов
            
        return stats['success'] / stats['total']

    def _get_board_pattern(self, board: Board, street: Street) -> str:
        """Создает паттерн расстановки для анализа"""
        street_cards = board._get_street(street).cards
        return f"{street.name}_{len(street_cards)}_{board.get_royalties()}"

    def update_statistics(self, board: Board, success: bool):
        """Обновляет статистику успешности паттернов"""
        for street in Street:
            pattern = self._get_board_pattern(board, street)
            self.statistics[pattern]['total'] += 1
            if success:
                self.statistics[pattern]['success'] += 1

    def get_best_moves(self, board: Board, available_cards: List[Card], 
                      top_n: int = 3) -> List[tuple]:
        """Возвращает лучшие ходы для сохранения в фантазии"""
        moves = []
        
        for card in available_cards:
            for street in Street:
                if not board._get_street(street).is_full():
                    score = self.evaluate_move(board, card, street)
                    moves.append((card, street, score))
        
        # Сортируем ходы по оценке
        return sorted(moves, key=lambda x: x[2], reverse=True)[:top_n]

    def get_strategy_stats(self) -> Dict:
        """Возвращает статистику стратегии"""
        total_patterns = len(self.statistics)
        successful_patterns = sum(
            1 for stats in self.statistics.values()
            if stats['success'] / stats['total'] > 0.7
        )
        
        return {
            'total_patterns': total_patterns,
            'successful_patterns': successful_patterns,
            'best_patterns': self._get_best_patterns(),
            'pattern_success_rate': successful_patterns / total_patterns if total_patterns > 0 else 0
        }

    def _get_best_patterns(self, limit: int = 5) -> List[Dict]:
        """Возвращает наиболее успешные паттерны"""
        patterns = []
        
        for pattern, stats in self.statistics.items():
            if stats['total'] >= 5:  # минимальный порог для статистической значимости
                success_rate = stats['success'] / stats['total']
                patterns.append({
                    'pattern': pattern,
                    'success_rate': success_rate,
                    'total_uses': stats['total']
                })
        
        return sorted(patterns, key=lambda x: x['success_rate'], reverse=True)[:limit]
