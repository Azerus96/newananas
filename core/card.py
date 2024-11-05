from dataclasses import dataclass
from enum import Enum, auto
from typing import List

class Suit(Enum):
    SPADES = auto()
    HEARTS = auto()
    DIAMONDS = auto()
    CLUBS = auto()

    @classmethod
    def from_char(cls, char: str) -> 'Suit':
        mapping = {'s': cls.SPADES, 'h': cls.HEARTS, 
                  'd': cls.DIAMONDS, 'c': cls.CLUBS}
        return mapping[char.lower()]

    def to_char(self) -> str:
        mapping = {self.SPADES: 's', self.HEARTS: 'h',
                  self.DIAMONDS: 'd', self.CLUBS: 'c'}
        return mapping[self]

class Rank(Enum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

    @classmethod
    def from_char(cls, char: str) -> 'Rank':
        mapping = {
            '2': cls.TWO, '3': cls.THREE, '4': cls.FOUR,
            '5': cls.FIVE, '6': cls.SIX, '7': cls.SEVEN,
            '8': cls.EIGHT, '9': cls.NINE, 'T': cls.TEN,
            'J': cls.JACK, 'Q': cls.QUEEN, 'K': cls.KING,
            'A': cls.ACE
        }
        return mapping[char.upper()]

    def to_char(self) -> str:
        mapping = {
            self.TWO: '2', self.THREE: '3', self.FOUR: '4',
            self.FIVE: '5', self.SIX: '6', self.SEVEN: '7',
            self.EIGHT: '8', self.NINE: '9', self.TEN: 'T',
            self.JACK: 'J', self.QUEEN: 'Q', self.KING: 'K',
            self.ACE: 'A'
        }
        return mapping[self]

@dataclass(frozen=True)
class Card:
    rank: Rank
    suit: Suit

    @classmethod
    def from_string(cls, card_str: str) -> 'Card':
        """Create card from string representation (e.g. 'Ah' for Ace of Hearts)"""
        if len(card_str) != 2:
            raise ValueError(f"Invalid card string: {card_str}")
        rank = Rank.from_char(card_str[0])
        suit = Suit.from_char(card_str[1])
        return cls(rank=rank, suit=suit)

    def to_string(self) -> str:
        """Convert card to string representation"""
        return f"{self.rank.to_char()}{self.suit.to_char()}"

    def __str__(self) -> str:
        return self.to_string()

    def __repr__(self) -> str:
        return f"Card('{self.to_string()}')"

    def to_dict(self):
        """Convert card to dictionary representation"""
        return {
            'rank': self.rank.to_char(),
            'suit': self.suit.to_char(),
            'color': 'red' if self.suit in (Suit.HEARTS, Suit.DIAMONDS) else 'black',
            'display': f"{self.rank.to_char()}{self.suit.to_char()}",
            'id': f"{self.rank.to_char()}{self.suit.to_char()}"
        }

    @property
    def prime_value(self) -> int:
        """Get prime number value for hand evaluation"""
        prime_values = {
            Rank.TWO: 2, Rank.THREE: 3, Rank.FOUR: 5,
            Rank.FIVE: 7, Rank.SIX: 11, Rank.SEVEN: 13,
            Rank.EIGHT: 17, Rank.NINE: 19, Rank.TEN: 23,
            Rank.JACK: 29, Rank.QUEEN: 31, Rank.KING: 37,
            Rank.ACE: 41
        }
        return prime_values[self.rank]

    @property
    def color(self) -> str:
        """Get card color for display"""
        return 'red' if self.suit in (Suit.HEARTS, Suit.DIAMONDS) else 'black'

    def pretty_str(self) -> str:
        """Get formatted string for display"""
        return f"[{self.rank.to_char()} {self.suit.to_char()}]"

    @classmethod
    def get_all_cards(cls) -> List['Card']:
        """Returns a list of all possible cards"""
        return [cls(rank=rank, suit=suit) 
                for rank in Rank 
                for suit in Suit]
