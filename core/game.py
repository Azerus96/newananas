import os
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from enum import Enum

from core.board import Board, Street
from core.card import Card
from core.deck import Deck
from core.fantasy import FantasyMode, FantasyManager, FantasyStrategy
from analytics.analytics_manager import AnalyticsManager
from agents.base import BaseAgent
from agents.rl.fantasy_agent import FantasyAgent
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
    fantasy_achieved: bool = False

    def get_player_score(self, player: int) -> int:
        return self.player1_score if player == 1 else self.player2_score

class Game:
    def __init__(self, player1: BaseAgent, player2: BaseAgent, 
                 fantasy_mode: FantasyMode = FantasyMode.NORMAL, 
                 seed: Optional[int] = None,
                 think_time: int = 30,
                 save_replays: bool = False):
        self.player1 = player1
        self.player2 = player2
        self.deck = Deck(seed)
        self.state = GameState.WAITING
        self.current_player = 1
        self.player1_board = Board()
        self.player2_board = Board()
        self.player1_cards = []
        self.player2_cards = []
        self.history = []
        self.removed_cards = []
        self.think_time = think_time
        self.save_replays = save_replays
        
        # Компоненты
        self.analytics = AnalyticsManager()
        self.fantasy_manager = FantasyManager(mode=fantasy_mode)
        self.fantasy_strategy = FantasyStrategy(self.fantasy_manager)
        
        # Настройка FantasyAgent
        self.fantasy_agents = []
        if isinstance(player1, FantasyAgent):
            self.fantasy_agents.append((1, player1))
        if isinstance(player2, FantasyAgent):
            self.fantasy_agents.append((2, player2))
            
        logger.info(f"Game initialized with think_time: {think_time}s")

    def start(self) -> None:
        """Начинает новую игру"""
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
        """Выполняет ход игрока"""
        if self.state != GameState.IN_PROGRESS:
            raise ValueError("Game is not in progress")
            
        if player != self.current_player:
            raise ValueError("Not your turn")
            
        try:
            board = self.player1_board if player == 1 else self.player2_board
            cards = self.player1_cards if player == 1 else self.player2_cards
            
            if card not in cards:
                return False
                
            success = board.place_card(card, street)
            
            if success:
                cards.remove(card)
                self.history.append((player, card, street))
                self.analytics.track_move(self, {
                    'player': player,
                    'card': card,
                    'street': street,
                    'think_time': self.think_time
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
                            'fantasy_active': True,
                            'think_time': self.think_time
                        })

                if self._is_round_complete():
                    self._deal_new_cards()
                    
                self._switch_player()
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error making move: {e}")
            return False

    def get_ai_move(self) -> Tuple[Card, Street]:
        """Получает ход от ИИ"""
        player = self.current_player
        agent = self.player2 if player == 2 else self.player1
        cards = self.player2_cards if player == 2 else self.player1_cards
        
        state = self._get_agent_state(player)
        state['think_time'] = self.think_time
        return agent.get_move(state)

    def is_game_over(self) -> bool:
        """Проверяет, закончена ли игра"""
        return (self.player1_board.is_complete() and 
                self.player2_board.is_complete()) or \
               self.state == GameState.COMPLETED

    def get_result(self) -> GameResult:
        """Возвращает результат игры"""
        if not self.is_game_over():
            raise ValueError("Game is not over")
            
        p1_score, p1_royalties = self.player1_board.evaluate()
        p2_score, p2_royalties = self.player2_board.evaluate()
        
        winner = None
        if p1_score > p2_score:
            winner = 1
        elif p2_score > p1_score:
            winner = 2
            
        return GameResult(
            player1_score=p1_score,
            player2_score=p2_score,
            player1_royalties=p1_royalties,
            player2_royalties=p2_royalties,
            player1_board=self.player1_board,
            player2_board=self.player2_board,
            winner=winner,
            fantasy_achieved=self.fantasy_manager.state.fantasy_achieved
        )

    def get_fantasy_status(self) -> Dict:
        """Возвращает текущий статус фантазии"""
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

    def get_fantasy_statistics(self) -> Dict:
        """Возвращает статистику фантазий"""
        return {
            'manager_stats': self.fantasy_manager.get_statistics(),
            'strategy_stats': self.fantasy_strategy.get_strategy_stats()
        }

    def get_move_recommendations(self) -> List[Dict]:
        """Возвращает рекомендации по ходам"""
        return self.analytics.get_move_recommendations(self)

    def get_removed_cards(self) -> List[Card]:
        """Возвращает список удаленных карт"""
        return self.removed_cards

    def _deal_initial_cards(self) -> None:
        """Раздает начальные карты"""
        self.player1_cards = self.deck.draw(5)
        self.player2_cards = self.deck.draw(5)
        logger.info(f"Dealt initial cards: P1 {self.player1_cards}, P2 {self.player2_cards}")

    def _deal_new_cards(self) -> None:
        """Раздает новые карты игрокам"""
        cards_needed = 5 - len(self.player1_cards)
        if cards_needed > 0:
            new_cards = self.deck.draw(cards_needed)
            self.player1_cards.extend(new_cards)
            
        cards_needed = 5 - len(self.player2_cards)
        if cards_needed > 0:
            new_cards = self.deck.draw(cards_needed)
            self.player2_cards.extend(new_cards)
            
        logger.info("Dealt new cards to players")

    def _deal_fantasy_cards(self, player: int, count: int) -> None:
        """Раздает дополнительные карты для фантазии"""
        cards = self.deck.draw(count)
        if player == 1:
            self.player1_cards.extend(cards)
        else:
            self.player2_cards.extend(cards)
        logger.info(f"Dealt {count} fantasy cards to player {player}")

    def _switch_player(self) -> None:
        """Переключает текущего игрока"""
        self.current_player = 3 - self.current_player  # 1 -> 2, 2 -> 1

    def _is_round_complete(self) -> bool:
        """Проверяет, завершен ли текущий раунд"""
        return len(self.player1_cards) == 0 and len(self.player2_cards) == 0

    def _get_agent_state(self, player: int) -> Dict:
        """Возвращает состояние игры для агента"""
        board = self.player1_board if player == 1 else self.player2_board
        opponent_board = self.player2_board if player == 1 else self.player1_board
        cards = self.player1_cards if player == 1 else self.player2_cards
        
        return {
            'board': board,
            'opponent_board': opponent_board,
            'cards': cards,
            'fantasy_active': self.fantasy_manager.state.active,
            'fantasy_mode': self.fantasy_manager.mode,
            'removed_cards': self.removed_cards,
            'deck_remaining': len(self.deck),
            'history': self.history,
            'think_time': self.think_time
        }

    def check_fantasy_entry(self, player: int) -> bool:
        """Проверяет возможность входа в фантазию"""
        board = self.player1_board if player == 1 else self.player2_board
        
        if self.fantasy_manager.check_fantasy_entry(board):
            cards_count = self.fantasy_manager.enter_fantasy()
            self._deal_fantasy_cards(player, cards_count)
            self.analytics.track_fantasy_attempt(True)
            return True
            
        self.analytics.track_fantasy_attempt(False)
        return False

    def get_statistics(self) -> Dict:
        """Возвращает статистику игры"""
        return {
            'game_stats': self.analytics.current_game_stats,
            'session_stats': self.analytics.get_session_statistics(),
            'recommendations': self.get_move_recommendations(),
            'fantasy_stats': self.get_fantasy_statistics(),
            'think_time': self.think_time
        }

    def save_state(self) -> Dict:
        """Сохраняет текущее состояние игры"""
        return {
            'state': self.state.value,
            'current_player': self.current_player,
            'player1_board': self.player1_board.to_dict(),
            'player2_board': self.player2_board.to_dict(),
            'player1_cards': [card.to_dict() for card in self.player1_cards],
            'player2_cards': [card.to_dict() for card in self.player2_cards],
            'history': [(p, c.to_dict(), s.value) for p, c, s in self.history],
            'removed_cards': [card.to_dict() for card in self.removed_cards],
            'fantasy_state': self.fantasy_manager.save_state(),
            'analytics_state': self.analytics.save_state(),
            'think_time': self.think_time,
            'save_replays': self.save_replays
        }

    def load_state(self, state: Dict) -> None:
        """Загружает сохраненное состояние игры"""
        try:
            self.state = GameState(state['state'])
            self.current_player = state['current_player']
            self.player1_board = Board.from_dict(state['player1_board'])
            self.player2_board = Board.from_dict(state['player2_board'])
            self.player1_cards = [Card.from_dict(c) for c in state['player1_cards']]
            self.player2_cards = [Card.from_dict(c) for c in state['player2_cards']]
            self.history = [(p, Card.from_dict(c), Street(s)) for p, c, s in state['history']]
            self.removed_cards = [Card.from_dict(c) for c in state['removed_cards']]
            self.fantasy_manager.load_state(state['fantasy_state'])
            self.analytics.load_state(state['analytics_state'])
            self.think_time = state.get('think_time', 30)
            self.save_replays = state.get('save_replays', False)
            logger.info("Game state loaded successfully")
        except Exception as e:
            logger.error(f"Error loading game state: {e}")
            raise

    def get_state(self) -> Dict:
        """Возвращает текущее состояние игры для клиента"""
        return {
            'state': self.state.value,
            'current_player': self.current_player,
            'player1_board': self.player1_board.to_dict(),
            'player2_board': self.player2_board.to_dict(),
            'player1_cards': [card.to_dict() for card in self.player1_cards],
            'player2_cards': [card.to_dict() for card in self.player2_cards],
            'fantasy_status': self.get_fantasy_status(),
            'think_time': self.think_time,
            'removed_cards': [card.to_dict() for card in self.removed_cards]
        }
