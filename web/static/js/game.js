class Game {
    constructor() {
        // Инициализация с проверкой готовности DOM
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initialize());
        } else {
            this.initialize();
        }
    }

    async initialize() {
        try {
            await this.waitForDOM();
            this.initializeState();
            this.ui = new GameUI(this);
            await this.loadResources();
            this.setupEventListeners();
            this.setupSocketHandlers();
            this.loadSavedState();
        } catch (error) {
            console.error('Game initialization failed:', error);
            this.handleInitializationError(error);
        }
    }

    waitForDOM() {
        return new Promise(resolve => {
            if (document.readyState === 'complete') {
                resolve();
            } else {
                document.addEventListener('DOMContentLoaded', resolve);
            }
        });
    }

    initializeState() {
        this.state = {
            players: 2,
            currentPlayer: 0,
            fantasyMode: 'normal',
            aiThinkTime: 30,
            agents: [],
            gameStarted: false,
            inFantasy: false,
            removedCards: new Set(),
            savedState: null,
            fouls: 0,
            totalMoves: 0,
            scoops: 0,
            totalGames: 0,
            animationEnabled: true
        };
    }

    async loadResources() {
        try {
            await Promise.all([
                this.loadAgents(),
                this.loadSettings(),
                this.loadStatistics()
            ]);
        } catch (error) {
            console.error('Failed to load resources:', error);
            throw new Error('Resource loading failed');
        }
    }

    setupEventListeners() {
        // Обработка клавиатуры с предотвращением множественных обработчиков
        const handleKeyboard = this.handleKeyboardInput.bind(this);
        document.removeEventListener('keydown', handleKeyboard);
        document.addEventListener('keydown', handleKeyboard);

        // Обработка изменения размера окна
        const handleResize = this.handleWindowResize.bind(this);
        window.removeEventListener('resize', handleResize);
        window.addEventListener('resize', handleResize);

        // Обработка состояния сети
        window.addEventListener('online', () => this.handleOnlineStatus(true));
        window.addEventListener('offline', () => this.handleOnlineStatus(false));
    }

    setupSocketHandlers() {
        this.socket = io({
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            timeout: 20000
        });

        this.socket.on('connect', () => this.handleSocketConnect());
        this.socket.on('disconnect', () => this.handleSocketDisconnect());
        this.socket.on('error', (error) => this.handleSocketError(error));
        this.socket.on('game_state', (state) => this.handleGameState(state));
        this.socket.on('game_over', (result) => this.handleGameOver(result));
    }

    async loadSavedState() {
        try {
            const savedState = localStorage.getItem('gameState');
            if (savedState) {
                const state = JSON.parse(savedState);
                if (this.isValidSavedState(state)) {
                    await this.restoreState(state);
                }
            }
        } catch (error) {
            console.error('Failed to load saved state:', error);
        }
    }

    isValidSavedState(state) {
        return state && 
               typeof state === 'object' && 
               'gameStarted' in state &&
               'players' in state;
    }

    async restoreState(state) {
        try {
            this.state = { ...this.state, ...state };
            if (this.state.gameStarted) {
                await this.resumeGame();
            }
        } catch (error) {
            console.error('Failed to restore state:', error);
            this.resetState();
        }
    }

    async resumeGame() {
        try {
            const response = await fetch('/api/resume_game', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    gameState: this.state
                })
            });

            if (!response.ok) {
                throw new Error('Failed to resume game');
            }

            const data = await response.json();
            this.updateGameState(data.gameState);
        } catch (error) {
            console.error('Failed to resume game:', error);
            this.ui.showError('Failed to resume game');
        }
    }

    resetState() {
        this.initializeState();
        localStorage.removeItem('gameState');
    }

    async makeMove(card, position) {
        if (!this.validateMove(card, position)) {
            this.ui.showError('Invalid move');
            return false;
        }

        try {
            const response = await this.sendMove(card, position);
            if (response.status === 'ok') {
                await this.handleMoveSuccess(response);
                return true;
            } else {
                this.handleMoveError(response.error);
                return false;
            }
        } catch (error) {
            this.handleMoveError(error);
            return false;
        }
    }

    validateMove(card, position) {
        if (!this.state.gameStarted || this.state.currentPlayer !== 0) {
            return false;
        }

        return this.isValidCard(card) && this.isValidPosition(position);
    }

    async sendMove(card, position) {
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

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        return await response.json();
    }

    async handleMoveSuccess(response) {
        if (this.state.animationEnabled) {
            await this.ui.animateMove(response.move);
        } else {
            this.ui.applyMove(response.move);
        }

        this.updateGameState(response.gameState);
        this.updateStatistics(response.move);
    }

    handleMoveError(error) {
        console.error('Move failed:', error);
        this.ui.showError('Failed to make move');
    }

    updateGameState(newState) {
        this.state = { ...this.state, ...newState };
        this.ui.updateGameState(this.state);
        this.saveState();
    }

    updateStatistics(move) {
        if (move.isFoul) {
            this.state.fouls++;
        }
        if (move.isScoop) {
            this.state.scoops++;
        }
        this.state.totalMoves++;
    }

    saveState() {
        try {
            localStorage.setItem('gameState', JSON.stringify(this.state));
        } catch (error) {
            console.error('Failed to save state:', error);
        }
    }

    handleSocketConnect() {
        console.log('Socket connected');
        if (this.state.gameStarted) {
            this.syncGameState();
        }
    }

    handleSocketDisconnect() {
        console.log('Socket disconnected');
        this.ui.showError('Connection lost. Trying to reconnect...');
    }

    handleSocketError(error) {
        console.error('Socket error:', error);
        this.ui.showError('Connection error occurred');
    }

    async syncGameState() {
        try {
            const response = await fetch(`/api/game/state/${this.state.gameId}`);
            const data = await response.json();
            if (data.status === 'ok') {
                this.updateGameState(data.gameState);
            }
        } catch (error) {
            console.error('Failed to sync game state:', error);
        }
    }

    handleGameState(state) {
        this.updateGameState(state);
        if (state.currentPlayer !== 0 && !this.state.aiThinking) {
            this.handleAITurn();
        }
    }

    async handleAITurn() {
        this.state.aiThinking = true;
        this.ui.showAIThinking(this.state.currentPlayer);

        try {
            const response = await fetch('/api/ai_move', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    gameId: this.state.gameId,
                    player: this.state.currentPlayer
                })
            });

            const data = await response.json();
            if (data.status === 'ok') {
                await this.handleAIMove(data);
            } else {
                throw new Error(data.error || 'AI move failed');
            }
        } catch (error) {
            console.error('AI move failed:', error);
            this.ui.showError('AI failed to make a move');
        } finally {
            this.state.aiThinking = false;
            this.ui.hideAIThinking();
        }
    }

    async handleAIMove(data) {
        if (this.state.animationEnabled) {
            await this.ui.animateMove(data.move);
        } else {
            this.ui.applyMove(data.move);
        }
        this.updateGameState(data.gameState);
        this.updateStatistics(data.move);
    }

    handleGameOver(result) {
        this.state.gameStarted = false;
        this.state.gameOver = true;
        this.state.totalGames++;
        
        this.updateFinalStatistics(result);
        this.ui.showGameOver(result);
        this.resetState();
    }

    updateFinalStatistics(result) {
        const stats = {
            gamesPlayed: this.state.totalGames,
            wins: result.winner === 0 ? this.state.wins + 1 : this.state.wins,
            foulsRate: this.state.fouls / this.state.totalMoves,
            scoopsRate: this.state.scoops / this.state.totalMoves
        };

        try {
            fetch('/api/statistics', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(stats)
            });
        } catch (error) {
            console.error('Failed to update statistics:', error);
        }
    }

    handleKeyboardInput(e) {
        if (e.ctrlKey || e.metaKey) {
            switch(e.key.toLowerCase()) {
                case 'z':
                    e.preventDefault();
                    this.undoLastMove();
                    break;
                case 's':
                    e.preventDefault();
                    this.saveGame();
                    break;
                case 'f':
                    e.preventDefault();
                    this.toggleFullscreen();
                    break;
            }
        }
    }

    async undoLastMove() {
        if (!this.state.gameStarted || this.state.currentPlayer !== 0) {
            return;
        }

        try {
            const response = await fetch('/api/undo_move', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    gameId: this.state.gameId
                })
            });

            const data = await response.json();
            if (data.status === 'ok') {
                this.updateGameState(data.gameState);
                this.ui.undoLastMove();
            }
        } catch (error) {
            console.error('Failed to undo move:', error);
            this.ui.showError('Failed to undo move');
        }
    }

    async saveGame() {
        try {
            const response = await fetch('/api/save_game', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    gameState: this.state
                })
            });

            const data = await response.json();
            if (data.status === 'ok') {
                this.ui.showMessage('Game saved successfully');
            } else {
                throw new Error(data.error || 'Failed to save game');
            }
        } catch (error) {
            console.error('Failed to save game:', error);
            this.ui.showError('Failed to save game');
        }
    }

    toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch(err => {
                this.ui.showError('Error attempting to enable fullscreen');
            });
        } else {
            document.exitFullscreen();
        }
    }

    handleWindowResize() {
        this.ui.updateLayout();
    }

    handleOnlineStatus(isOnline) {
        if (isOnline) {
            this.ui.hideOfflineIndicator();
            if (this.state.gameStarted) {
                this.syncGameState();
            }
        } else {
            this.ui.showOfflineIndicator();
        }
    }

    handleInitializationError(error) {
        console.error('Initialization error:', error);
        this.ui.showError('Failed to initialize game');
    }

    isValidCard(card) {
        return card && 
               typeof card.rank === 'string' && 
               typeof card.suit === 'string' &&
               !this.state.removedCards.has(`${card.rank}${card.suit}`);
    }

    isValidPosition(position) {
        return typeof position === 'number' && 
               position >= 0 && 
               position < 13;
    }
}

// Экспорт класса
export default Game;
