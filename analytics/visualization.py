# analytics/visualization.py

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from typing import Dict, List
import numpy as np

class PerformanceVisualizer:
    def __init__(self):
        self.style_setup()

    @staticmethod
    def style_setup():
        """Настраивает стиль графиков"""
        plt.style.use('seaborn')
        sns.set_palette("husl")

    def plot_learning_curve(self, 
                          stats: Dict[str, List[float]], 
                          window_size: int = 100):
        """Отображает кривую обучения"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

        # Сглаживаем данные
        rewards = pd.Series(stats['rewards']).rolling(window_size).mean()
        losses = pd.Series(stats['losses']).rolling(window_size).mean()

        # График наград
        ax1.plot(rewards, label='Average Reward')
        ax1.fill_between(rewards.index, 
                        rewards - rewards.std(), 
                        rewards + rewards.std(), 
                        alpha=0.2)
        ax1.set_title('Learning Curve - Rewards')
        ax1.set_xlabel('Episode')
        ax1.set_ylabel('Reward')
        ax1.legend()

        # График потерь
        ax2.plot(losses, label='Loss', color='orange')
        ax2.set_title('Learning Curve - Loss')
        ax2.set_xlabel('Episode')
        ax2.set_ylabel('Loss')
        ax2.legend()

        plt.tight_layout()
        return fig

    def plot_fantasy_statistics(self, stats: Dict):
        """Визуализирует статистику фантазий"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))

        # График успешности фантазий
        fantasy_success = pd.Series(stats['fantasy_success_rate'])
        ax1.plot(fantasy_success.rolling(50).mean(), label='Success Rate')
        ax1.set_title('Fantasy Success Rate')
        ax1.set_xlabel('Game')
        ax1.set_ylabel('Success Rate')
        ax1.legend()

        # Распределение длин серий фантазий
        fantasy_streaks = pd.Series(stats['fantasy_streaks'])
        sns.histplot(fantasy_streaks, ax=ax2, bins=20)
        ax2.set_title('Fantasy Streak Distribution')
        ax2.set_xlabel('Streak Length')
        ax2.set_ylabel('Count')

        plt.tight_layout()
        return fig

    def plot_combination_heatmap(self, combination_stats: Dict):
        """Создает тепловую карту успешности комбинаций"""
        data = pd.DataFrame(combination_stats)
        plt.figure(figsize=(12, 8))
        sns.heatmap(data, annot=True, fmt='.2f', cmap='YlOrRd')
        plt.title('Combination Success Rates')
        plt.xlabel('Street')
        plt.ylabel('Combination Type')
        return plt.gcf()

    def create_performance_dashboard(self, stats: Dict):
        """Создает комплексную панель статистики"""
        fig = plt.figure(figsize=(15, 10))
        gs = fig.add_gridspec(3, 3)

        # Основные метрики
        ax1 = fig.add_subplot(gs[0, :])
        self._plot_main_metrics(ax1, stats)

        # Распределение выигрышей
        ax2 = fig.add_subplot(gs[1, 0])
        self._plot_win_distribution(ax2, stats)

        # Типы комбинаций
        ax3 = fig.add_subplot(gs[1, 1:])
        self._plot_combination_types(ax3, stats)

        # Прогресс обучения
        ax4 = fig.add_subplot(gs[2, :])
        self._plot_learning_progress(ax4, stats)

        plt.tight_layout()
        return fig

    def _plot_main_metrics(self, ax, stats):
        """Отображает основные метрики производительности"""
        metrics = pd.DataFrame({
            'Win Rate': stats['win_rate'],
            'Fantasy Rate': stats['fantasy_rate'],
            'Royalty Rate': stats['royalty_rate']
        }, index=range(len(stats['win_rate'])))
        
        # analytics/visualization.py (продолжение)

        metrics.rolling(50).mean().plot(ax=ax)
        ax.set_title('Main Performance Metrics')
        ax.set_xlabel('Games')
        ax.set_ylabel('Rate')
        ax.legend()

    def _plot_win_distribution(self, ax, stats):
        """Отображает распределение выигрышей"""
        wins = pd.Series(stats['points_scored'])
        sns.histplot(wins, ax=ax, bins=20)
        ax.axvline(wins.mean(), color='r', linestyle='--', label='Mean')
        ax.set_title('Points Distribution')
        ax.set_xlabel('Points')
        ax.legend()

    def _plot_combination_types(self, ax, stats):
        """Отображает частоту различных типов комбинаций"""
        combinations = pd.DataFrame(stats['combination_types'])
        combinations.plot(kind='bar', stacked=True, ax=ax)
        ax.set_title('Combination Types by Street')
        ax.set_xlabel('Street')
        ax.set_ylabel('Count')
        plt.xticks(rotation=45)

    def _plot_learning_progress(self, ax, stats):
        """Отображает прогресс обучения"""
        progress = pd.Series(stats['learning_progress'])
        progress.plot(ax=ax)
        ax.set_title('Learning Progress')
        ax.set_xlabel('Training Episodes')
        ax.set_ylabel('Performance Score')

