// web/static/js/game.js

class Game {
    constructor() {
        this.state = {
            players: 2,
            currentPlayer: 0,
            fantasyMode: 'normal',
            aiThinkTime: 30,
            agents: [],
            gameStarted: false,
            inFantasy: false,
            removedCards: new Set()
        };

        this.ui = new GameUI(this);
        this.stats = new GameStatistics();
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Обработчики меню
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', () => this.setPlayerCount(parseInt(btn.dataset.players)));
        });

        document.getElementById('fantasyType').addEventListener('change', (e) => {
            this.state.fantasyMode = e.target.value;
        });

        document.getElementById('aiThinkTime').addEventListener('input', (e) => {
            this.state.aiThinkTime = parseInt(e.target.value);
            document.getElementById('thinkTimeValue').textContent = e.target.value;
        });

        document.getElementById('startGame').addEventListener('click', () => this.startGame());
        document.getElementById('trainingMode').addEventListener('click', () => this.startTrainingMode());
    }

    async setPlayerCount(count) {
        this.state.players = count;
        this.ui.updatePlayerCount(count);
        await this.loadAvailableAgents();
    }

    async loadAvailableAgents() {
        try {
            const response = await fetch('/api/agents');
            const data = await response.json();
            this.ui.updateAgentSelectors(data.agents, this.state.players);
        } catch (error) {
            console.error('Failed to load agents:', error);
            this.ui.showError('Failed to load AI agents');
        }
    }

    async startGame() {
        try {
            // Собираем конфигурацию игры
            const gameConfig = {
                players: this.state.players,
                fantasyMode: this.state.fantasyMode,
                aiThinkTime: this.state.aiThinkTime,
                agents: this.collectAgentConfigs()
            };

            const response = await fetch('/api/new_game', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(gameConfig)
            });

            const data = await response.json();
            if (data.status === 'ok') {
                this.state.gameStarted = true;
                this.ui.switchToGame();
                this.initializeGameState(data.game_state);
            } else {
                this.ui.showError(data.message);
            }
        } catch (error) {
            console.error('Failed to start game:', error);
            this.ui.showError('Failed to start game');
        }
    }

    collectAgentConfigs() {
        const configs = [];
        document.querySelectorAll('.ai-selector').forEach(selector => {
            const agentType = selector.querySelector('select').value;
            const config = {
                type: agentType,
                useLatestModel: selector.querySelector('#useLatestModel')?.checked ?? true,
                thinkTime: this.state.aiThinkTime
            };
            configs.push(config);
        });
        return configs;
    }

    initializeGameState(gameState) {
        this.state = { ...this.state, ...gameState };
        this.ui.updateGameState(this.state);
        this.startGameLoop();
    }

    async startGameLoop() {
        while (this.state.gameStarted && !this.state.gameOver) {
            if (this.state.currentPlayer === 0) {
                // Ход человека
                await this.handlePlayerTurn();
            } else {
                // Ход AI
                await this.handleAITurn();
            }
            await this.checkGameState();
        }
    }

    async handlePlayerTurn() {
        this.ui.enablePlayerInput();
        return new Promise(resolve => {
            this.resolvePlayerTurn = resolve;
        });
    }

    async handleAITurn() {
        this.ui.showAIThinking();
        try {
            const response = await fetch('/api/ai_move', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    player: this.state.currentPlayer
                })
            });

            const data = await response.json();
            if (data.status === 'ok') {
                this.ui.animateMove(data.move);
                this.updateGameState(data.game_state);
            }
        } catch (error) {
            console.error('AI move failed:', error);
            this.ui.showError('AI move failed');
        }
        this.ui.hideAIThinking();
    }

    async makeMove(card, position) {
        try {
            const response = await fetch('/api/make_move', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    card: card,
                    position: position
                })
            });

            const data = await response.json();
            if (data.status === 'ok') {
                this.updateGameState(data.game_state);
                if (this.resolvePlayerTurn) {
                    this.resolvePlayerTurn();
                }
                return true;
            } else {
                this.ui.showError(data.message);
                return false;
            }
        } catch (error) {
            console.error('Move failed:', error);
            this.ui.showError('Failed to make move');
            return false;
        }
    }

    updateGameState(newState) {
        this.state = { ...this.state, ...newState };
        this.ui.updateGameState(this.state);
        this.stats.updateStats(this.state);
    }

    async checkGameState() {
        try {
            const response = await fetch('/api/game/state');
            const data = await response.json();
            if (data.status === 'ok') {
                this.updateGameState(data.game_state);
                if (data.game_state.gameOver) {
                    this.handleGameOver(data.game_state.result);
                }
            }
        } catch (error) {
            console.error('Failed to check game state:', error);
        }
    }

    handleGameOver(result) {
        this.state.gameStarted = false;
        this.ui.showGameOver(result);
        this.stats.saveGameResult(result);
    }

    startTrainingMode() {
        window.location.href = '/training';
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.game = new Game();
});
