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

# analytics/performance_analyzer.py (продолжение)

    def analyze_fantasy_strategies(self) -> Dict:
        """Анализирует эффективность различных стратегий в фантазии"""
        strategies = defaultdict(lambda: {'success': 0, 'total': 0})
        
        for episode in self.performance_history:
            if episode['fantasies'] > 0:
                moves = episode['moves']
                for move in moves:
                    if move['state'].get('in_fantasy'):
                        strategy_type = self._identify_strategy(move)
                        strategies[strategy_type]['total'] += 1
                        if move['reward'] > 0:
                            strategies[strategy_type]['success'] += 1
        
        return {
            strategy: {
                'success_rate': stats['success'] / stats['total'],
                'usage_rate': stats['total'] / sum(s['total'] for s in strategies.values())
            }
            for strategy, stats in strategies.items()
        }
    
    def _identify_strategy(self, move: Dict) -> str:
        """Определяет тип стратегии по ходу"""
        if move['state'].get('trying_for_royalty'):
            return 'royalty_focused'
        elif move['state'].get('defensive_play'):
            return 'defensive'
        elif move['state'].get('aggressive_play'):
            return 'aggressive'
        return 'balanced'

    def get_training_recommendations(self) -> List[str]:
        """Генерирует рекомендации по улучшению обучения"""
        recommendations = []
        stats = self.get_overall_statistics()
        
        # Анализ фантазий
        if stats['fantasy_success_rate'] < 0.3:
            recommendations.append(
                "Необходимо улучшить стратегию игры в фантазии. "
                "Рассмотрите увеличение приоритета сохранения позиции."
            )
        
        # Анализ комбинаций
        for street, rates in stats['combination_success_rates'].items():
            worst_combo = min(rates.items(), key=lambda x: x[1])
            if worst_combo[1] < 0.2:
                recommendations.append(
                    f"Низкая успешность комбинации {worst_combo[0]} на {street}. "
                    "Требуется дополнительное обучение."
                )
        
        # Анализ обучения
        learning_curve = self._calculate_learning_curve()
        if len(learning_curve) > 1000 and (learning_curve[-1] - learning_curve[-1000]) < 0.1:
            recommendations.append(
                "Обучение застопорилось. Рекомендуется обновить параметры "
                "или изменить структуру модели."
            )
        
        return recommendations

    def export_detailed_report(self) -> Dict:
        """Создает подробный отчет о производительности"""
        return {
            'overall_statistics': self.get_overall_statistics(),
            'fantasy_analysis': self.get_fantasy_analysis(),
            'strategy_analysis': self.analyze_fantasy_strategies(),
            'recommendations': self.get_training_recommendations(),
            'learning_progress': {
                'reward_history': self.performance_history['total_reward'],
                'fantasy_progress': self._get_fantasy_progress(),
                'combination_mastery': self._get_combination_mastery()
            }
        }
    
    def _get_fantasy_progress(self) -> Dict:
        """Анализирует прогресс в игре в фантазии"""
        episodes = len(self.performance_history['total_reward'])
        window_size = min(100, episodes // 10)
        
        fantasy_success = pd.Series([
            1 if episode['fantasies'] > 0 and episode['total_reward'] > 0 else 0
            for episode in self.performance_history
        ])
        
        return {
            'success_rate_trend': fantasy_success.rolling(window_size).mean().tolist(),
            'total_fantasies': self.fantasy_stats['total_fantasies'],
            'successful_fantasies': self.fantasy_stats['successful_fantasies'],
            'average_reward_in_fantasy': np.mean([
                episode['total_reward']
                for episode in self.performance_history
                if episode['fantasies'] > 0
            ])
        }
    
    def _get_combination_mastery(self) -> Dict:
        """Оценивает освоение различных комбинаций"""
        mastery = defaultdict(dict)
        
        for street, combinations in self.combination_stats.items():
            total_attempts = sum(combinations.values())
            for combo_type, count in combinations.items():
                success_rate = count / total_attempts if total_attempts > 0 else 0
                mastery[street][combo_type] = {
                    'attempts': count,
                    'success_rate': success_rate,
                    'mastery_level': self._calculate_mastery_level(success_rate, count)
                }
        
        return dict(mastery)
    
    def _calculate_mastery_level(self, success_rate: float, attempts: int) -> str:
        """Определяет уровень освоения комбинации"""
        if attempts < 10:
            return "Недостаточно данных"
        elif success_rate < 0.3:
            return "Начальный"
        elif success_rate < 0.6:
            return "Развивающийся"
        elif success_rate < 0.8:
            return "Продвинутый"
        else:
            return "Мастерский"

    def save_analytics(self, filepath: str):
        """Сохраняет аналитику в файл"""
        report = self.export_detailed_report()
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=4)
