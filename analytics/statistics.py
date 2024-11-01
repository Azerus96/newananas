# analytics/statistics.py

from dataclasses import dataclass
from typing import List, Dict, Optional
from collections import defaultdict
import numpy as np
import pandas as pd

@dataclass
class PlayerStats:
    games_played: int = 0
    games_won: int = 0
    fantasies_entered: int = 0
    fantasies_completed: int = 0
    fouls: int = 0
    royalties_earned: int = 0
    best_combinations: Dict[str, int] = defaultdict(int)
    points_history: List[int] = []

class StatisticsManager:
    def __init__(self):
        self.players_stats: Dict[str, PlayerStats] = defaultdict(PlayerStats)
        self.game_history: List[Dict] = []
        self.combination_stats = defaultdict(lambda: defaultdict(int))

    def record_game(self, game_result, player_id: str):
        """Записывает результаты игры"""
        stats = self.players_stats[player_id]
        stats.games_played += 1
        
        if game_result.winner == player_id:
            stats.games_won += 1
        
        stats.points_history.append(game_result.score)
        stats.royalties_earned += game_result.royalties
        
        if game_result.foul:
            stats.fouls += 1
            
        self._update_combination_stats(game_result.combinations, player_id)
        self._record_game_history(game_result, player_id)

    def get_player_analytics(self, player_id: str) -> Dict:
        """Возвращает аналитику по игроку"""
        stats = self.players_stats[player_id]
        return {
            'win_rate': stats.games_won / stats.games_played if stats.games_played > 0 else 0,
            'fantasy_success_rate': stats.fantasies_completed / stats.fantasies_entered 
                                  if stats.fantasies_entered > 0 else 0,
            'foul_rate': stats.fouls / stats.games_played if stats.games_played > 0 else 0,
            'avg_royalties': stats.royalties_earned / stats.games_played 
                           if stats.games_played > 0 else 0,
            'best_combinations': dict(stats.best_combinations),
            'points_trend': self._calculate_trend(stats.points_history),
            'recent_performance': self._get_recent_performance(player_id)
        }

    def _update_combination_stats(self, combinations: Dict, player_id: str):
        """Обновляет статистику комбинаций"""
        for position, combo in combinations.items():
            self.combination_stats[player_id][f"{position}_{combo.type}"] += 1
            
            if combo.is_royalty:
                self.players_stats[player_id].best_combinations[combo.type] += 1

    def _calculate_trend(self, history: List[int], window: int = 10) -> float:
        """Рассчитывает тренд производительности"""
        if len(history) < window:
            return 0
        return np.mean(history[-window:]) - np.mean(history[:-window])

    def _get_recent_performance(self, player_id: str, games: int = 10) -> Dict:
        """Анализирует последние игры"""
        recent_games = self.game_history[-games:]
        return {
            'wins': sum(1 for game in recent_games 
                       if game['player_id'] == player_id and game['won']),
            'avg_score': np.mean([game['score'] for game in recent_games 
                                if game['player_id'] == player_id]),
            'fantasy_rate': sum(1 for game in recent_games 
                              if game['player_id'] == player_id and game['fantasy'])
        }

    def export_statistics(self) -> pd.DataFrame:
        """Экспортирует статистику в pandas DataFrame"""
        return pd.DataFrame([
            {
                'player_id': player_id,
                **self.get_player_analytics(player_id)
            }
            for player_id in self.players_stats.keys()
        ])
