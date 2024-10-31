from typing import List, Dict, Any
import numpy as np
from datetime import datetime
import json
import os

from ..agents.base import BaseAgent
from ..core.game import Game
from ..utils.logger import get_logger
from ..utils.config import Config

logger = get_logger(__name__)

class Trainer:
    """Класс для обучения агентов"""
    
    def __init__(self, agent: BaseAgent, config: Config):
        self.agent = agent
        self.config = config
        self.training_history = []
        
        # Создаем директории для сохранения
        self.setup_directories()
        
    def setup_directories(self) -> None:
        """Создает необходимые директории"""
        paths = self.config.get('paths', {})
        os.makedirs(paths.get('models', 'models'), exist_ok=True)
        os.makedirs(paths.get('logs', 'logs'), exist_ok=True)
        os.makedirs(paths.get('checkpoints', 'checkpoints'), exist_ok=True)
        
    def train(self, opponent: BaseAgent, num_episodes: int) -> Dict[str, Any]:
        """Обучает агента против оппонента"""
        logger.info(f"Starting training for {num_episodes} episodes")
        
        episode_rewards = []
        episode_wins = []
        
        for episode in range(num_episodes):
            # Создаем новую игру
            game = Game(self.agent, opponent)
            game.start()
            
            # Играем до конца
            while not game.is_game_over():
                if game.current_player == 1:
                    # Ход нашего агента
                    state = self._get_state(game)
                    legal_moves = game.get_legal_moves(1)
                    
                    action = self.agent.choose_move(
                        game.player1_board,
                        game.player1_cards,
                        legal_moves,
                        game.player2_board
                    )
                    
                    # Делаем ход
                    game.make_move(1, *action)
                    
                    # Получаем новое состояние
                    next_state = self._get_state(game)
                    
                    # Сохраняем опыт
                    if hasattr(self.agent, 'remember'):
                        reward = self._get_reward(game)
                        done = game.is_game_over()
                        self.agent.remember(state, action, reward, next_state, done)
                        
                else:
                    # Ход оппонента
                    legal_moves = game.get_legal_moves(2)
                    action = opponent.choose_move(
                        game.player2_board,
                        game.player2_cards,
                        legal_moves,
                        game.player1_board
                    )
                    game.make_move(2, *action)
            
            # Игра закончена
            result = game.get_result()
            
            # Сохраняем результаты
            episode_rewards.append(result.player1_score)
            episode_wins.append(1 if result.winner == 1 else 0)
            
            # Обучаем на собранном опыте
            if hasattr(self.agent, 'replay'):
                metrics = self.agent.replay(
                    self.config.get('training.batch_size', 32)
                )
                self._update_history(metrics)
            
            # Логируем прогресс
            if (episode + 1) % self.config.get('training.log_interval', 100) == 0:
                self._log_progress(episode + 1, episode_rewards, episode_wins)
                
            # Сохраняем чекпоинт
            if (episode + 1) % self.config.get('training.checkpoint_interval', 1000) == 0:
                self.save_checkpoint(episode + 1)
                
        # Сохраняем финальную модель
        self.save_model()
        
        return self._get_training_summary(episode_rewards, episode_wins)
    
    def _get_state(self, game: Game) -> np.ndarray:
        """Получает текущее состояние игры"""
        if hasattr(self.agent, 'encode_state'):
            return self.agent.encode_state(
                game.player1_board,
                game.player1_cards,
                game.player2_board
            )
        return np.array([])
    
    def _get_reward(self, game: Game) -> float:
        """Вычисляет награду для текущего состояния"""
        # Базовая награда за выигрыш/проигрыш
        if game.is_game_over():
            result = game.get_result()
            return 1.0 if result.winner == 1 else -1.0
            
        # Промежуточные награды
        reward = 0.0
        
        # Награда за роялти
        reward += game.player1_board.get_royalties() * 0.1
        
        # Штраф за фол
        if game.player1_board.is_foul():
            reward -= 0.5
            
        return reward
    
    def _update_history(self, metrics: Dict[str, float]) -> None:
        """Обновляет историю обучения"""
        self.training_history.append({
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics
        })
    
    def _log_progress(self, episode: int, rewards: List[float], wins: List[int]) -> None:
        """Логирует прогресс обучения"""
        recent_rewards = rewards[-100:]
        recent_wins = wins[-100:]
        
        logger.info(
            f"Episode {episode} - "
            f"Avg Reward: {np.mean(recent_rewards):.2f}, "
            f"Win Rate: {np.mean(recent_wins):.2f}, "
            f"Epsilon: {getattr(self.agent, 'epsilon', 0):.3f}"
        )
    
    def _get_training_summary(self, rewards: List[float], wins: List[int]) -> Dict[str, Any]:
        """Создает итоговый отчет об обучении"""
        return {
            'total_episodes': len(rewards),
            'final_win_rate': np.mean(wins[-1000:]),
            'final_avg_reward': np.mean(rewards[-1000:]),
            'max_reward': max(rewards),
            'min_reward': min(rewards),
            'training_history': self.training_history
        }
    
    def save_checkpoint(self, episode: int) -> None:
        """Сохраняет чекпоинт обучения"""
        checkpoint_dir = self.config.get('paths.checkpoints', 'checkpoints')
        checkpoint_path = os.path.join(
            checkpoint_dir,
            f"checkpoint_ep{episode}"
        )
        
        # Сохраняем модель
        if hasattr(self.agent, 'save'):
            self.agent.save(f"{checkpoint_path}_model")
            
        # Сохраняем состояние обучения
        checkpoint_data = {
            'episode': episode,
            'training_history': self.training_history,
            'agent_stats': self.agent.get_stats()
        }
        
        with open(f"{checkpoint_path}_state.json", 'w') as f:
            json.dump(checkpoint_data, f, indent=4)
            
    def load_checkpoint(self, checkpoint_path: str) -> None:
        """Загружает чекпоинт обучения"""
        # Загружаем модель
        if hasattr(self.agent, 'load'):
            self.agent.load(f"{checkpoint_path}_model")
            
        # Загружаем состояние обучения
        with open(f"{checkpoint_path}_state.json", 'r') as f:
            checkpoint_data = json.load(f)
            
        self.training_history = checkpoint_data['training_history']
        
    def save_model(self) -> None:
        """Сохраняет финальную модель"""
        model_dir = self.config.get('paths.models', 'models')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_path = os.path.join(model_dir, f"model_{timestamp}")
        
        if hasattr(self.agent, 'save'):
            self.agent.save(model_path)
            
        # Сохраняем конфигурацию и результаты
        metadata = {
            'timestamp': timestamp,
            'agent_type': self.agent.__class__.__name__,
            'config': self.config.config,
            'final_stats': self.agent.get_stats()
        }
        
        with open(f"{model_path}_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=4)
