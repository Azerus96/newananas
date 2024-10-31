from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum

from .board import Board, Street
from .card import Card
from .deck import Deck
from ..agents.base import BaseAgent
from ..utils.logger import get_logger

logger = get_logger(__name__)

class GameState(Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class GameResult:
    player1_score: int
    player2_score: int
    player1_royalties: int
    player2_royalties: int
    player1_board: Board
    player2_board: Board
    winner: Optional[int] = None  # 1 или 2 для победителя, None для ничьей

class Game:
    """Основной класс игры"""
    
    def __init__(self, player1: BaseAgent, player2: BaseAgent, seed: Optional[int] = None):
        self.player1 = player1
        self.player2 = player2
        self.deck = Deck(seed)
        self.state = GameState.WAITING
        self.current_player = 1
        self.player1_board = Board()
        self.player2_board = Board()
        self.history = []
        
    def start(self) -> None:
        """Начинает новую игру"""
        try:
            logger.info("Starting new game")
            self.deck.shuffle()
            self._deal_initial_cards()
            self.state = GameState.IN_PROGRESS
        except Exception as e:
            logger.error(f"Error starting game: {e}")
            self.state = GameState.ERROR
            raise
            
    def _deal_initial_cards(self) -> None:
        """Раздает начальные карты игрокам"""
        self.player1_cards = self.deck.draw(5)
        self.player2_cards = self.deck.draw(5)
        
    def make_move(self, player: int, card: Card, street: Street) -> bool:
        """Выполняет ход игрока"""
        if self.state != GameState.IN_PROGRESS:
            raise ValueError("Game is not in progress")
            
        if player != self.current_player:
            raise ValueError("Not your turn")
            
        try:
            board = self.player1_board if player == 1 else self.player2_board
            board.place_card(card, street)
            self.history.append((player, card, street))
            
            if self._is_round_complete():
                self._deal_new_cards()
                
            self._switch_player()
            return True
            
        except Exception as e:
            logger.error(f"Error making move: {e}")
            return False
            
    def _switch_player(self) -> None:
        """Переключает текущего игрока"""
        self.current_player = 3 - self.current_player  # 1 -> 2, 2 -> 1
        
    def _is_round_complete(self) -> bool:
        """Проверяет, завершен ли текущий раунд"""
        return (not self.player1_cards and not self.player2_cards)
        
    def _deal_new_cards(self) -> None:
        """Раздает новые карты для следующего раунда"""
        if self.deck.cards_remaining() >= 2:
            self.player1_cards = self.deck.draw(1)
            self.player2_cards = self.deck.draw(1)
            
    def is_game_over(self) -> bool:
        """Проверяет, закончена ли игра"""
        return (
            self.player1_board.is_complete() and 
            self.player2_board.is_complete()
        )
        
    def get_result(self) -> GameResult:
        """Подсчитывает и возвращает результат игры"""
        if not self.is_game_over():
            raise ValueError("Game is not over")
            
        p1_royalties = self.player1_board.get_royalties()
        p2_royalties = self.player2_board.get_royalties()
        
        p1_score = 0
        p2_score = 0
        
        # Проверяем фолы
        if not self.player1_board.is_valid() and not self.player2_board.is_valid():
            winner = None
        elif not self.player1_board.is_valid():
            p2_score = 6 + p2_royalties
            winner = 2
        elif not self.player2_board.is_valid():
            p1_score = 6 + p1_royalties
            winner = 1
        else:
            # Считаем очки за улицы
            for street in Street:
                p1_hand = self.player1_board._get_street(street)
                p2_hand = self.player2_board._get_street(street)
                
                if p1_hand.get_rank() < p2_hand.get_rank():
                    p1_score += 1
                elif p1_hand.get_rank() > p2_hand.get_rank():
                    p2_score += 1
                    
            # Добавляем роялти
            p1_score += p1_royalties
            p2_score += p2_royalties
            
            # Определяем победителя
            if p1_score > p2_score:
                winner = 1
            elif p2_score > p1_score:
                winner = 2
            else:
                winner = None
                
        return GameResult(
            player1_score=p1_score,
            player2_score=p2_score,
            player1_royalties=p1_royalties,
            player2_royalties=p2_royalties,
            player1_board=self.player1_board,
            player2_board=self.player2_board,
            winner=winner
        )
        
    def get_legal_moves(self, player: int) -> List[Tuple[Card, Street]]:
        """Возвращает список доступных ходов для игрока"""
        board = self.player1_board if player == 1 else self.player2_board
        cards = self.player1_cards if player == 1 else self.player2_cards
        
        return [
            (card, street)
            for card in cards
            for street in board.get_free_streets()
        ]
