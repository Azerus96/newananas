# agents/strategy.py

from typing import List, Tuple, Dict, Optional
import numpy as np
from core.card import Card
from core.board import Board, Street
from analytics.history import HistoryAnalyzer
from core.fantasy import FantasyManager

class StrategyContext:
    def __init__(self, 
                 history_analyzer: HistoryAnalyzer,
                 fantasy_manager: FantasyManager):
        self.history_analyzer = history_analyzer
        self.fantasy_manager = fantasy_manager
        self.current_strategy = None
        self.game_state = {}

    def update_state(self, board: Board, cards: List[Card], 
                    opponent_board: Optional[Board] = None):
        """Обновляет состояние игры для принятия решений"""
        self.game_state = {
            'board': board,
            'cards': cards,
            'opponent_board': opponent_board,
            'in_fantasy': self.fantasy_manager.state.active,
            'cards_played': self._count_cards_played(board, opponent_board),
            'potential_combinations': self._analyze_potential_combinations(cards)
        }

    def choose_strategy(self) -> 'BaseStrategy':
        """Выбирает подходящую стратегию based on текущего состояния"""
        if self.fantasy_manager.state.active:
            return FantasyStrategy(self)
        elif self._should_aim_for_fantasy():
            return FantasySeekingStrategy(self)
        elif self._is_endgame():
            return EndgameStrategy(self)
        return NormalStrategy(self)

    def _should_aim_for_fantasy(self) -> bool:
        """Определяет, стоит ли стремиться к фантазии"""
        if not self.game_state['cards']:
            return False
            
        potential_fantasy = self._evaluate_fantasy_potential(
            self.game_state['cards'],
            self.game_state['board']
        )
        
        return potential_fantasy > 0.7  # порог можно настраивать

    def _is_endgame(self) -> bool:
        """Определяет, находимся ли в эндшпиле"""
        return len(self.game_state['cards_played']) > 40

    def _evaluate_fantasy_potential(self, cards: List[Card], board: Board) -> float:
        """Оценивает потенциал попадания в фантазию"""
        # Используем историю для оценки вероятности
        similar_situations = self.history_analyzer.get_similar_situations(
            cards, board, limit=100
        )
        
        if not similar_situations:
            return 0.0
            
        fantasy_success = sum(1 for sit in similar_situations 
                            if sit.fantasy_achieved)
        return fantasy_success / len(similar_situations)

class BaseStrategy:
    def __init__(self, context: StrategyContext):
        self.context = context

    def choose_move(self, legal_moves: List[Tuple[Card, Street]]) -> Tuple[Card, Street]:
        raise NotImplementedError

class FantasyStrategy(BaseStrategy):
    """Стратегия для игры в фантазии"""
    def def choose_move(self, legal_moves: List[Tuple[Card, Street]]) -> Tuple[Card, Street]:
        """Выбирает ход с приоритетом на сохранение в фантазии"""
        board = self.context.game_state['board']
        
        # Оцениваем каждый возможный ход
        move_scores = []
        for card, street in legal_moves:
            # Симулируем ход
            temp_board = board.copy()
            temp_board.place_card(card, street)
            
            score = self._evaluate_fantasy_move(temp_board, card, street)
            move_scores.append((score, (card, street)))
        
        # Выбираем ход с наивысшей оценкой
        return max(move_scores, key=lambda x: x[0])[1]

    def _evaluate_fantasy_move(self, board: Board, card: Card, street: Street) -> float:
        """Оценивает ход с точки зрения сохранения в фантазии"""
        # Базовая оценка на основе исторических данных
        historical_success = self.context.history_analyzer.get_combination_probability(
            board._get_street(street).cards + [card],
            'fantasy_success'
        )
        
        # Бонус за сохранение валидности расстановки
        validity_bonus = 1.0 if board.is_valid() else 0.0
        
        # Бонус за роялти
        royalty_bonus = board.get_royalties() * 0.1
        
        return historical_success + validity_bonus + royalty_bonus

