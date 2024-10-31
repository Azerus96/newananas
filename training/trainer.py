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
                    game.make_move(
