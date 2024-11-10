# services/game_service.py
from utils.cache import cache
from utils.metrics import metrics
from utils.validators import validate_game_state

class GameService:
    def __init__(self):
        self.cache = cache
        self.metrics = metrics

    @cache.memoize(timeout=300)
    def get_game_state(self, game_id: str):
        try:
            game = self.load_game(game_id)
            return validate_game_state(game)
        except Exception as e:
            self.metrics.increment('game.state.error')
            raise GameServiceError(f"Failed to get game state: {str(e)}")

    @metrics.measure_time
    def make_move(self, game_id: str, move_data: dict):
        # Логика хода
        pass
