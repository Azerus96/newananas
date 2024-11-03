# analytics/analytics_manager.py

from typing import Dict, Optional
from pathlib import Path
import json
import threading
from datetime import datetime

from card_tracker import CardTracker
from core.game import Game, GameResult
from utils.logger import get_logger

logger = get_logger(__name__)

class AnalyticsManager:
    """Управляет сбором и анализом игровой статистики"""
    
    def __init__(self, save_dir: str = 'data/analytics'):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        self.card_tracker = CardTracker()
        self.current_game_stats = {}
        self.session_stats = {
            'games_played': 0,
            'wins': 0,
            'fantasies': 0,
            'start_time': datetime.now().isoformat()
        }
        
        self._lock = threading.Lock()
        self._load_existing_data()
    
    def _load_existing_data(self):
        """Загружает существующую статистику"""
        try:
            stats_file = self.save_dir / 'card_statistics.json'
            if stats_file.exists():
                self.card_tracker.load_statistics(str(stats_file))
                logger.info("Loaded existing card statistics")
        except Exception as e:
            logger.error(f"Error loading existing statistics: {e}")
    
    def start_game(self, game: Game):
        """Начинает отслеживание новой игры"""
        with self._lock:
            self.current_game_stats = {
                'start_time': datetime.now(),
                'moves': [],
                'fantasy_attempts': 0,
                'cards_played': set()
            }
            self.session_stats['games_played'] += 1
    
    def track_move(self, game: Game, move: Dict):
        """Отслеживает ход в игре"""
        with self._lock:
            self.current_game_stats['moves'].append({
                'timestamp': datetime.now().isoformat(),
                'move': move,
                'board_state': game.get_board_state(),
                'fantasy_active': game.is_fantasy_active()
            })
            
            if 'card' in move:
                self.current_game_stats['cards_played'].add(move['card'])
    
    def track_fantasy_attempt(self, success: bool):
        """Отслеживает попытку фантазии"""
        with self._lock:
            self.current_game_stats['fantasy_attempts'] += 1
            if success:
                self.session_stats['fantasies'] += 1
    
    def end_game(self, result: GameResult):
        """Завершает отслеживание игры"""
        with self._lock:
            game_stats = {
                'duration': (datetime.now() - 
                           self.current_game_stats['start_time']).total_seconds(),
                'moves_count': len(self.current_game_stats['moves']),
                'fantasy_attempts': self.current_game_stats['fantasy_attempts'],
                'cards_played': list(self.current_game_stats['cards_played']),
                'result': {
                    'winner': result.winner,
                    'player1_score': result.player1_score,
                    'player2_score': result.player2_score,
                    'player1_royalties': result.player1_royalties,
                    'player2_royalties': result.player2_royalties
                }
            }
            
            # Обновляем статистику карт
            self.card_tracker.track_game(game_stats)
            
            # Обновляем статистику сессии
            if result.winner == 1:
                self.session_stats['wins'] += 1
            
            # Сохраняем статистику
            self._save_statistics()
            
            return game_stats
    
    def get_move_recommendations(self, game: Game, available_cards: List[Card]) -> Dict:
        """Получает рекомендации по ходам"""
        with self._lock:
            return self.card_tracker.get_card_suggestions(
                current_board=game.get_current_board(),
                available_cards=available_cards,
                fantasy_mode=game.is_fantasy_active()
            )
    
    def get_session_statistics(self) -> Dict:
        """Возвращает статистику текущей сессии"""
        with self._lock:
            return {
                **self.session_stats,
                'win_rate': (self.session_stats['wins'] / 
                            self.session_stats['games_played']
                            if self.session_stats['games_played'] > 0 
                            else 0),
                'fantasy_rate': (self.session_stats['fantasies'] / 
                               self.session_stats['games_played']
                               if self.session_stats['games_played'] > 0 
                               else 0),
                'duration': (datetime.now() - 
                           datetime.fromisoformat(self.session_stats['start_time'])
                           ).total_seconds()
            }
    
    def get_detailed_statistics(self) -> Dict:
        """Возвращает подробную статистику"""
        with self._lock:
            return {
                'session_stats': self.get_session_statistics(),
                'card_stats': self.card_tracker.get_overall_statistics(),
                'patterns': self.card_tracker.analyze_game_patterns()
            }
    
    def _save_statistics(self):
        """Сохраняет текущую статистику"""
        try:
            # Сохраняем статистику карт
            stats_file = self.save_dir / 'card_statistics.json'
            self.card_tracker.save_statistics(str(stats_file))
            
            # Сохраняем статистику сессии
            session_file = self.save_dir / 'session_statistics.json'
            with open(session_file, 'w') as f:
                json.dump(self.session_stats, f, indent=4)
                
            logger.info("Statistics saved successfully")
        except Exception as e:
            logger.error(f"Error saving statistics: {e}")
    
    def reset_session(self):
        """Сбрасывает статистику текущей сессии"""
        with self._lock:
            self.session_stats = {
                'games_played': 0,
                'wins': 0,
                'fantasies': 0,
                'start_time': datetime.now().isoformat()
            }
            self.current_game_stats = {}
