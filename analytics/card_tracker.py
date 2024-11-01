# analytics/card_tracker.py

from typing import Dict, List, Set, Tuple
from collections import defaultdict
import numpy as np
from datetime import datetime

from ..core.card import Card
from ..core.board import Street, Board

class CardStatistics:
    """Класс для хранения статистики по картам"""
    def __init__(self):
        self.appearances = 0  # Сколько раз карта появлялась
        self.wins = 0        # Сколько раз приводила к победе
        self.fantasy_entries = 0  # Сколько раз приводила к фантазии
        self.street_placements = defaultdict(int)  # На какие улицы ставилась
        self.combinations = defaultdict(int)  # В каких комбинациях участвовала
        self.win_rate_by_street = defaultdict(float)  # Процент побед по улицам

class CardTracker:
    """Система анализа и отслеживания карт на основе истории игр"""
    
    def __init__(self):
        self.card_stats: Dict[Card, CardStatistics] = defaultdict(CardStatistics)
        self.combination_stats = defaultdict(lambda: defaultdict(int))
        self.current_game_cards: Set[Card] = set()
        self.removed_cards: Set[Card] = set()
        self.history: List[Dict] = []
        
    def track_game(self, game_result: Dict):
        """Анализирует результаты игры"""
        game_data = {
            'timestamp': datetime.now(),
            'cards_used': set(),
            'combinations': defaultdict(list),
            'winner': game_result['winner'],
            'fantasy_achieved': game_result.get('fantasy_achieved', False)
        }
        
        # Анализируем карты на доске победителя
        winning_board = game_result['player1_board'] if game_result['winner'] == 1 else game_result['player2_board']
        self._analyze_board(winning_board, True, game_data)
        
        # Анализируем карты на доске проигравшего
        losing_board = game_result['player2_board'] if game_result['winner'] == 1 else game_result['player1_board']
        self._analyze_board(losing_board, False, game_data)
        
        self.history.append(game_data)
        self._update_statistics(game_data)
        
    def _analyze_board(self, board: Board, is_winner: bool, game_data: Dict):
        """Анализирует расположение карт на доске"""
        for street in Street:
            street_cards = board._get_street(street).cards
            game_data['cards_used'].update(street_cards)
            
            if street_cards:
                combo_type = self._get_combination_type(street_cards)
                game_data['combinations'][street].append({
                    'cards': street_cards,
                    'type': combo_type,
                    'is_winner': is_winner
                })
                
                # Обновляем статистику для каждой карты
                for card in street_cards:
                    stats = self.card_stats[card]
                    stats.appearances += 1
                    stats.street_placements[street] += 1
                    stats.combinations[combo_type] += 1
                    if is_winner:
                        stats.wins += 1
                        stats.win_rate_by_street[street] = (
                            stats.wins / stats.appearances
                        )
    
    def get_card_recommendation(self, 
                              available_cards: List[Card], 
                              current_board: Board,
                              target_street: Street,
                              fantasy_mode: bool = False) -> List[Tuple[Card, float]]:
        """Возвращает рекомендации по картам на основе статистики"""
        recommendations = []
        
        for card in available_cards:
            if card in self.removed_cards:
                continue
                
            score = self._calculate_card_score(
                card, 
                current_board, 
                target_street,
                fantasy_mode
            )
            recommendations.append((card, score))
        
        return sorted(recommendations, key=lambda x: x[1], reverse=True)
    
    def _calculate_card_score(self, 
                            card: Card, 
                            board: Board, 
                            target_street: Street,
                            fantasy_mode: bool) -> float:
        """Рассчитывает оценку карты на основе статистики"""
        stats = self.card_stats[card]
        
        if stats.appearances == 0:
            return 0.0
            
        # Базовая оценка на основе процента побед
        base_score = stats.wins / stats.appearances
        
        # Бонус за успешность на конкретной улице
        street_bonus = stats.win_rate_by_street[target_street]
        
        # Бонус за комбинации
        combo_bonus = self._calculate_combination_bonus(
            card, 
            board._get_street(target_street).cards
        )
        
        # Если в режиме фантазии, учитываем статистику фантазий
        fantasy_bonus = 0.0
        if fantasy_mode and stats.fantasy_entries > 0:
            fantasy_bonus = stats.fantasy_entries / stats.appearances
        
        # Взвешенная сумма всех факторов
        return (
            0.3 * base_score +
            0.3 * street_bonus +
            0.3 * combo_bonus +
            0.1 * fantasy_bonus
        )
    
    def _calculate_combination_bonus(self, card: Card, existing_cards: List[Card]) -> float:
        """Рассчитывает бонус за потенциальные комбинации"""
        if not existing_cards:
            return 0.0
            
        potential_combos = self._get_potential_combinations(
            existing_cards + [card]
        )
        
        combo_scores = []
        for combo_type in potential_combos:
            success_count = self.combination_stats[combo_type]['wins']
            total_count = self.combination_stats[combo_type]['total']
            if total_count > 0:
                combo_scores.append(success_count / total_count)
        
        return max(combo_scores) if combo_scores else 0.0
    
    def mark_card_removed(self, card: Card):
        """Отмечает карту как удаленную из игры"""
        self.removed_cards.add(card)
    
    def reset_removed_cards(self):
        """Сбрасывает список удаленных карт"""
        self.removed_cards.clear()
    
    def get_card_statistics(self, card: Card) -> Dict:
        """Возвращает полную статистику по карте"""
        stats = self.card_stats[card]
        return {
            'appearances': stats.appearances,
            'win_rate': stats.wins / stats.appearances if stats.appearances > 0 else 0,
            'fantasy_rate': stats.fantasy_entries / stats.appearances if stats.appearances > 0 else 0,
            'preferred_streets': sorted(
                stats.street_placements.items(),
                key=lambda x: x[1],
                reverse=True
            ),
            'best_combinations': sorted(
                stats.combinations.items(),
                key=lambda x: x[1],
                reverse=True
            )
        }
    
    def # analytics/card_tracker.py (продолжение)

    def get_overall_statistics(self) -> Dict:
        """Возвращает общую статистику по всем картам"""
        return {
            'total_games': len(self.history),
            'most_successful_cards': self._get_most_successful_cards(),
            'best_combinations': self._get_best_combinations(),
            'street_statistics': self._get_street_statistics(),
            'fantasy_statistics': self._get_fantasy_statistics()
        }
    
    def _get_most_successful_cards(self, limit: int = 10) -> List[Dict]:
        """Возвращает список самых успешных карт"""
        card_success = []
        for card, stats in self.card_stats.items():
            if stats.appearances >= 10:  # Минимальный порог для статистической значимости
                success_rate = stats.wins / stats.appearances
                card_success.append({
                    'card': card,
                    'success_rate': success_rate,
                    'appearances': stats.appearances,
                    'fantasy_entries': stats.fantasy_entries
                })
        
        return sorted(card_success, key=lambda x: x['success_rate'], reverse=True)[:limit]
    
    def _get_best_combinations(self) -> Dict:
        """Анализирует самые успешные комбинации"""
        combo_stats = {}
        for combo_type, stats in self.combination_stats.items():
            if stats['total'] >= 5:  # Минимальный порог
                success_rate = stats['wins'] / stats['total']
                combo_stats[combo_type] = {
                    'success_rate': success_rate,
                    'total_appearances': stats['total'],
                    'fantasy_entries': stats['fantasy_entries']
                }
        
        return combo_stats
    
    def _get_street_statistics(self) -> Dict:
        """Анализирует статистику по улицам"""
        street_stats = defaultdict(lambda: {
            'total_cards': 0,
            'winning_cards': 0,
            'fantasy_entries': 0,
            'best_cards': []
        })
        
        for card, stats in self.card_stats.items():
            for street, count in stats.street_placements.items():
                street_stats[street]['total_cards'] += count
                street_stats[street]['winning_cards'] += (
                    count * stats.wins / stats.appearances
                    if stats.appearances > 0 else 0
                )
                
                # Добавляем карту в список лучших для улицы
                if count >= 5:  # Минимальный порог появлений
                    success_rate = stats.win_rate_by_street[street]
                    street_stats[street]['best_cards'].append({
                        'card': card,
                        'success_rate': success_rate,
                        'appearances': count
                    })
        
        # Сортируем лучшие карты для каждой улицы
        for street in street_stats:
            street_stats[street]['best_cards'].sort(
                key=lambda x: x['success_rate'],
                reverse=True
            )
            street_stats[street]['best_cards'] = street_stats[street]['best_cards'][:5]
        
        return dict(street_stats)
    
    def _get_fantasy_statistics(self) -> Dict:
        """Анализирует статистику фантазий"""
        return {
            'total_fantasies': sum(1 for game in self.history 
                                 if game['fantasy_achieved']),
            'fantasy_success_rate': self._calculate_fantasy_success_rate(),
            'best_fantasy_cards': self._get_best_fantasy_cards(),
            'best_fantasy_combinations': self._get_best_fantasy_combinations()
        }
    
    def _calculate_fantasy_success_rate(self) -> float:
        """Рассчитывает процент успешных фантазий"""
        fantasy_games = [game for game in self.history 
                        if game['fantasy_achieved']]
        if not fantasy_games:
            return 0.0
            
        successful_fantasies = sum(1 for game in fantasy_games 
                                 if game['winner'] == 1)
        return successful_fantasies / len(fantasy_games)
    
    def _get_best_fantasy_cards(self, limit: int = 5) -> List[Dict]:
        """Определяет карты, наиболее часто приводящие к успешным фантазиям"""
        fantasy_cards = []
        for card, stats in self.card_stats.items():
            if stats.fantasy_entries >= 3:  # Минимальный порог
                fantasy_rate = stats.fantasy_entries / stats.appearances
                fantasy_cards.append({
                    'card': card,
                    'fantasy_rate': fantasy_rate,
                    'total_fantasies': stats.fantasy_entries,
                    'total_appearances': stats.appearances
                })
        
        return sorted(fantasy_cards, key=lambda x: x['fantasy_rate'], 
                     reverse=True)[:limit]
    
    def _get_best_fantasy_combinations(self) -> Dict:
        """Определяет комбинации, наиболее успешные в фантазии"""
        fantasy_combos = {}
        for combo_type, stats in self.combination_stats.items():
            if stats['fantasy_entries'] >= 3:  # Минимальный порог
                fantasy_rate = stats['fantasy_entries'] / stats['total']
                fantasy_combos[combo_type] = {
                    'fantasy_rate': fantasy_rate,
                    'total_fantasies': stats['fantasy_entries'],
                    'total_appearances': stats['total']
                }
        
        return fantasy_combos
    
    def save_statistics(self, filepath: str):
        """Сохраняет статистику в файл"""
        data = {
            'card_stats': {str(card): self._serialize_card_stats(stats)
                          for card, stats in self.card_stats.items()},
            'combination_stats': dict(self.combination_stats),
            'history': self.history
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
    
    def load_statistics(self, filepath: str):
        """Загружает статистику из файла"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.card_stats.clear()
        for card_str, stats_dict in data['card_stats'].items():
            card = Card.from_string(card_str)
            self.card_stats[card] = self._deserialize_card_stats(stats_dict)
        
        self.combination_stats.clear()
        self.combination_stats.update(data['combination_stats'])
        
        self.history = data['history']
    
    def _serialize_card_stats(self, stats: CardStatistics) -> Dict:
        """Сериализует статистику карты"""
        return {
            'appearances': stats.appearances,
            'wins': stats.wins,
            'fantasy_entries': stats.fantasy_entries,
            'street_placements': dict(stats.street_placements),
            'combinations': dict(stats.combinations),
            'win_rate_by_street': dict(stats.win_rate_by_street)
        }
    
    def _deserialize_card_stats(self, data: Dict) -> CardStatistics:
        """Десериализует статистику карты"""
        stats = CardStatistics()
        stats.appearances = data['appearances']
        stats.wins = data['wins']
        stats.fantasy_entries = data['fantasy_entries']
        stats.street_placements.update(data['street_placements'])
        stats.combinations.update(data['combinations'])
        # analytics/card_tracker.py (продолжение)

        stats.win_rate_by_street.update(data['win_rate_by_street'])
        return stats

    def _get_combination_type(self, cards: List[Card]) -> str:
        """Определяет тип комбинации из карт"""
        from ..core.evaluator import HandEvaluator  # Импорт здесь во избежание циклических зависимостей
        return HandEvaluator.get_combination_type(cards)

    def _get_potential_combinations(self, cards: List[Card]) -> List[str]:
        """Определяет возможные комбинации из данных карт"""
        from ..core.evaluator import HandEvaluator
        return HandEvaluator.get_potential_combinations(cards)

    def merge_statistics(self, other_tracker: 'CardTracker'):
        """Объединяет статистику с другим трекером"""
        for card, other_stats in other_tracker.card_stats.items():
            stats = self.card_stats[card]
            stats.appearances += other_stats.appearances
            stats.wins += other_stats.wins
            stats.fantasy_entries += other_stats.fantasy_entries
            
            for street, count in other_stats.street_placements.items():
                stats.street_placements[street] += count
            
            for combo, count in other_stats.combinations.items():
                stats.combinations[combo] += count
            
            # Пересчитываем win_rate_by_street
            for street in stats.street_placements:
                if stats.appearances > 0:
                    stats.win_rate_by_street[street] = (
                        stats.wins / stats.appearances
                    )

        # Объединяем историю
        self.history.extend(other_tracker.history)
        
        # Обновляем статистику комбинаций
        for combo_type, stats in other_tracker.combination_stats.items():
            self.combination_stats[combo_type]['total'] += stats['total']
            self.combination_stats[combo_type]['wins'] += stats['wins']
            self.combination_stats[combo_type]['fantasy_entries'] += stats['fantasy_entries']

    def get_card_suggestions(self, 
                           current_board: Board, 
                           available_cards: List[Card],
                           fantasy_mode: bool = False,
                           top_n: int = 3) -> Dict[Street, List[Tuple[Card, float, str]]]:
        """Возвращает рекомендации по картам для каждой улицы"""
        suggestions = {}
        
        for street in Street:
            if not current_board._get_street(street).is_full():
                street_suggestions = []
                for card in available_cards:
                    if card not in self.removed_cards:
                        score = self._calculate_card_score(
                            card, 
                            current_board, 
                            street,
                            fantasy_mode
                        )
                        reasoning = self._get_suggestion_reasoning(
                            card, 
                            score, 
                            street,
                            fantasy_mode
                        )
                        street_suggestions.append((card, score, reasoning))
                
                suggestions[street] = sorted(
                    street_suggestions,
                    key=lambda x: x[1],
                    reverse=True
                )[:top_n]
        
        return suggestions

    def _get_suggestion_reasoning(self, 
                                card: Card, 
                                score: float, 
                                street: Street,
                                fantasy_mode: bool) -> str:
        """Формирует объяснение для рекомендации карты"""
        stats = self.card_stats[card]
        reasons = []
        
        if stats.appearances > 0:
            win_rate = stats.wins / stats.appearances
            reasons.append(f"Win rate: {win_rate:.1%}")
            
            street_win_rate = stats.win_rate_by_street[street]
            reasons.append(f"Street success: {street_win_rate:.1%}")
            
            if fantasy_mode and stats.fantasy_entries > 0:
                fantasy_rate = stats.fantasy_entries / stats.appearances
                reasons.append(f"Fantasy success: {fantasy_rate:.1%}")
        
        best_combo = max(stats.combinations.items(), 
                        key=lambda x: x[1], 
                        default=(None, 0))
        if best_combo[0]:
            reasons.append(f"Best combo: {best_combo[0]}")
        
        return " | ".join(reasons)

    def analyze_game_patterns(self) -> Dict:
        """Анализирует паттерны в играх"""
        patterns = {
            'winning_sequences': self._analyze_winning_sequences(),
            'fantasy_patterns': self._analyze_fantasy_patterns(),
            'street_patterns': self._analyze_street_patterns()
        }
        return patterns

    def _analyze_winning_sequences(self) -> Dict:
        """Анализирует успешные последовательности карт"""
        sequences = defaultdict(lambda: {'total': 0, 'wins': 0})
        
        for game in self.history:
            if game['winner'] == 1:  # Анализируем только победные игры
                for street, combos in game['combinations'].items():
                    for combo in combos:
                        cards_seq = tuple(sorted(combo['cards']))
                        sequences[cards_seq]['total'] += 1
                        if combo['is_winner']:
                            sequences[cards_seq]['wins'] += 1
        
        return {
            str(seq): stats
            for seq, stats in sequences.items()
            if stats['total'] >= 3  # Минимальный порог для паттерна
        }

    def _analyze_fantasy_patterns(self) -> Dict:
        """Анализирует паттерны в фантазиях"""
        patterns = defaultdict(lambda: {
            'total': 0,
            'success': 0,
            'cards': set()
        })
        
        for game in self.history:
            if game['fantasy_achieved']:
                for street, combos in game['combinations'].items():
                    for combo in combos:
                        pattern_key = (street, combo['type'])
                        patterns[pattern_key]['total'] += 1
                        patterns[pattern_key]['cards'].update(combo['cards'])
                        if combo['is_winner']:
                            patterns[pattern_key]['success'] += 1
        
        return {
            f"{street}_{combo_type}": {
                'success_rate': stats['success'] / stats['total'],
                'total_appearances': stats['total'],
                'common_cards': [str(card) for card in stats['cards']]
            }
            for (street, combo_type), stats in patterns.items()
            if stats['total'] >= 3
        }

    def _analyze_street_patterns(self) -> Dict:
        """Анализирует паттерны размещения карт по улицам"""
        patterns = defaultdict(lambda: {
            'total': 0,
            'success': 0,
            'fantasy_entries': 0
        })
        
        for game in self.history:
            for street, combos in game['combinations'].items():
                for combo in combos:
                    pattern = (street, len(combo['cards']))
                    patterns[pattern]['total'] += 1
                    if combo['is_winner']:
                        patterns[pattern]['success'] += 1
                    if game['fantasy_achieved']:
                        patterns[pattern]['fantasy_entries'] += 1
        
        return {
            f"{street}_{cards_count}": {
                'success_rate': stats['success'] / stats['total'],
                'fantasy_rate': stats['fantasy_entries'] / stats['total'],
                'total_appearances': stats['total']
            }
            for (street, cards_count), stats in patterns.items()
        }
