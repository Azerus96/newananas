# utils/validators.py
from marshmallow import Schema, fields, validates, ValidationError
from typing import Dict, Any

class CardSchema(Schema):
    rank = fields.Str(required=True)
    suit = fields.Str(required=True)
    
    @validates('rank')
    def validate_rank(self, value):
        valid_ranks = {'2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'}
        if value not in valid_ranks:
            raise ValidationError('Invalid card rank')

    @validates('suit')
    def validate_suit(self, value):
        valid_suits = {'h', 'd', 'c', 's'}
        if value not in valid_suits:
            raise ValidationError('Invalid card suit')

class MoveSchema(Schema):
    card = fields.Nested(CardSchema, required=True)
    position = fields.Int(required=True)
    
    @validates('position')
    def validate_position(self, value):
        if not 0 <= value <= 12:
            raise ValidationError('Invalid position')

def validate_game_state(state: Dict[str, Any]) -> Dict[str, Any]:
    required_fields = {'players', 'current_player', 'board_state', 'moves'}
    if not all(field in state for field in required_fields):
        raise ValidationError('Invalid game state structure')
    return state
