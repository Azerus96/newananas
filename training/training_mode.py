# training/training_mode.py

from dataclasses import dataclass
from typing import List, Optional, Dict
from core.card import Card
from core.board import Board, Street

@dataclass
class TrainingConfig:
    fantasy_mode: bool = False
    time_limit: int = 30  # секунды на ход
    show_removed_cards: bool = True
    progressive_fantasy: bool = False

class TrainingMode:
    def __init__(self, config: TrainingConfig):
        self.config = config
        self.board = Board()
        self.removed_cards: List[Card] = []
        self.input_cards: List[Optional[Card]] = [None] * 16
        self.ai_thinking_time = 0
    
    def set_input_card(self, position: int, card: Card):
        """Устанавливает карту в позицию ввода"""
        if 0 <= position < 16:
            self.input_cards[position] = card
    
    def remove_card(self, card: Card):
        """Удаляет карту из колоды"""
        if card not in self.removed_cards:
            self.removed_cards.append(card)
    
    def get_ai_move(self) -> Dict:
        """Получает ход ИИ с учетом ограничения времени"""
        start_time = time.time()
        
        # Создаем состояние для ИИ
        state = {
            'board': self.board,
            'cards': [card for card in self.input_cards if card],
            'removed_cards': self.removed_cards,
            'fantasy_mode': self.config.fantasy_mode,
            'progressive_fantasy': self.config.progressive_fantasy
        }
        
        # Получаем ход от ИИ
        # training/training_mode.py (продолжение)

        # Получаем ход от ИИ
        move = self._get_ai_decision(state)
        
        self.ai_thinking_time = time.time() - start_time
        
        return {
            'move': move,
            'thinking_time': self.ai_thinking_time,
            'confidence': move.get('confidence', 0)
        }
    
    def _get_ai_decision(self, state: Dict) -> Dict:
        """Получает решение от ИИ с учетом временного ограничения"""
        try:
            with timeout(self.config.time_limit):
                # Получаем все возможные ходы
                legal_moves = self._get_legal_moves(state['board'], state['cards'])
                
                # Оцениваем каждый ход
                move_evaluations = []
                for card, street in legal_moves:
                    evaluation = self._evaluate_move(state, card, street)
                    move_evaluations.append({
                        'card': card,
                        'street': street,
                        'score': evaluation['score'],
                        'confidence': evaluation['confidence'],
                        'reasoning': evaluation['reasoning']
                    })
                
                # Выбираем лучший ход
                best_move = max(move_evaluations, key=lambda x: x['score'])
                return best_move
                
        except TimeoutError:
            # Если время истекло, выбираем ход на основе быстрой эвристики
            return self._get_emergency_move(state)
    
    def _evaluate_move(self, state: Dict, card: Card, street: Street) -> Dict:
        """Оценивает конкретный ход"""
        # Создаем копию доски для симуляции
        test_board = state['board'].copy()
        test_board.place_card(card, street)
        
        # Базовая оценка
        base_score = 0
        confidence = 0.5
        reasoning = []
        
        # Проверяем валидность расстановки
        if test_board.is_valid():
            base_score += 1
            confidence += 0.1
            reasoning.append("Валидная расстановка")
        
        # Если в режиме фантазии
        if state['fantasy_mode']:
            fantasy_score = self._evaluate_fantasy_potential(test_board)
            base_score += fantasy_score * 2
            confidence += 0.2
            reasoning.append(f"Потенциал фантазии: {fantasy_score}")
        
        # Учитываем вышедшие карты
        remaining_potential = self._evaluate_remaining_potential(
            test_board, state['removed_cards']
        )
        base_score += remaining_potential
        confidence += 0.15
        reasoning.append(f"Потенциал оставшихся карт: {remaining_potential}")
        
        return {
            'score': base_score,
            'confidence': min(confidence, 1.0),
            'reasoning': reasoning
        }
    
    def _evaluate_fantasy_potential(self, board: Board) -> float:
        """Оценивает потенциал для фантазии"""
        royalties = board.get_royalties()
        if royalties >= 6:
            return 1.0
        elif royalties >= 4:
            return 0.7
        elif royalties >= 2:
            return 0.4
        return 0.1
    
    def _evaluate_remaining_potential(self, board: Board, 
                                   removed_cards: List[Card]) -> float:
        """Оценивает потенциал с учетом оставшихся карт"""
        available_cards = set(Card.get_all_cards()) - set(removed_cards)
        potential_improvements = 0
        
        for street in Street:
            street_cards = board._get_street(street).cards
            potential = self._calculate_street_potential(
                street_cards, available_cards
            )
            potential_improvements += potential
        
        return potential_improvements / len(Street)
    
    def _calculate_street_potential(self, current_cards: List[Card], 
                                  available_cards: Set[Card]) -> float:
        """Рассчитывает потенциал улучшения улицы"""
        if not current_cards:
            return 1.0
            
        current_rank = HandEvaluator.evaluate(current_cards)
        max_potential_rank = 0
        
        # Проверяем возможные улучшения с доступными картами
        for test_cards in combinations(available_cards, 
                                    min(3, len(available_cards))):
            test_hand = current_cards + list(test_cards)
            rank = HandEvaluator.evaluate(test_hand)
            max_potential_rank = max(max_potential_rank, rank)
        
        improvement_potential = (max_potential_rank - current_rank) / 8000
        return min(1.0, improvement_potential)
    
    def _get_emergency_move(self, state: Dict) -> Dict:
        """Быстрый выбор хода при нехватке времени"""
        legal_moves = self._get_legal_moves(state['board'], state['cards'])
        if not legal_moves:
            return None
            
        # Используем простую эвристику
        for card, street in legal_moves:
            test_board = state['board'].copy()
            test_board.place_card(card, street)
            if test_board.is_valid():
                return {
                    'card': card,
                    'street': street,
                    'score': 0.5,
                    'confidence': 0.3,
                    'reasoning': ["Экстренный выбор из-за нехватки времени"]
                }
        
        # Если не нашли валидный ход, берем первый доступный
        card, street = legal_moves[0]
        return {
            'card': card,
            'street': street,
            'score': 0.1,
            'confidence': 0.1,
            'reasoning': ["Вынужденный ход"]
        }
    
    def _get_legal_moves(self, board: Board, cards: List[Card]) -> List[Tuple[Card, Street]]:
        """Получает список доступных ходов"""
        legal_moves = []
        for card in cards:
            for street in Street:
                if not board._get_street(street).is_full():
                    legal_moves.append((card, street))
        return legal_moves

