import pytest
from rlofc.core.game import Game, GameState
from rlofc.core.card import Card
from rlofc.core.board import Street

def test_game_initialization(game):
    """Тест инициализации игры"""
    assert game.state == GameState.WAITING
    assert game.current_player == 1

def test_game_start(game):
    """Тест начала игры"""
    game.start()
    assert game.state == GameState.IN_PROGRESS
    assert len(game.player1_cards) == 5
    assert len(game.player2_cards) == 5

def test_game_make_move(game):
    """Тест выполнения хода"""
    game.start()
    
    # Получаем начальные карты первого игрока
    initial_cards = len(game.player1_cards)
    
    # Делаем ход
    card = game.player1_cards[0]
    success = game.make_move(1, card, Street.BACK)
    
    assert success
    assert len(game.player1_cards) == initial_cards - 1

def test_game_completion(game):
    """Тест завершения игры"""
    game.start()
    
    # Играем до конца
    while not game.is_game_over():
        player = game.current_player
        cards = game.player1_cards if player == 1 else game.player2_cards
        board = game.player1_board if player == 1 else game.player2_board
        
        legal_moves = game.get_legal_moves(player)
        card, street = legal_moves[0]
        game.make_move(player, card, street)
    
    assert game.state == GameState.COMPLETED
    result = game.get_result()
    assert result.winner in [1, 2, None]
