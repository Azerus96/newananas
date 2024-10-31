import pytest
import numpy as np
from rlofc.agents.random import RandomAgent
from rlofc.agents.rl.dqn import DQNAgent
from rlofc.core.board import Board, Street
from rlofc.core.card import Card

def test_random_agent_choice(random_agent, game):
    """Тест выбора хода случайным агентом"""
    board = Board()
    cards = [
        Card.from_string("Ah"),
        Card.from_string("Kh"),
        Card.from_string("Qh")
    ]
    legal_moves = [(card, street) for card in cards for street in Street]
    
    # Проверяем, что агент всегда выбирает допустимый ход
    for _ in range(100):
        move = random_agent.choose_move(board, cards, legal_moves)
        assert move in legal_moves

def test_dqn_agent_initialization(config):
    """Тест инициализации DQN агента"""
    state_size = 100
    action_size = 3
    
    agent = DQNAgent(
        name="TestDQN",
        state_size=state_size,
        action_size=action_size,
        config=config
    )
    
    assert agent.state_size == state_size
    assert agent.action_size == action_size
    assert agent.epsilon == config['training']['epsilon_start']

def test_dqn_agent_learning(config):
    """Тест обучения DQN агента"""
    agent = DQNAgent(
        name="TestDQN",
        state_size=100,
        action_size=3,
        config=config
    )
    
    # Генерируем тестовый опыт
    state = np.random.random(100)
    action = 1
    reward = 1.0
    next_state = np.random.random(100)
    done = False
    
    # Сохраняем опыт и обучаем
    agent.remember(state, action, reward, next_state, done)
    history = agent.replay(batch_size=1)
    
    assert 'loss' in history
