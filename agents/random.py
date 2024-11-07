import random
import json
import os
from typing import Tuple, List, Optional, Dict, Any
from pathlib import Path

from agents.base import BaseAgent
from core.card import Card
from core.board import Street, Board
from utils.logger import get_logger

class RandomAgent(BaseAgent):
    """Агент, делающий случайные ходы"""
    
    SAVE_DIR = Path("agents/saved_states")  # Базовая директория для сохранений
    
    def __init__(self, name: str = "RandomAgent", seed: Optional[int] = None, think_time: int = 30):
        super().__init__(name, think_time=think_time)
        # Создаем директорию для сохранений, если её нет
        self.SAVE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Устанавливаем путь сохранения
        self.save_path = self.SAVE_DIR / f"{self.name}_latest.json"
        
        if seed is not None:
            random.seed(seed)
            self.logger.debug(f"Initialized with seed: {seed}")
            
        self.logger.info(f"Initialized RandomAgent with save path: {self.save_path}")
            
    @classmethod
    def load_latest(cls, name: str = "RandomAgent", think_time: int = 30, **kwargs):
        """Загружает последнее состояние случайного агента"""
        logger = get_logger(f"RandomAgent_loader")
        logger.info(f"Loading latest state for {name}")
        
        agent = cls(name=name, think_time=think_time)
        
        try:
            if agent.save_path.exists():
                with agent.save_path.open('r') as f:
                    data = json.load(f)
                    if 'seed' in data:
                        random.seed(data['seed'])
                    if 'moves' in data:
                        agent.moves = data['moves']
                    if 'opponent_moves' in data:
                        agent.opponent_moves = data['opponent_moves']
                    if 'games_played' in data:
                        agent.games_played = data['games_played']
                    if 'games_won' in data:
                        agent.games_won = data['games_won']
                    if 'total_score' in data:
                        agent.total_score = data['total_score']
                    if 'think_time' in data:
                        agent.think_time = data['think_time']
                agent.logger.info(f"Loaded state from {agent.save_path}")
        except Exception as e:
            agent.logger.error(f"Error loading state: {e}")
            agent.reset_stats()
            
        return agent

    def choose_move(self,
                   board: Board,
                   cards: List[Card],
                   legal_moves: List[Tuple[Card, Street]],
                   opponent_board: Optional[Board] = None,
                   think_time: Optional[int] = None) -> Tuple[Card, Street]:
        """
        Выбирает случайный ход из доступных
        
        Args:
            board: Текущая доска агента
            cards: Карты в руке агента
            legal_moves: Список доступных ходов
            opponent_board: Доска противника (если видима)
            think_time: Время на размышление (если отличается от default)
            
        Returns:
            Tuple[Card, Street]: Выбранные карта и улица для хода
        """
        current_think_time = think_time or self.think_time
        move = random.choice(legal_moves)
        self.logger.debug(f"Choosing random move: {move} (think_time: {current_think_time}s)")
        return move

    def save_latest(self) -> None:
        """Сохраняет текущее состояние агента"""
        try:
            # Убеждаемся, что директория существует
            self.save_path.parent.mkdir(parents=True, exist_ok=True)
            
            state = {
                'seed': random.getstate(),
                'moves': self.moves,
                'opponent_moves': self.opponent_moves,
                'games_played': self.games_played,
                'games_won': self.games_won,
                'total_score': self.total_score,
                'game_history': self.game_history,
                'think_time': self.think_time,
                'name': self.name,
                'save_path': str(self.save_path)
            }
            
            with self.save_path.open('w') as f:
                json.dump(state, f, indent=4, default=str)
            self.logger.info(f"Saved state to {self.save_path}")
        except Exception as e:
            self.logger.error(f"Error saving state: {e}")

    def notify_game_end(self, result: Dict[str, Any]) -> None:
        """
        Переопределяем метод завершения игры для сохранения состояния
        
        Args:
            result: Результаты игры
        """
        super().notify_game_end(result)
        self.save_latest()

    def get_stats(self) -> Dict[str, Any]:
        """
        Расширяем статистику для случайного агента
        
        Returns:
            Dict: Расширенная статистика
        """
        base_stats = super().get_stats()
        random_stats = {
            'random_seed': random.getstate()[1][0],
            'save_path': str(self.save_path),
            'has_saved_state': self.save_path.exists(),
            'think_time': self.think_time
        }
        return {**base_stats, **random_stats}

    def reset_stats(self) -> None:
        """
        Расширяем сброс статистики
        """
        super().reset_stats()
        self.save_latest()  # Сохраняем пустое состояние

    def __str__(self) -> str:
        """
        Строковое представление агента
        
        Returns:
            str: Описание агента
        """
        win_rate = self.games_won / self.games_played if self.games_played > 0 else 0
        return f"RandomAgent(name={self.name}, games_played={self.games_played}, win_rate={win_rate:.2%})"

    def __repr__(self) -> str:
        """
        Подробное строковое представление агента
        
        Returns:
            str: Подробное описание агента
        """
        return (f"RandomAgent(name='{self.name}', games_played={self.games_played}, "
                f"games_won={self.games_won}, total_score={self.total_score}, "
                f"think_time={self.think_time}, save_path='{self.save_path}')")
