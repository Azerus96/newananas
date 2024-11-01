# analytics/performance_analyzer.py

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from collections import defaultdict

class PerformanceAnalyzer:
    """Анализатор производительности ИИ"""
    
    def __init__(self):
        self.performance_history = defaultdict(list)
        self.current_episode_data = {}
        self.fantasy_stats = defaultdict(int)
        self.combination_stats = defaultdict(lambda: defaultdict(int))
        
    def start_episode(self):
        """Начинает отслеживание нового эпизода"""
        self.current_episode_data = {
            'moves': [],
            'rewards': [],
            'fantasies': 0,
            'fouls': 0,
            'combinations': defaultdict(list)
        }
        
    def record_move(self, state: Dict, action: int, reward: float, 
                   next_state: Dict, done: bool):
        """Записывает информацию о ходе"""
        self.current_episode_data['moves'].append({
            'state': state,
            'action': action,
            'reward': reward,
            'next_state': next_state,
            'done': done
        })
        self.current_episode_data['rewards'].append(reward)
        
    def record_fantasy(self, success: bool):
        """Записывает результат фантазии"""
        self.current_episode_data['fantasies'] += 1
        if success:
            self.fantasy_stats['successful_fantasies'] += 1
        self.fantasy_stats['total_fantasies'] += 1
        
    def record_combination(self, street: str, combination_type: str, 
                         success: bool):
        """Записывает информацию о собранной комбинации"""
        self.current_episode_data['combinations'][street].append({
            'type': combination_type,
            'success': success
        })
        self.combination_stats[street][combination_type] += 1
        
    def end_episode(self) -> Dict:
        """Завершает эпизод и возвращает статистику"""
        episode_stats = {
            'total_reward': sum(self.current_episode_data['rewards']),
            'moves_count': len(self.current_episode_data['moves']),
            'fantasies': self.current_episode_data['fantasies'],
            'fouls': self.current_episode_data['fouls'],
            'combinations': dict(self.current_episode_data['combinations'])
        }
        
        # Обновляем историю
        for key, value in episode_stats.items():
            self.performance_history[key].append(value)
            
        return episode_stats
        
    def get_overall_statistics(self) -> Dict:
        """Возвращает общую статистику"""
        return {
            'average_reward': np.mean(self.performance_history['total_reward']),
            'fantasy_success_rate': (self.fantasy_stats['successful_fantasies'] / 
                                   self.fantasy_stats['total_fantasies']
                                   if self.fantasy_stats['total_fantasies'] > 0 
                                   else 0),
            'combination_success_rates': self._calculate_combination_rates(),
            'learning_curve': self._calculate_learning_curve(),
            'fantasy_stats': dict(self.fantasy_stats),
            'combination_stats': dict(self.combination_stats)
        }
        
    def _calculate_combination_rates(self) -> Dict:
        """Рассчитывает успешность различных комбинаций"""
        rates = {}
        for street, combinations in self.combination_stats.items():
            total = sum(combinations.values())
            rates[street] = {
                combo: count/total
                for combo, count in combinations.items()
            }
        return rates
        
    def _calculate_learning_curve(self, window_size: int = 100) -> pd.Series:
        """Рассчитывает кривую обучения"""
        rewards = pd.Series(self.performance_history['total_reward'])
        return rewards.rolling(window_size).mean()
        
    def get_fantasy_analysis(self) -> Dict:
        """Анализирует игру в фантазии"""
        return {
            'success_rate': (self.fantasy_stats['successful_fantasies'] / 
                           self.fantasy_stats['total_fantasies']
                           if self.fantasy_stats['total_fantasies'] > 0 
                           else 0),
            'average_duration': np.mean([
                len(episode['moves'])
                for episode in self.performance_history
                if episode['fantasies'] > 0
            ]),
            'best_combinations': self._get_best_fantasy_combinations()
        }
        
    def _get_best_fantasy_combinations(self) -> Dict:
        """Определяет наиболее успешные комбинации в фантазии"""
        fantasy_combinations = defaultdict(lambda: {'success': 0, 'total': 0})
        
        for episode in self.performance_history:
            if episode['fantasies'] > 0:
                for street, combos in episode['combinations'].items():
                    for combo in combos:
                        key = f"{street}_{combo['type']}"
                        fantasy_combinations[key]['total'] += 1
                        if combo['success']:
                            fantasy_combinations[key]['success'] += 1
                            
        return {
            key: combo['success'] / combo['total']
            for key, combo in fantasy_combinations.items()
            if combo['total'] > 0
        }
