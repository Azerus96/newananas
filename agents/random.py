import random
import json
import os
from typing import Tuple, List, Optional, Dict, Any
from pathlib import Path

from agents.base import BaseAgent
from core.card import Card
from core.board import Street, Board

class RandomAgent(BaseAgent):
    """Агент, делающий случайные ходы"""
    
    def __init__(self, name: str = "RandomAgent", seed: Optional[int] = None):
        super().__init__(name)
        if seed is not None:
            random.seed(seed)
        self.save_path = f"agents/saved_states/{self.name}_latest.json"
            
    @classmethod
    def load_latest(cls, name: str = "RandomAgent", **kwargs):
        """Загружает последнее состояние случайного агента"""
        agent = super().load_latest(name=name)
        
        save_path = f"agents/saved_states/{name}_latest.json"
        try:
            if os.path.exists(save_path):
                with open(save_path, 'r') as f:
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
                agent.logger.info(f"Loaded state for {name}")
        except Exception as e:
            agent.logger.error(f"Error loading state: {e}")
            agent.reset_stats()
            
        return agent

    def choose_move(self,
                   board: Board,
                   cards: List[Card],
                   legal_moves: List[Tuple[Card, Street]],
                   opponent_board: Optional[Board] = None) -> Tuple[Card, Street]:
        """
        Выбирает случайный ход из доступных
        
        Args:
            board: Текущая доска агента
            cards: Карты в руке агента
            legal_moves: Список доступных ходов
            opponent_board: Доска противника (если видима)
            
        Returns:
            Tuple[Card, Street]: Выбранные карта и улица для хода
        """
        move = random.choice(legal_moves)
        self.logger.debug(f"Choosing random move: {move}")
        return move

    def save_latest(self) -> None:
        """Сохраняет текущее состояние агента"""
        try:
            os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
            state = {
                'seed': random.getstate(),
                'moves': self.moves,
                'opponent_moves': self.opponent_moves,
                'games_played': self.games_played,
                'games_won': self.games_won,
                'total_score': self.total_score,
                'game_history': self.game_history
            }
            with open(self.save_path, 'w') as f:
                json.dump(state, f, indent=4, default=str)
            self.logger.info(f"Saved state for {self.name}")
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
            'random_seed': random.getstate()[1][0],  # Получаем текущее состояние генератора
            'save_path': self.save_path,
            'has_saved_state': os.path.exists(self.save_path)
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
        return f"RandomAgent(name={self.name}, games_played={self.games_played}, win_rate={self.get_stats()['win_rate']:.2%})"

    def __repr__(self) -> str:
        """
        Подробное строковое представление агента
        
        Returns:
            str: Подробное описание агента
        """
        return f"RandomAgent(name='{self.name}', games_played={self.games_played}, " \
               f"games_won={self.games_won}, total_score={self.total_score})"