class FantasySeekingStrategy(BaseStrategy):
    """Стратегия для стремления к фантазии"""
    def choose_move(self, legal_moves: List[Tuple[Card, Street]]) -> Tuple[Card, Street]:
        board = self.context.game_state['board']
        
        # Оцениваем каждый ход с точки зрения потенциала фантазии
        move_scores = []
        for card, street in legal_moves:
            temp_board = board.copy()
            temp_board.place_card(card, street)
            
            score = self._evaluate_fantasy_potential(temp_board, card, street)
            move_scores.append((score, (card, street)))
        
        return max(move_scores, key=lambda x: x[0])[1]

    def _evaluate_fantasy_potential(self, board: Board, card: Card, street: Street) -> float:
        """Оценивает потенциал достижения фантазии"""
        # Анализируем исторические данные
        similar_positions = self.context.history_analyzer.get_similar_positions(board)
        fantasy_rate = sum(1 for pos in similar_positions if pos.reached_fantasy) / len(similar_positions) if similar_positions else 0
        
        # Оцениваем текущую позицию
        current_strength = board.get_royalties() / 6.0  # нормализуем к 1
        
        # Учитываем оставшиеся карты
        remaining_potential = self._evaluate_remaining_potential(board)
        
        return 0.4 * fantasy_rate + 0.4 * current_strength + 0.2 * remaining_potential

class EndgameStrategy(BaseStrategy):
    """Стратегия для конца игры"""
    def choose_move(self, legal_moves: List[Tuple[Card, Street]]) -> Tuple[Card, Street]:
        board = self.context.game_state['board']
        opponent_board = self.context.game_state['opponent_board']
        
        move_scores = []
        for card, street in legal_moves:
            temp_board = board.copy()
            temp_board.place_card(card, street)
            
            score = self._evaluate_endgame_move(temp_board, opponent_board, card, street)
            move_scores.append((score, (card, street)))
        
        return max(move_scores, key=lambda x: x[0])[1]

    def _evaluate_endgame_move(self, board: Board, opponent_board: Board, 
                             card: Card, street: Street) -> float:
        """Оценивает ход в эндшпиле"""
        # Оцениваем прямое преимущество над оппонентом
        street_advantage = self._calculate_street_advantage(
            board._get_street(street),
            opponent_board._get_street(street)
        )
        
        # Оцениваем общий счет
        score_difference = board.get_royalties() - opponent_board.get_royalties()
        
        # Учитываем исторический успех
        historical_success = self.context.history_analyzer.get_combination_probability(
            board._get_street(street).cards + [card],
            'winning_combination'
        )
        
        return 0.4 * street_advantage + 0.3 * (score_difference / 10.0) + 0.3 * historical_success

class NormalStrategy(BaseStrategy):
    """Стандартная стратегия для обычной игры"""
    def choose_move(self, legal_moves: List[Tuple[Card, Street]]) -> Tuple[Card, Street]:
        board = self.context.game_state['board']
        
        move_scores = []
        for card, street in legal_moves:
            temp_board = board.copy()
            temp_board.place_card(card, street)
            
            score = self._evaluate_normal_move(temp_board, card, street)
            move_scores.append((score, (card, street)))
        
        return max(move_scores, key=lambda x: x[0])[1]

    def _evaluate_normal_move(self, board: Board, card: Card, street: Street) -> float:
        """Оценивает ход в обычной ситуации"""
        # Оцениваем силу комбинации
        combination_strength = board._get_street(street).get_rank() / 8000.0  # нормализуем
        
        # Оцениваем потенциал улучшения
        improvement_potential = self._evaluate_improvement_potential(
            board._get_street(street).cards + [card]
        )
        
        # Учитываем исторический успех
        historical_success = self.context.history_analyzer.get_combination_probability(
            board._get_street(street).cards + [card],
            'successful_combination'
        )
        
        return 0.4 * combination_strength + 0.3 * improvement_potential + 0.3 * historical_success