class TrainingSession:
    """Управляет сессией тренировки"""
    
    def __init__(self, config: TrainingConfig):
        self.config = config
        self.training_mode = TrainingMode(config)
        self.history = []
        self.statistics = TrainingStatistics()
    
    def start_new_game(self):
        """Начинает новую игру"""
        self.training_mode.board.clear()
        self.training_mode.removed_cards.clear()
        self.training_mode.input_cards = [None] * 16
        self.statistics.new_game()
    
    def make_move(self) -> Dict:
        """Делает ход и обновляет статистику"""
        move_result = self.training_mode.get_ai_move()
        self.history.append(move_result)
        self.statistics.record_move(move_result)
        return move_result
    
    # training/training_mode.py (продолжение)

    def get_statistics(self) -> Dict:
        """Возвращает статистику тренировки"""
        return self.statistics.get_summary()
    
    def export_session(self, filepath: str):
        """Экспортирует данные сессии"""
        session_data = {
            'config': asdict(self.config),
            'history': self.history,
            'statistics': self.statistics.get_summary(),
            'timestamp': datetime.now().isoformat()
        }
        with open(filepath, 'w') as f:
            json.dump(session_data, f, indent=4)
    
    def import_session(self, filepath: str):
        """Импортирует данные сессии"""
        with open(filepath, 'r') as f:
            session_data = json.load(f)
        
        self.config = TrainingConfig(**session_data['config'])
        self.history = session_data['history']
        self.statistics.load_from_dict(session_data['statistics'])