class RealTimeVisualizer:
    """Визуализатор для отображения игры в реальном времени"""
    
    def __init__(self):
        self.fig, self.axes = plt.subplots(2, 2, figsize=(15, 10))
        self.setup_plots()
        
    def setup_plots(self):
        """Инициализирует области графиков"""
        self.current_game_ax = self.axes[0, 0]
        self.stats_ax = self.axes[0, 1]
        self.history_ax = self.axes[1, 0]
        self.prediction_ax = self.axes[1, 1]
        
        self.fig.canvas.draw()
        plt.tight_layout()
        
    def update_game_state(self, game_state: Dict):
        """Обновляет отображение текущего состояния игры"""
        self.current_game_ax.clear()
        self._draw_game_board(self.current_game_ax, game_state)
        self.fig.canvas.draw()
        
    def update_statistics(self, stats: Dict):
        """Обновляет статистику в реальном времени"""
        self.stats_ax.clear()
        self._draw_statistics(self.stats_ax, stats)
        self.fig.canvas.draw()
        
    def update_history(self, history: List[Dict]):
        """Обновляет график истории игр"""
        self.history_ax.clear()
        self._draw_history(self.history_ax, history)
        self.fig.canvas.draw()
        
    def update_predictions(self, predictions: Dict):
        """Обновляет отображение предсказаний ИИ"""
        self.prediction_ax.clear()
        self._draw_predictions(self.prediction_ax, predictions)
        self.fig.canvas.draw()
        
    def _draw_game_board(self, ax, game_state):
        """Отрисовывает игровое поле"""
        # Создаем сетку для карт
        grid = np.zeros((3, 5))
        
        # Заполняем сетку картами
        for street, cards in game_state['board'].items():
            row = {'front': 0, 'middle': 1, 'back': 2}[street]
            for i, card in enumerate(cards):
                grid[row, i] = card.value
                
        # Отображаем сетку
        sns.heatmap(grid, ax=ax, cmap='YlOrRd', annot=True, fmt='.0f',
                   xticklabels=False, yticklabels=['Front', 'Middle', 'Back'])
        ax.set_title('Current Game State')
        
    def _draw_statistics(self, ax, stats):
        """Отрисовывает текущую статистику"""
        metrics = {
            'Win Rate': stats['win_rate'][-1],
            'Fantasy Rate': stats['fantasy_rate'][-1],
            'Avg Points': stats['avg_points'][-1],
            'Best Combo': stats['best_combo']
        }
        
        y_pos = np.arange(len(metrics))
        ax.barh(y_pos, list(metrics.values()))
        ax.set_yticks(y_pos)
        ax.set_yticklabels(list(metrics.keys()))
        ax.set_title('Current Statistics')
        
    def _draw_history(self, ax, history):
        """Отрисовывает историю игр"""
        games = range(len(history))
        points = [game['points'] for game in history]
        
        ax.plot(games, points, '-o')
        ax.set_title('Points History')
        ax.set_xlabel('Game')
        ax.set_ylabel('Points')
        
    def _draw_predictions(self, ax, predictions):
        """Отрисовывает предсказания ИИ"""
        moves = list(predictions.keys())
        probabilities = list(predictions.values())
        
        ax.barh(moves, probabilities)
        ax.set_title('AI Move Predictions')
        ax.set_xlabel('Probability')

