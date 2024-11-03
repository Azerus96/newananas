# agents/rl/fantasy_agent.py

from typing import List, Dict, Tuple, Any, Optional
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from agents.base import BaseAgent
from core.card import Card
from core.board import Board, Street
from core.fantasy import FantasyMode
from utils.logger import get_logger

logger = get_logger(__name__)

class FantasyNetwork(nn.Module):
    """Нейронная сеть для игры в фантазии"""
    
    def __init__(self, input_size: int, hidden_size: int = 256):
        super().__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, hidden_size // 2)
        
        # Две головы: одна для оценки вероятности сохранения в фантазии,
        # другая для оценки ценности позиции
        self.fantasy_head = nn.Linear(hidden_size // 2, 1)
        self.value_head = nn.Linear(hidden_size // 2, 1)
        
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        
        fantasy_prob = torch.sigmoid(self.fantasy_head(x))
        value = self.value_head(x)
        
        return fantasy_prob, value

class FantasyAgent(BaseAgent):
    """Агент, специализирующийся на игре в фантазии"""
    
    def __init__(self, state_size: int, name: str = "FantasyAgent"):
        super().__init__(name)
        self.state_size = state_size
        self.network = FantasyNetwork(state_size)
        self.optimizer = torch.optim.Adam(self.network.parameters())
        self.fantasy_history = []
        self.training_mode = True
        
    def choose_move(self, 
                   board: Board,
                   cards: List[Card],
                   legal_moves: List[Tuple[Card, Street]],
                   opponent_board: Optional[Board] = None) -> Tuple[Card, Street]:
        """Выбирает ход с приоритетом на сохранение в фантазии"""
        
        state = self.encode_state(board, cards, opponent_board)
        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        
        with torch.no_grad():
            fantasy_probs = []
            values = []
            
            for card, street in legal_moves:
                # Симулируем каждый возможный ход
                test_board = board.copy()
                test_board.place_card(card, street)
                test_state = self.encode_state(test_board, 
                                            [c for c in cards if c != card],
                                            opponent_board)
                test_tensor = torch.FloatTensor(test_state).unsqueeze(0)
                
                fantasy_prob, value = self.network(test_tensor)
                fantasy_probs.append(fantasy_prob.item())
                values.append(value.item())
        
        # Выбираем ход с учетом обоих факторов
        move_scores = [
            0.7 * fp + 0.3 * v  # Больший вес для вероятности сохранения в фантазии
            for fp, v in zip(fantasy_probs, values)
        ]
        
        best_move_idx = np.argmax(move_scores)
        chosen_move = legal_moves[best_move_idx]
        
        # Сохраняем информацию о ходе для обучения
        if self.training_mode:
            self.fantasy_history.append({
                'state': state,
                'move': chosen_move,
                'fantasy_prob': fantasy_probs[best_move_idx],
                'value': values[best_move_idx]
            })
        
        return chosen_move
    
    def train_on_game(self, game_result: Dict):
        """Обучается на результатах игры"""
        if not self.fantasy_history:
            return
        
        fantasy_success = game_result.get('fantasy_success', False)
        final_reward = 1.0 if fantasy_success else -1.0
        
        # Подготавливаем данные для обучения
        states = torch.FloatTensor([h['state'] for h in self.fantasy_history])
        fantasy_probs = torch.FloatTensor([h['fantasy_prob'] for h in self.fantasy_history])
        values = torch.FloatTensor([h['value'] for h in self.fantasy_history])
        
        # Рассчитываем целевые значения
        fantasy_targets = torch.full_like(fantasy_probs, float(fantasy_success))
        value_targets = self._calculate_value_targets(final_reward)
        
        # Обучаем сеть
        self.optimizer.zero_grad()
        
        predicted_probs, predicted_values = self.network(states)
        
        # Функция потерь: комбинация BCE для вероятности фантазии и MSE для ценности
        fantasy_loss = F.binary_cross_entropy(predicted_probs.squeeze(), fantasy_targets)
        value_loss = F.mse_loss(predicted_values.squeeze(), value_targets)
        
        total_loss = fantasy_loss + 0.5 * value_loss
        
        total_loss.backward()
        self.optimizer.step()
        
        # Очищаем историю
        self.fantasy_history.clear()
        
        return {
            'fantasy_loss': fantasy_loss.item(),
            'value_loss': value_loss.item(),
            'total_loss': total_loss.item()
        }
    
    def _calculate_value_targets(self, final_reward: float) -> torch.Tensor:
        """Рассчитывает целевые значения с учетом временных различий"""
        gamma = 0.99
        targets = []
        running_reward = final_reward
        
        for _ in reversed(self.fantasy_history):
            targets.append(running_reward)
            running_reward *= gamma
        
        return torch.FloatTensor(list(reversed(targets)))
    
    def encode_state(self, board: Board, cards: List[Card], 
                    opponent_board: Optional[Board] = None) -> np.ndarray:
        """Кодирует состояние игры для нейронной сети"""
        # Кодируем карты на доске
        board_state = self._encode_board(board)
        
        # Кодируем карты в руке
        hand_state = self._encode_cards(cards)
        
        # Кодируем доску противника, если доступна
        opponent_state = (self._encode_board(opponent_board) 
                         if opponent_board else np.zeros_like(board_state))
        
        return np.concatenate([board_state, hand_state, opponent_state])
    
     # agents/rl/fantasy_agent.py (продолжение)

    def _encode_board(self, board: Board) -> np.ndarray:
        """Кодирует состояние доски"""
        # Создаем вектор для каждой улицы
        front_state = self._encode_cards(board.front.cards, max_cards=3)
        middle_state = self._encode_cards(board.middle.cards, max_cards=5)
        back_state = self._encode_cards(board.back.cards, max_cards=5)
        
        # Добавляем информацию о комбинациях
        front_combo = self._encode_combination(board.front.get_combination())
        middle_combo = self._encode_combination(board.middle.get_combination())
        back_combo = self._encode_combination(board.back.get_combination())
        
        return np.concatenate([
            front_state, middle_state, back_state,
            front_combo, middle_combo, back_combo
        ])
    
    def _encode_cards(self, cards: List[Card], max_cards: int = 13) -> np.ndarray:
        """Кодирует список карт в бинарный вектор"""
        # 52 бита для каждой возможной карты (1 если карта присутствует)
        encoding = np.zeros(52)
        
        for card in cards:
            # Индекс = (ранг - 2) * 4 + масть
            idx = (card.rank.value - 2) * 4 + card.suit.value
            encoding[idx] = 1
            
        # Добавляем информацию о количестве карт
        count_encoding = np.zeros(max_cards)
        count_encoding[len(cards)-1] = 1 if cards else 0
        
        return np.concatenate([encoding, count_encoding])
    
    def _encode_combination(self, combination: str) -> np.ndarray:
        """Кодирует тип комбинации"""
        # Возможные типы комбинаций
        combo_types = [
            'high_card', 'pair', 'two_pair', 'three_of_kind',
            'straight', 'flush', 'full_house', 'four_of_kind',
            'straight_flush', 'royal_flush'
        ]
        
        encoding = np.zeros(len(combo_types))
        if combination in combo_types:
            encoding[combo_types.index(combination)] = 1
            
        return encoding
    
    def save_model(self, path: str):
        """Сохраняет модель"""
        torch.save({
            'network_state': self.network.state_dict(),
            'optimizer_state': self.optimizer.state_dict()
        }, path)
        
    def load_model(self, path: str):
        """Загружает модель"""
        checkpoint = torch.load(path)
        self.network.load_state_dict(checkpoint['network_state'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state'])
    
    def get_training_stats(self) -> Dict:
        """Возвращает статистику обучения"""
        return {
            'fantasy_success_rate': self.get_fantasy_success_rate(),
            'average_value_prediction': self.get_average_value_prediction(),
            'model_parameters': self.get_model_parameters()
        }
    
    def get_fantasy_success_rate(self) -> float:
        """Возвращает процент успешных фантазий"""
        if not hasattr(self, 'fantasy_results'):
            return 0.0
        
        total = len(self.fantasy_results)
        if total == 0:
            return 0.0
            
        successes = sum(1 for result in self.fantasy_results if result)
        return successes / total
    
    def get_average_value_prediction(self) -> float:
        """Возвращает среднюю предсказанную ценность"""
        if not self.fantasy_history:
            return 0.0
            
        values = [h['value'] for h in self.fantasy_history]
        return sum(values) / len(values)
    
    def get_model_parameters(self) -> Dict:
        """Возвращает информацию о параметрах модели"""
        return {
            'total_parameters': sum(
                p.numel() for p in self.network.parameters()
            ),
            'trainable_parameters': sum(
                p.numel() for p in self.network.parameters() if p.requires_grad
            ),
            'layer_sizes': {
                'input': self.state_size,
                'hidden': self.network.fc1.out_features,
                'output_fantasy': 1,
                'output_value': 1
            }
        }

class FantasyAgentTrainer:
    """Класс для обучения FantasyAgent"""
    
    def __init__(self, agent: FantasyAgent, config: Dict):
        self.agent = agent
        self.config = config
        self.training_history = []
        self.logger = get_logger(__name__)
    
    def train_episode(self, env) -> Dict:
        """Проводит один эпизод обучения"""
        state = env.reset()
        done = False
        episode_reward = 0
        
        while not done:
            # Получаем действие от агента
            action = self.agent.choose_move(
                env.get_board(),
                env.get_available_cards(),
                env.get_legal_moves()
            )
            
            # Делаем ход в среде
            next_state, reward, done, info = env.step(action)
            episode_reward += reward
            
            # Если это фантазия, обновляем статистику
            if info.get('fantasy_active', False):
                self.agent.fantasy_results.append(info.get('fantasy_success', False))
            
            state = next_state
        
        # Обучаем агента на результатах эпизода
        training_stats = self.agent.train_on_game({
            'fantasy_success': info.get('fantasy_success', False),
            'final_reward': episode_reward
        })
        
        # Сохраняем статистику эпизода
        episode_stats = {
            'episode_reward': episode_reward,
            'training_loss': training_stats['total_loss'],
            'fantasy_success': info.get('fantasy_success', False)
        }
        self.training_history.append(episode_stats)
        
        return episode_stats
    
    def train(self, num_episodes: int, save_frequency: int = 100):
        """Проводит полный цикл обучения"""
        for episode in range(num_episodes):
            stats = self.train_episode(self.env)
            
            # Логируем прогресс
            if episode % 10 == 0:
                self.logger.info(
                    f"Episode {episode}/{num_episodes}: "
                    f"Reward = {stats['episode_reward']:.2f}, "
                    f"Loss = {stats['training_loss']:.4f}"
                )
            
            # Сохраняем модель
            if episode % save_frequency == 0:
                self.save_checkpoint(episode)
    
    # agents/rl/fantasy_agent.py (продолжение)

    def save_checkpoint(self, episode: int):
        """Сохраняет чекпоинт обучения"""
        checkpoint_path = f"checkpoints/fantasy_agent_ep{episode}.pt"
        self.agent.save_model(checkpoint_path)
        
        # Сохраняем статистику обучения
        stats_path = f"checkpoints/fantasy_agent_ep{episode}_stats.json"
        with open(stats_path, 'w') as f:
            json.dump({
                'episode': episode,
                'training_history': self.training_history,
                'agent_stats': self.agent.get_training_stats(),
                'config': self.config
            }, f, indent=4)
        
        self.logger.info(f"Saved checkpoint at episode {episode}")
    
    def load_checkpoint(self, checkpoint_path: str):
        """Загружает чекпоинт обучения"""
        self.agent.load_model(checkpoint_path)
        
        # Загружаем статистику
        stats_path = checkpoint_path.replace('.pt', '_stats.json')
        if os.path.exists(stats_path):
            with open(stats_path, 'r') as f:
                stats = json.load(f)
                self.training_history = stats['training_history']
                self.config = stats['config']
    
    def get_training_summary(self) -> Dict:
        """Возвращает сводку по обучению"""
        if not self.training_history:
            return {}
        
        recent_episodes = self.training_history[-100:]  # последние 100 эпизодов
        
        return {
            'total_episodes': len(self.training_history),
            'average_reward': np.mean([ep['episode_reward'] for ep in recent_episodes]),
            'average_loss': np.mean([ep['training_loss'] for ep in recent_episodes]),
            'fantasy_success_rate': np.mean([
                1 if ep['fantasy_success'] else 0 
                for ep in recent_episodes
            ]),
            'agent_stats': self.agent.get_training_stats()
        }
    
    def plot_training_progress(self):
        """Визуализирует прогресс обучения"""
        if not self.training_history:
            return
        
        episodes = range(len(self.training_history))
        rewards = [ep['episode_reward'] for ep in self.training_history]
        losses = [ep['training_loss'] for ep in self.training_history]
        fantasy_success = [
            1 if ep['fantasy_success'] else 0 
            for ep in self.training_history
        ]
        
        plt.figure(figsize=(15, 5))
        
        # График наград
        plt.subplot(131)
        plt.plot(episodes, rewards)
        plt.title('Episode Rewards')
        plt.xlabel('Episode')
        plt.ylabel('Reward')
        
        # График функции потерь
        plt.subplot(132)
        plt.plot(episodes, losses)
        plt.title('Training Loss')
        plt.xlabel('Episode')
        plt.ylabel('Loss')
        
        # График успешности фантазий
        plt.subplot(133)
        window_size = 100
        fantasy_rate = pd.Series(fantasy_success).rolling(window_size).mean()
        plt.plot(episodes, fantasy_rate)
        plt.title('Fantasy Success Rate')
        plt.xlabel('Episode')
        plt.ylabel('Success Rate')
        
        plt.tight_layout()
        return plt.gcf()
