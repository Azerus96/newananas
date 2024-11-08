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
            removedCards: new Set(),
            savedState: null
        };

        this.ui = new GameUI(this);
        this.stats = new GameStatistics();
        this.socket = io();
        this.setupSocketHandlers();
        this.initializeEventListeners();
    }

    setupSocketHandlers() {
        this.socket.on('game_state', (state) => {
            this.updateGameState(state);
        });

        this.socket.on('ai_thinking', (data) => {
            this.ui.showAIThinking(data.player);
        });

        this.socket.on('game_over', (result) => {
            this.handleGameOver(result);
        });

        this.socket.on('error', (error) => {
            this.ui.showError(error.message);
        });

        // Обработка переподключения
        this.socket.on('connect', () => {
            if (this.state.gameStarted) {
                this.loadSavedState();
            }
        });
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
        document.getElementById('viewStats').addEventListener('click', () => this.showFullStatistics());

        // Обработка навигации
        window.onpopstate = (event) => {
            event.preventDefault();
            if (this.state.gameStarted) {
                this.saveCurrentState();
                this.showConfirmDialog(
                    "Exit game?",
                    "Do you want to return to menu? Your progress will be saved.",
                    () => this.returnToMenu(),
                    () => history.pushState(null, '', window.location.href)
                );
            }
        };

        // Обработка обновления страницы
        window.onbeforeunload = () => {
            if (this.state.gameStarted) {
                this.saveCurrentState();
            }
        };

        // Обработчик для мобильного меню
        document.getElementById('menuButton')?.addEventListener('click', () => {
            this.ui.toggleMobileMenu();
        });
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
            if (data.agents) {
                this.state.availableAgents = data.agents;
                this.ui.updateAgentSelectors(data.agents, this.state.players);
            }
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
                this.state.gameId = data.game_id;
                this.ui.switchToGame();
                this.initializeGameState(data.game_state);
                history.pushState({ gameStarted: true }, '', '/game');
            } else {
                this.ui.showError(data.message || 'Failed to start game');
            }
        } catch (error) {
            console.error('Failed to start game:', error);
            this.ui.showError('Failed to start game');
        }
    }

    collectAgentConfigs() {
        const configs = [];
        document.querySelectorAll('.ai-selector').forEach((selector, index) => {
            const agentType = selector.querySelector('select').value;
            const useLatest = selector.querySelector('#useLatestModel')?.checked ?? true;
            configs.push({
                type: agentType,
                useLatestModel: useLatest,
                thinkTime: this.state.aiThinkTime,
                position: index + 1
            });
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
                    player: this.state.currentPlayer,
                    gameId: this.state.gameId
                })
            });

            const data = await response.json();
            if (data.status === 'ok') {
                await this.ui.animateMove(data.move);
                this.updateGameState(data.game_state);
            }
        } catch (error) {
            console.error('AI move failed:', error);
            this.ui.showError('AI move failed');
        } finally {
            this.ui.hideAIThinking();
        }
    }

    async makeMove(card, position) {
        try {
            const response = await fetch('/api/make_move', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    gameId: this.state.gameId,
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
                this.ui.showError(data.message || 'Invalid move');
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
        
        // Сохраняем состояние после каждого обновления
        this.saveCurrentState();
    }

async checkGameState() {
        try {
            const response = await fetch(`/api/game/state?gameId=${this.state.gameId}`);
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
        this.state.gameOver = true;
        this.ui.showGameOver(result);
        this.stats.saveGameResult(result);
        
        // Очищаем сохраненное состояние
        localStorage.removeItem('savedGameState');
    }

    async startAIvsAI() {
        try {
            const agent1 = document.querySelector('#agent1Select').value;
            const agent2 = document.querySelector('#agent2Select').value;
            
            const response = await fetch('/api/ai_vs_ai', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    agent1: agent1,
                    agent2: agent2,
                    think_time: this.state.aiThinkTime
                })
            });

            const data = await response.json();
            if (data.status === 'ok') {
                this.state.gameStarted = true;
                this.state.gameId = data.game_id;
                this.state.isAIvsAI = true;
                this.ui.switchToGame();
                this.initializeGameState(data.game_state);
            }
        } catch (error) {
            console.error('Failed to start AI vs AI game:', error);
            this.ui.showError('Failed to start AI vs AI game');
        }
    }

    startTrainingMode() {
        window.location.href = '/training';
    }

    async showFullStatistics() {
        try {
            const response = await fetch('/api/statistics');
            const data = await response.json();
            if (data.status === 'ok') {
                this.ui.showStatisticsModal(data.statistics);
            }
        } catch (error) {
            console.error('Failed to load statistics:', error);
            this.ui.showError('Failed to load statistics');
        }
    }

    saveCurrentState() {
        if (!this.state.gameStarted) return;

        const saveState = {
            timestamp: Date.now(),
            gameState: this.state
        };

        try {
            localStorage.setItem('savedGameState', JSON.stringify(saveState));
            
            // Также сохраняем на сервере
            fetch('/api/save_game_state', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(saveState)
            });
        } catch (error) {
            console.error('Failed to save game state:', error);
        }
    }

    async loadSavedState() {
        try {
            // Сначала пробуем загрузить с сервера
            const serverResponse = await fetch('/api/load_game_state', {
                method: 'POST'
            });
            
            if (serverResponse.ok) {
                const data = await serverResponse.json();
                if (data.status === 'ok') {
                    this.initializeGameState(data.game_state);
                    return;
                }
            }

            // Если не получилось, пробуем локальное сохранение
            const savedState = localStorage.getItem('savedGameState');
            if (savedState) {
                const { timestamp, gameState } = JSON.parse(savedState);
                
                // Проверяем, не устарело ли сохранение (24 часа)
                if (Date.now() - timestamp < 24 * 60 * 60 * 1000) {
                    this.initializeGameState(gameState);
                } else {
                    localStorage.removeItem('savedGameState');
                }
            }
        } catch (error) {
            console.error('Failed to load saved state:', error);
        }
    }

    returnToMenu() {
        this.state.gameStarted = false;
        this.state.gameOver = false;
        this.ui.showMainMenu();
        history.pushState(null, '', '/');
    }

    showConfirmDialog(title, message, onConfirm, onCancel) {
        this.ui.showConfirmDialog({
            title,
            message,
            onConfirm: () => {
                onConfirm();
                this.ui.hideConfirmDialog();
            },
            onCancel: () => {
                if (onCancel) onCancel();
                this.ui.hideConfirmDialog();
            }
        });
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.game = new Game();
});

// Обработка мобильных жестов
if ('ontouchstart' in window) {
    document.addEventListener('touchstart', handleTouchStart);
    document.addEventListener('touchmove', handleTouchMove);
}

let xDown = null;
let yDown = null;

function handleTouchStart(evt) {
    xDown = evt.touches[0].clientX;
    yDown = evt.touches[0].clientY;
}

function handleTouchMove(evt) {
    if (!xDown || !yDown) return;

    const xUp = evt.touches[0].clientX;
    const yUp = evt.touches[0].clientY;

    const xDiff = xDown - xUp;
    const yDiff = yDown - yUp;

    if (Math.abs(xDiff) > Math.abs(yDiff)) {
        if (xDiff > 0) {
            // Свайп влево - открыть боковую панель
            window.game.ui.openSidePanel();
        } else {
            // Свайп вправо - закрыть боковую панель
            window.game.ui.closeSidePanel();
        }
    }

    xDown = null;
    yDown = null;
}
