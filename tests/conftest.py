import pytest
from rlofc.core.game import Game
from rlofc.agents.random import RandomAgent
from rlofc.utils.config import Config

@pytest.fixture
def config():
    """Фикстура с тестовой конфигурацией"""
    return Config({
        'game': {
            'seed': 42,
            'num_games': 10
        },
        'training': {
            'batch_size': 32,
            'learning_rate': 0.001,
            'gamma': 0.99,
            'epsilon_start': 1.0,
            'epsilon_end': 0.01,
            'epsilon_decay': 0.995
        }
    })

@pytest.fixture
def random_agent():
    """Фикстура с случайным агентом"""
    return RandomAgent(name="TestRandomAgent")

@pytest.fixture
def game(random_agent):
    """Фикстура с игрой"""
    return Game(random_agent, random_agent)