class TrainingStatistics:
    """Сбор и анализ статистики тренировки"""
    
    def __init__(self):
        self.games_played = 0
        self.moves_history = []
        self.thinking_times = []
        self.fantasy_stats = defaultdict(int)
        self.combination_stats = defaultdict(lambda: defaultdict(int))
        self.current_game_stats = {}
    
    def new_game(self):
        """Начинает отслеживание новой игры"""
        self.games_played += 1
        self.current_game_stats = {
            'moves': [],
            'thinking_times': [],
            'combinations': defaultdict(list),
            'fantasy_achieved': False
        }
    
    def record_move(self, move_result: Dict):
        """Записывает информацию о ходе"""
        self.moves_history.append(move_result)
        self.thinking_times.append(move_result['thinking_time'])
        
        self.current_game_stats['moves'].append(move_result)
        self.current_game_stats['thinking_times'].append(move_result['thinking_time'])
        
        if 'combination_formed' in move_result:
            street = move_result['street']
            combo_type = move_result['combination_formed']
            self.combination_stats[street][combo_type] += 1
            self.current_game_stats['combinations'][street].append(combo_type)
        
        if move_result.get('fantasy_achieved'):
            self.fantasy_stats['total'] += 1
            self.current_game_stats['fantasy_achieved'] = True
    
    def get_summary(self) -> Dict:
        """Возвращает сводную статистику"""
        return {
            'games_played': self.games_played,
            'total_moves': len(self.moves_history),
            'average_thinking_time': np.mean(self.thinking_times),
            'fantasy_stats': dict(self.fantasy_stats),
            'combination_stats': dict(self.combination_stats),
            'performance_metrics': self._calculate_performance_metrics(),
            'learning_progress': self._analyze_learning_progress()
        }
    
    def _calculate_performance_metrics(self) -> Dict:
        """Рассчитывает метрики производительности"""
        return {
            'success_rate': self._calculate_success_rate(),
            'average_confidence': np.mean([move['confidence'] for move in self.moves_history]),
            'thinking_time_trend': self._calculate_thinking_time_trend(),
            'combination_efficiency': self._calculate_combination_efficiency()
        }
    
    def _calculate_success_rate(self) -> float:
        """Рассчитывает общий процент успешных ходов"""
        successful_moves = sum(1 for move in self.moves_history 
                             if move.get('score', 0) > 0.5)
        return successful_moves / len(self.moves_history) if self.moves_history else 0
    
    def _calculate_thinking_time_trend(self) -> List[float]:
        """Анализирует тренд времени принятия решений"""
        window_size = min(50, len(self.thinking_times))
        if window_size < 2:
            return []
            
        return pd.Series(self.thinking_times).rolling(window_size).mean().tolist()
    
    def _calculate_combination_efficiency(self) -> Dict:
        """Рассчитывает эффективность составления комбинаций"""
        efficiency = {}
        for street, combinations in self.combination_stats.items():
            total = sum(combinations.values())
            if total > 0:
                efficiency[street] = {
                    combo: count/total
                    for combo, count in combinations.items()
                }
        return efficiency
    
    def _analyze_learning_progress(self) -> Dict:
        """Анализирует прогресс обучения"""
        if len(self.moves_history) < 2:
            return {}
            
        # Разбиваем историю на периоды
        periods = min(10, len(self.moves_history) // 100)
        moves_per_period = len(self.moves_history) // periods
        
        progress = []
        for i in range(periods):
            start_idx = i * moves_per_period
            end_idx = start_idx + moves_per_period
            period_moves = self.moves_history[start_idx:end_idx]
            
            progress.append({
                'period': i + 1,
                'average_score': np.mean([move.get('score', 0) for move in period_moves]),
                'average_confidence': np.mean([move.get('confidence', 0) for move in period_moves]),
                'fantasy_rate': sum(1 for move in period_moves if move.get('fantasy_achieved')) / len(period_moves)
            })
        
        return {
            'learning_periods': progress,
            'overall_trend': self._calculate_learning_trend(progress)
        }
    
    def _calculate_learning_trend(self, progress: List[Dict]) -> str:
        """Определяет тренд обучения"""
        if not progress:
            return "Недостаточно данных"
            
        scores = [p['average_score'] for p in progress]
        confidence = [p['average_confidence'] for p in progress]
        
        score_trend = (scores[-1] - scores[0]) / len(scores)
        confidence_trend = (confidence[-1] - confidence[0]) / len(confidence)
        
        if score_trend > 0.1 and confidence_trend > 0.1:
            return "Значительный прогресс"
        elif score_trend > 0 and confidence_trend > 0:
            return "Умеренный прогресс"
        elif score_trend < 0 or confidence_trend < 0:
            return "Требуется корректировка"
        else:
            return "Стабильная производительность"
    
    def load_from_dict(self, data: Dict):
        """Загружает статистику из словаря"""
        self.games_played = data['games_played']
        self.moves_history = data.get('moves_history', [])
        self.thinking_times = data.get('thinking_times', [])
        self.fantasy_stats = defaultdict(int, data.get('fantasy_stats', {}))
        self.combination_stats = defaultdict(
            lambda: defaultdict(int), 
            data.get('combination_stats', {})
        )
