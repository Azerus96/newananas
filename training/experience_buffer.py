# training/experience_buffer.py

from collections import deque, namedtuple
import numpy as np
from typing import List, Tuple, Dict
import random

Experience = namedtuple('Experience', 
    ['state', 'action', 'reward', 'next_state', 'done', 'fantasy_state', 'game_context'])

class PrioritizedExperienceBuffer:
    def __init__(self, capacity: int, alpha: float = 0.6, beta: float = 0.4):
        self.capacity = capacity
        self.alpha = alpha  # Приоритет сэмплирования
        self.beta = beta    # Важность коррекции
        self.beta_increment = 0.001
        
        self.buffer = deque(maxlen=capacity)
        self.priorities = deque(maxlen=capacity)
        self.position = 0
        
        # Специальные буферы для важных событий
        self.fantasy_buffer = deque(maxlen=capacity // 4)
        self.winning_combinations_buffer = deque(maxlen=capacity // 4)

    def add(self, experience: Experience, priority: float = None):
        """Добавляет новый опыт в буфер"""
        if priority is None:
            priority = max(self.priorities) if self.priorities else 1.0

        if len(self.buffer) == self.capacity:
            self.buffer.popleft()
            self.priorities.popleft()
            
        self.buffer.append(experience)
        self.priorities.append(priority)

        # Сохраняем особые события отдельно
        if experience.fantasy_state:
            self.fantasy_buffer.append(experience)
        if self._is_winning_combination(experience):
            self.winning_combinations_buffer.append(experience)

    def sample(self, batch_size: int, priority_scale: float = 0.0) -> Tuple[List[Experience], List[int], List[float]]:
        """Выбирает batch_size опытов с учётом их приоритета"""
        # Масштабируем приоритеты и конвертируем в вероятности
        scaled_priorities = np.array(self.priorities) ** self.alpha
        sample_probabilities = scaled_priorities / sum(scaled_priorities)

        # Выбираем индексы с учётом приоритетов
        indices = random.choices(range(len(self.buffer)), 
                               weights=sample_probabilities, 
                               k=batch_size)

        # Добавляем опыт из специальных буферов
        if self.fantasy_buffer:
            indices[-2] = self.buffer.index(self.fantasy_buffer[-1])
        if self.winning_combinations_buffer:
            indices[-1] = self.buffer.index(self.winning_combinations_buffer[-1])

        experiences = [self.buffer[idx] for idx in indices]
        
        # Вычисляем веса для коррекции смещения
        weights = (len(self.buffer) * sample_probabilities[indices]) ** (-self.beta)
        weights /= max(weights)  # нормализация
        
        self.beta = min(1.0, self.beta + self.beta_increment)
        
        return experiences, indices, weights

    def update_priorities(self, indices: List[int], priorities: List[float]):
        """Обновляет приоритеты для указанных опытов"""
        for idx, priority in zip(indices, priorities):
            self.priorities[idx] = priority + 1e-5  # небольшой бонус для избежания нулевых приоритетов

    def _is_winning_combination(self, experience: Experience) -> bool:
        """Проверяет, является ли опыт выигрышной комбинацией"""
        return (experience.reward > 0 and 
                experience.game_context.get('combination_formed', False))

    def get_statistics(self) -> Dict:
        """Возвращает статистику буфера"""
        return {
            'total_experiences': len(self.buffer),
            'fantasy_experiences': len(self.fantasy_buffer),
            'winning_combinations': len(self.winning_combinations_buffer),
            'average_priority': np.mean(self.priorities) if self.priorities else 0,
            'max_priority': max(self.priorities) if self.priorities else 0,
            'min_priority': min(self.priorities) if self.priorities else 0
        }
