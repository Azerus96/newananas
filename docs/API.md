# API Documentation

## Game Core

### Card

Представляет игральную карту.

```python
class Card:
    def __init__(self, rank: Rank, suit: Suit)
    def to_string(self) -> str
    def pretty_str(self) -> str
