from abc import ABC, abstractmethod
from typing import Tuple, List, Optional, Dict, Any
import numpy as np
import os
import json
import tensorflow as tf

from core.card import Card
from core.board import Street, Board
from utils.logger import get_logger

logger = get_logger(__name__)

class BaseAgent(ABC):
    """Базовый класс для всех агентов"""
    
    def __init__(self, name: str = "Agent", think_time: int = 30):
        self.name = name
        self.think_time = think_time  # добавляем параметр think_time
        self.logger = get_logger(f"Agent_{name}")
        self.reset_stats()

    @classmethod
    def load_latest(cls, name: str = None, think_time: int = 30, **kwargs):
        """Базовый метод загрузки последнего состояния"""
        logger.debug(f"Base load_latest called for {name}")
        return cls(name=name, think_time=think_time) if name else cls(think_time=think_time)

    def save_model(self, filepath: str) -> None:
        """Сохраняет модель и дополнительные данные"""
        if hasattr(self, 'model'):
            self.model.save_weights(filepath + '_main.h5')
        if hasattr(self, 'target_model'):
            self.target_model.save_weights(filepath + '_target.h5')

        # Сохраняем метаданные агента
        metadata = {
            'name': self.name,
            'think_time': self.think_time,
            'games_played': self.games_played,
            'games_won': self.games_won,
            'total_score': self.total_score,
            'moves': self.moves,
            'opponent_moves': self.opponent_moves,
            'config': getattr(self, 'config', {})  # Сохраняем конфигурацию, если она есть
        }
        
        with open(filepath + '_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=4)
        logger.info(f"Model and metadata saved to {filepath}")

    def load_model(self, filepath: str) -> None:
        """Загружает модель и дополнительные данные"""
        if hasattr(self, 'model') and os.path.exists(filepath + '_main.h5'):
            self.model.load_weights(filepath + '_main.h5')
        else:
            logger.warning(f"No main model weights found at {filepath + '_main.h5'}")

        if hasattr(self, 'target_model') and os.path.exists(filepath + '_target.h5'):
            self.target_model.load_weights(filepath + '_target.h5')
        else:
            logger.warning(f"No target model weights found at {filepath + '_target.h5'}")
        
        # Загружаем метаданные
        try:
            with open(filepath + '_metadata.json', 'r') as f:
                metadata = json.load(f)
                self.name = metadata.get('name', self.name)
                self.think_time = metadata.get('think_time', self.think_time)
                self.games_played = metadata.get('games_played', 0)
                self.games_won = metadata.get('games_won', 0)
                self.total_score = metadata.get('total_score', 0)
                self.moves = metadata.get('moves', [])
                self.opponent_moves = metadata.get('opponent_moves', [])
                if hasattr(self, 'config'):
                    self.config.update(metadata.get('config', {}))
            logger.info(f"Model and metadata loaded from {filepath}")
        except FileNotFoundError:
            logger.warning(f"No metadata file found at {filepath}")

    @abstractmethod
    def choose_move(self, 
                   board: Board,
                   cards: List[Card],
                   legal_moves: List[Tuple[Card, Street]],
                   opponent_board: Optional[Board] = None,
                   think_time: Optional[int] = None) -> Tuple[Card, Street]:
        """
        Выбирает ход из списка доступных
        
        Args:
            board: Текущая доска агента
            cards: Карты в руке агента
            legal_moves: Список доступных ходов
            opponent_board: Доска противника (если видима)
            think_time: Время на размышление (если отличается от default)
            
        Returns:
            Tuple[Card, Street]: Выбранные карта и улица для хода
        """
        pass
        
    def notify_game_start(self, initial_cards: List[Card]) -> None:
        """
        Уведомляет агента о начале новой игры
        
        Args:
            initial_cards: Начальные карты агента
        """
        self.reset_stats()
        self.current_cards = initial_cards.copy()
        self.logger.info(f"Starting new game with cards: {initial_cards}")
        
    def notify_opponent_move(self, card: Card, street: Street, board_state: Dict) -> None:
        """
        Уведомляет агента о ходе противника
        
        Args:
            card: Сыгранная карта
            street: Улица, на которую поставлена карта
            board_state: Состояние доски после хода
        """
        self.opponent_moves.append({
            'card': card,
            'street': street,
            'board_state': board_state
        })
        self.logger.debug(f"Opponent move: {card} to {street}")
        
    def notify_move_result(self, card: Card, street: Street, 
                          success: bool, board_state: Dict) -> None:
        """
        Уведомляет агента о результате его хода
        
        Args:
            card: Сыгранная карта
            street: Улица, на которую поставлена карта
            success: Был ли ход успешным
            board_state: Состояние доски после хода
        """
        self.moves.append({
            'card': card,
            'street': street,
            'success': success,
            'board_state': board_state
        })
        if success:
            self.current_cards.remove(card)
        self.logger.debug(f"Move result: {success} for {card} to {street}")
        
    def notify_game_end(self, result: Dict[str, Any]) -> None:
        """
        Уведомляет агента о завершении игры
        
        Args:
            result: Результаты игры (победитель, счет и т.д.)
        """
        self.games_played += 1
        if result.get('winner') == self.name:
            self.games_won += 1
        self.total_score += result.get('score', 0)
        
        self.logger.info(f"Game ended. Result: {result}")
        self.save_game_stats(result)
        
    def reset_stats(self) -> None:
        """Сбрасывает статистику агента"""
        self.games_played = 0
        self.games_won = 0
        self.total_score = 0
        self.moves = []
        self.opponent_moves = []
        self.current_cards = []
        self.game_history = []
        self.logger.debug("Stats reset")
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику агента
        
        Returns:
            Dict: Статистика игр агента
        """
        stats = {
            'name': self.name,
            'games_played': self.games_played,
            'games_won': self.games_won,
            'win_rate': self.games_won / self.games_played if self.games_played > 0 else 0,
            'average_score': self.total_score / self.games_played if self.games_played > 0 else 0,
            'total_moves': len(self.moves),
            'successful_moves': sum(1 for move in self.moves if move['success']),
            'think_time': self.think_time  # добавляем think_time в статистику
        }
        self.logger.debug(f"Retrieved stats: {stats}")
        return stats
        
    def save_game_stats(self, result: Dict[str, Any]) -> None:
        """
        Сохраняет статистику игры
        
        Args:
            result: Результаты игры
        """
        game_stats = {
            'moves': self.moves.copy(),
            'opponent_moves': self.opponent_moves.copy(),
            'result': result,
            'think_time': self.think_time  # добавляем think_time в статистику игры
        }
        self.game_history.append(game_stats)
        self.logger.debug(f"Saved game stats: {game_stats}")
