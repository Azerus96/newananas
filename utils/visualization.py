import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from typing import List, Dict
import json
from pathlib import Path

class Visualizer:
    """Класс для визуализации результатов обучения и игровой статистики"""
    
    def __init__(self, save_dir: str = 'plots'):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
    def plot_training_history(self, history: List[Dict], save_name: str = 'training_history.png'):
        """Строит графики метрик обучения"""
        # Извлекаем метрики
        episodes = range(len(history))
        metrics = {}
        
        for metric in history[0]['metrics'].keys():
            metrics[metric] = [h['metrics'][metric] for h in history]
            
        # Создаем subplot для каждой метрики
        fig, axes = plt.subplots(len(metrics), 1, figsize=(12, 4*len(metrics)))
        if len(metrics) == 1:
            axes = [axes]
            
        for ax, (metric_name, metric_values) in zip(axes, metrics.items()):
            ax.plot(episodes, metric_values)
            ax.set_title(f'Training {metric_name}')
            ax.set_xlabel('Episode')
            ax.set_ylabel(metric_name)
            ax.grid(True)
            
        plt.tight_layout()
        plt.savefig(self.save_dir / save_name)
        plt.close()
        
    def plot_win_rate(self, wins: List[int], window: int = 100, 
                     save_name: str = 'win_rate.png'):
        """Строит график процента побед"""
        win_rate = [
            np.mean(wins[max(0, i-window):i])
            for i in range(1, len(wins)+1)
        ]
        
        plt.figure(figsize=(12, 6))
        plt.plot(win_rate)
        plt.title(f'Win Rate (Moving Average, window={window})')
        plt.xlabel('Episode')
        plt.ylabel('Win Rate')
        plt.grid(True)
        plt.savefig(self.save_dir / save_name)
        plt.close()
        
    def plot_reward_distribution(self, rewards: List[float], 
                               save_name: str = 'reward_dist.png'):
        """Строит распределение наград"""
        plt.figure(figsize=(10, 6))
        sns.histplot(rewards, bins=50)
        plt.title('Reward Distribution')
        plt.xlabel('Reward')
        plt.ylabel('Count')
        plt.savefig(self.save_dir / save_name)
        plt.close()
        
    def plot_learning_curves(self, histories: Dict[str, List[Dict]], 
                           save_name: str = 'learning_curves.png'):
        """Сравнивает кривые обучения разных агентов"""
        plt.figure(figsize=(12, 6))
        
        for agent_name, history in histories.items():
            rewards = [h['metrics'].get('reward', 0) for h in history]
            plt.plot(rewards, label=agent_name)
            
        plt.title('Learning Curves Comparison')
        plt.xlabel('Episode')
        plt.ylabel('Reward')
        plt.legend()
        plt.grid(True)
        plt.savefig(self.save_dir / save_name)
        plt.close()
        
    def save_training_summary(self, summary: Dict, 
                            save_name: str = 'training_summary.json'):
        """Сохраняет итоговую статистику обучения"""
        with open(self.save_dir / save_name, 'w') as f:
            json.dump(summary, f, indent=4)
            
    def plot_game_statistics(self, game_results: List[Dict],
                           save_name: str = 'game_stats.png'):
        """Визуализирует статистику игр"""
        # Извлекаем статистику
        royalties = [g['royalties'] for g in game_results]
        scores = [g['score'] for g in game_results]
        street_wins = {
            'front': [g['street_wins']['front'] for g in game_results],
            'middle': [g['street_wins']['middle'] for g in game_results],
            'back': [g['street_wins']['back'] for g in game_results]
        }
        
        # Создаем подграфики
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # Распределение роялти
        sns.histplot(royalties, bins=20, ax=axes[0,0])
        axes[0,0].set_title('Royalties Distribution')
        
        # Распределение очков
        sns.histplot(scores, bins=20, ax=axes[0,1])
        axes[0,1].set_title('Scores Distribution')
        
        # Процент побед по улицам
        win_rates = {
            street: np.mean(wins) for street, wins in street_wins.items()
        }
        axes[1,0].bar(win_rates.keys(), win_rates.values())
        axes[1,0].set_title('Win Rate by Street')
        axes[1,0].set_ylim(0, 1)
        
        # Корреляция между роялти и итоговым счетом
        axes[1,1].scatter(royalties, scores, alpha=0.5)
        axes[1,1].set_title('Royalties vs Final Score')
        axes[1,1].set_xlabel('Royalties')
        axes[1,1].set_ylabel('Score')
        
        plt.tight_layout()
        plt.savefig(self.save_dir / save_name)
        plt.close()
        
    def create_training_report(self, agent_name: str, config: dict,
                             training_history: List[Dict],
                             game_results: List[Dict],
                             save_name: str = 'training_report.html'):
        """Создает HTML отчет о процессе обучения"""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Training Report - {agent_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .section {{ margin: 20px 0; }}
                .metric {{ margin: 10px 0; }}
                img {{ max-width: 100%; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Training Report - {agent_name}</h1>
            
            <div class="section">
                <h2>Configuration</h2>
                <pre>{config}</pre>
            </div>
            
            <div class="section">
                <h2>Training Metrics</h2>
                <img src="training_history.png" alt="Training History">
                <img src="win_rate.png" alt="Win Rate">
            </div>
            
            <div class="section">
                <h2>Game Statistics</h2>
                <img src="game_stats.png" alt="Game Statistics">
            </div>
            
            <div class="section">
                <h2>Summary</h2>
                <div class="metric">
                    <strong>Total Episodes:</strong> {total_episodes}
                </div>
                <div class="metric">
                    <strong>Final Win Rate:</strong> {win_rate:.2%}
                </div>
                <div class="metric">
                    <strong>Average Score:</strong> {avg_score:.2f}
                </div>
                <div class="metric">
                    <strong>Average Royalties:</strong> {avg_royalties:.2f}
                </div>
            </div>
        </body>
        </html>
        """
        
        # Вычисляем итоговые метрики
        total_episodes = len(training_history)
        win_rate = np.mean([g['won'] for g in game_results[-1000:]])
        avg_score = np.mean([g['score'] for g in game_results[-1000:]])
        avg_royalties = np.mean([g['royalties'] for g in game_results[-1000:]])
        
        # Создаем графики
        self.plot_training_history(training_history)
        self.plot_win_rate([g['won'] for g in game_results])
        self.plot_game_statistics(game_results)
        
        # Формируем отчет
        report = template.format(
            agent_name=agent_name,
            config=json.dumps(config, indent=4),
            total_episodes=total_episodes,
            win_rate=win_rate,
            avg_score=avg_score,
            avg_royalties=avg_royalties
        )
        
        # Сохраняем отчет
        with open(self.save_dir / save_name, 'w') as f:
            f.write(report)