class TrainingVisualizer:
    """Визуализатор для режима тренировки"""
    
    def __init__(self):
        self.fig = plt.figure(figsize=(15, 10))
        self.setup_plots()
        
    def setup_plots(self):
        """Настраивает области для визуализации тренировки"""
        gs = self.fig.add_gridspec(3, 2)
        
        self.training_progress_ax = self.fig.add_subplot(gs[0, :])
        self.loss_ax = self.fig.add_subplot(gs[1, 0])
        self.reward_ax = self.fig.add_subplot(gs[1, 1])
        self.fantasy_stats_ax = self.fig.add_subplot(gs[2, 0])
        self.combination_stats_ax = self.fig.add_subplot(gs[2, 1])
        
        plt.tight_layout()
        
    def update(self, training_stats: Dict):
        """Обновляет все графики"""
        self._update_training_progress(training_stats)
        self._update_loss_plot(training_stats)
        self._update_reward_plot(training_stats)
        self._update_fantasy_stats(training_stats)
        self._update_combination_stats(training_stats)
        
        self.fig.canvas.draw()
        
    def _update_training_progress(self, stats):
        """Обновляет график прогресса обучения"""
        self.training_progress_ax.clear()
        episodes = range(len(stats['episode_rewards']))
        self.training_progress_ax.plot(episodes, stats['episode_rewards'])
        self.training_progress_ax.set_title('Training Progress')
        self.training_progress_ax.set_xlabel('Episode')
        self.training_progress_ax.set_ylabel('Total Reward')
        
    def _update_loss_plot(self, stats):
        """Обновляет график функции потерь"""
        self.loss_ax.clear()
        self.loss_ax.plot(stats['losses'])
        self.loss_ax.set_title('Loss Function')
        # analytics/visualization.py (продолжение)

        self.loss_ax.set_xlabel('Training Step')
        self.loss_ax.set_ylabel('Loss')
        
    def _update_reward_plot(self, stats):
        """Обновляет график наград"""
        self.reward_ax.clear()
        rewards = pd.Series(stats['episode_rewards']).rolling(100).mean()
        self.reward_ax.plot(rewards, label='Average Reward')
        self.reward_ax.fill_between(
            rewards.index,
            rewards - rewards.std(),
            rewards + rewards.std(),
            alpha=0.2
        )
        self.reward_ax.set_title('Rolling Average Reward')
        self.reward_ax.set_xlabel('Episode')
        self.reward_ax.set_ylabel('Reward')
        self.reward_ax.legend()
        
    def _update_fantasy_stats(self, stats):
        """Обновляет статистику фантазий"""
        self.fantasy_stats_ax.clear()
        fantasy_data = pd.DataFrame({
            'Fantasy Success': stats['fantasy_success_rate'],
            'Fantasy Attempts': stats['fantasy_attempts']
        })
        fantasy_data.plot(kind='bar', ax=self.fantasy_stats_ax)
        self.fantasy_stats_ax.set_title('Fantasy Statistics')
        self.fantasy_stats_ax.set_xlabel('Training Phase')
        self.fantasy_stats_ax.set_ylabel('Rate')
        plt.xticks(rotation=45)
        
    def _update_combination_stats(self, stats):
        """Обновляет статистику комбинаций"""
        self.combination_stats_ax.clear()
        combinations = pd.DataFrame(stats['combination_success'])
        sns.heatmap(combinations, 
                   ax=self.combination_stats_ax,
                   annot=True,
                   fmt='.2f',
                   cmap='YlOrRd')
        self.combination_stats_ax.set_title('Combination Success Rates')
