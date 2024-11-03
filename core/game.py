import os
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from enum import Enum

from core.board import Board, Street
from core.card import Card
from core.deck import Deck
from core.fantasy import FantasyMode, FantasyManager, FantasyStrategy
from core.analytics import AnalyticsManager
from agents.base import BaseAgent
from agents.fantasy import FantasyAgent
from utils.logger import get_logger

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
    winner: Optional[int] = None

    def get_player_score(self, player: int) -> int:
        return self.player1_score if player == 1 else self.player2_score

class Game:
    def __init__(self, player1: BaseAgent, player2: BaseAgent, 
                 fantasy_mode: FantasyMode = FantasyMode.NORMAL, 
                 seed: Optional[int] = None):
        self.player1 = player1
        self.player2 = player2
        self.deck = Deck(seed)
        self.state = GameState.WAITING
        self.current_player = 1
        self.player1_board = Board()
        self.player2_board = Board()
        self.history = []
        
        # Новые компоненты
        self.analytics = AnalyticsManager()
        self.fantasy_manager = FantasyManager(mode=fantasy_mode)
        self.fantasy_strategy = FantasyStrategy(self.fantasy_manager)
        
        # Настройка FantasyAgent
        self.fantasy_agents = []
        if isinstance(player1, FantasyAgent):
            self.fantasy_agents.append((1, player1))
        if isinstance(player2, FantasyAgent):
            self.fantasy_agents.append((2, player2))

    def start(self) -> None:
        try:
            logger.info("Starting new game")
            self.deck.shuffle()
            self._deal_initial_cards()
            self.state = GameState.IN_PROGRESS
            self.analytics.start_game(self)
        except Exception as e:
            logger.error(f"Error starting game: {e}")
            self.state = GameState.ERROR
            raise

    def make_move(self, player: int, card: Card, street: Street) -> bool:
        if self.state != GameState.IN_PROGRESS:
            raise ValueError("Game is not in progress")
            
        if player != self.current_player:
            raise ValueError("Not your turn")
            
        try:
            board = self.player1_board if player == 1 else self.player2_board
            success = board.place_card(card, street)
            
            if success:
                self.history.append((player, card, street))
                self.analytics.track_move(self, {
                    'player': player,
                    'card': card,
                    'street': street
                })

                # Обработка фантазии
                if self.fantasy_manager.state.active:
                    if board.is_complete():
                        fantasy_success = self.fantasy_manager.check_fantasy_entry(board)
                        self.fantasy_manager.exit_fantasy(fantasy_success)
                        self.fantasy_strategy.update_statistics(board, fantasy_success)

                # Обновление FantasyAgent
                for player_id, agent in self.fantasy_agents:
                    if player == player_id and self.fantasy_manager.state.active:
                        agent.fantasy_history.append({
                            'state': self._get_agent_state(player),
                            'move': (card, street),
                            'fantasy_active': True
                        })

                if self._is_round_complete():
                    self._deal_new_cards()
                    
                self._switch_player()
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error making move: {e}")
            return False

    # ... (остальные существующие методы остаются без изменений)

    def check_fantasy_entry(self, player: int) -> bool:
        board = self.player1_board if player == 1 else self.player2_board
        
        if self.fantasy_manager.check_fantasy_entry(board):
            cards_count = self.fantasy_manager.enter_fantasy()
            self._deal_fantasy_cards(player, cards_count)
            self.analytics.track_fantasy_attempt(True)
            return True
            
        return False

    def _deal_fantasy_cards(self, player: int, count: int):
        cards = self.deck.draw(count)
        if player == 1:
            self.player1_cards.extend(cards)
        else:
            self.player2_cards.extend(cards)

    def get_fantasy_status(self) -> Dict:
        return {
            'active': self.fantasy_manager.state.active,
            'mode': self.fantasy_manager.mode.value,
            'cards_count': self.fantasy_manager.state.cards_count,
            'consecutive_fantasies': self.fantasy_manager.state.consecutive_fantasies,
            'progressive_bonus': (
                self.fantasy_manager.state.progressive_bonus.name
                if self.fantasy_manager.state.progressive_bonus
                else None
            )
        }

    def get_statistics(self) -> Dict:
        return {
            'game_stats': self.analytics.current_game_stats,
            'session_stats': self.analytics.get_session_statistics(),
            'recommendations': self.get_move_recommendations(),
            'fantasy_stats': self.get_fantasy_statistics()
        }

    def get_fantasy_statistics(self) -> Dict:
        return {
            'manager_stats': self.fantasy_manager.get_statistics(),
            'strategy_stats': self.fantasy_strategy.get_strategy_stats()
        }

    def _get_agent_state(self, player: int) -> Dict:
        board = self.player1_board if player == 1 else self.player2_board
        opponent_board = self.player2_board if player == 1 else self.player1_board
        cards = self.player1_cards if player == 1 else self.player2_cards
        
        return {
            'board': board,
            'opponent_board': opponent_board,
            'cards': cards,
            'fantasy_active': self.fantasy_manager.state.active,
            'fantasy_mode': self.fantasy_manager.mode
        }

# Настройка Flask
from flask import Flask, request, jsonify

app = Flask(__name__)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
