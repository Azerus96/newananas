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
            removedCards: new Set(),
            savedState: null,
            fouls: 0,
            totalMoves: 0,
            scoops: 0,
            totalGames: 0,
            animationEnabled: true
        };

        this.ui = new GameUI(this);
        this.stats = new GameStatistics();
        this.socket = io();
        this.setupSocketHandlers();
        this.initializeEventListeners();
        this.setupAnimationControl();
    }

    setupSocketHandlers() {
        this.socket.on('game_state', (state) => {
            this.updateGameState(state);
        });

        this.socket.on('ai_thinking', (data) => {
            this.ui.showAIThinking(data.player, data.thinkTime);
        });

        this.socket.on('game_over', (result) => {
            this.handleGameOver(result);
        });

        this.socket.on('fantasy_update', (data) => {
            this.handleFantasyUpdate(data);
        });

        this.socket.on('error', (error) => {
            this.ui.showError(error.message);
        });

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
            document.getElementById('thinkTimeValue').textContent = `${e.target.value}s`;
        });

        // Управление анимацией
        document.getElementById('animationControl').addEventListener('change', (e) => {
            this.state.animationEnabled = e.target.value !== 'off';
            document.body.classList.toggle('animations-disabled', !this.state.animationEnabled);
        });

        // Основные кнопки управления
        document.getElementById('startGame').addEventListener('click', () => this.startGame());
        document.getElementById('trainingMode').addEventListener('click', () => this.startTrainingMode());
        document.getElementById('viewStats').addEventListener('click', () => this.showFullStatistics());
        document.getElementById('tutorial').addEventListener('click', () => this.showTutorial());

        // Обработка навигации
        window.onpopstate = (event) => {
            if (this.state.gameStarted) {
                this.saveCurrentState();
                this.ui.showConfirmDialog(
                    "Выйти из игры?",
                    "Хотите вернуться в меню? Ваш прогресс будет сохранен.",
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

        // Клавиатурные сокращения
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
    }

    setupAnimationControl() {
        const animationControl = document.getElementById('animationControl');
        if (animationControl) {
            animationControl.innerHTML = `
                <option value="normal">Normal</option>
                <option value="fast">Fast</option>
                <option value="off">Off</option>
            `;
        }
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
            if (data.status === 'ok') {
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
            const gameConfig = {
                players: this.state.players,
                fantasyMode: this.state.fantasyMode,
                aiThinkTime: this.state.aiThinkTime,
                agents: this.collectAgentConfigs(),
                animationEnabled: this.state.animationEnabled
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
                await this.handlePlayerTurn();
            } else {
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
        this.ui.showAIThinking(this.state.currentPlayer);
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
            if (this.state.animationEnabled) {
                await this.ui.animateMove(data.move);
            } else {
                this.ui.applyMove(data.move);
            }
            this.updateGameState(data.game_state);
            
            // Проверяем на фолы и скупы
            if (data.move.isFoul) {
                this.state.fouls++;
            }
            if (data.move.isScoop) {
                this.state.scoops++;
            }
            this.state.totalMoves++;
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
            if (this.state.animationEnabled) {
                await this.ui.animateMove({ card, position });
            } else {
                this.ui.applyMove({ card, position });
            }
            
            this.updateGameState(data.game_state);
            
            // Обновляем статистику
            if (data.move.isFoul) {
                this.state.fouls++;
            }
            if (data.move.isScoop) {
                this.state.scoops++;
            }
            this.state.totalMoves++;
            
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
    this.stats.updateStats({
        foulsRate: this.state.fouls / this.state.totalMoves,
        scoopsRate: this.state.scoops / this.state.totalMoves,
        ...this.state
    });
    
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
    this.state.totalGames++;
    
    // Обновляем общую статистику
    this.stats.saveGameResult({
        ...result,
        foulsRate: this.state.fouls / this.state.totalMoves,
        scoopsRate: this.state.scoops / this.state.totalMoves
    });
    
    this.ui.showGameOver(result);
    localStorage.removeItem('savedGameState');
}

handleFantasyUpdate(data) {
    if (data.status === 'active') {
        this.state.inFantasy = true;
        this.ui.showFantasyMode();
    } else {
        this.state.inFantasy = false;
        this.ui.hideFantasyMode();
    }
}

handleKeyboardShortcuts(e) {
    if (e.ctrlKey || e.metaKey) {
        switch(e.key) {
            case 'z':
                e.preventDefault();
                this.undoLastMove();
                break;
            case 's':
                e.preventDefault();
                this.saveCurrentState();
                break;
            case 'f':
                e.preventDefault();
                this.toggleFullscreen();
                break;
        }
    }
}

async undoLastMove() {
    if (!this.state.gameStarted || this.state.currentPlayer !== 0) return;
    
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
            this.updateGameState(data.game_state);
            this.ui.undoLastMove();
        }
    } catch (error) {
        console.error('Failed to undo move:', error);
        this.ui.showError('Failed to undo move');
    }
}

toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen();
    } else {
        document.exitFullscreen();
    }
}

showTutorial() {
    this.ui.showTutorial(`
        <h2>Как играть в OFC Poker</h2>
        
        <h3>Основные правила</h3>
        <p>Open Face Chinese Poker - это покерная игра, где каждый игрок должен составить три покерных комбинации,
        располагая карты в три ряда: верхний (3 карты), средний (5 карт) и нижний (5 карт).</p>
        
        <h3>Размещение карт</h3>
        <ul>
            <li>Карты можно размещать только сверху вниз</li>
            <li>Нижняя комбинация должна быть сильнее средней</li>
            <li>Средняя комбинация должна быть сильнее верхней</li>
        </ul>
        
        <h3>Фантазия</h3>
        <p>Фантазия активируется, когда игрок собирает определенные комбинации. В режиме фантазии
        игрок получает дополнительные карты для размещения.</p>
        
        <h3>Статистика</h3>
        <ul>
            <li>Fouls Rate - процент нарушений правила старшинства комбинаций</li>
            <li>Scoops Rate - процент ситуаций, когда игрок выигрывает все три ряда</li>
        </ul>
        
        <h3>Управление</h3>
        <ul>
            <li>Перетащите карту в нужную позицию</li>
            <li>Ctrl+Z - отменить последний ход</li>
            <li>Ctrl+S - сохранить игру</li>
            <li>Ctrl+F - полноэкранный режим</li>
        </ul>
        
        <h3>Настройки</h3>
        <ul>
            <li>Animation: Normal/Fast/Off - управление анимациями</li>
            <li>AI Think Time - время на ход AI</li>
            <li>Fantasy Type - тип фантазии (Normal/Progressive/Disabled)</li>
                <li>Sound Effects - включение/выключение звуковых эффектов</li>
            </ul>
            
            <h3>Советы</h3>
            <ul>
                <li>Планируйте размещение карт заранее</li>
                <li>Следите за вышедшими картами</li>
                <li>Используйте статистику для улучшения игры</li>
                <li>В мобильной версии можно использовать свайпы для навигации</li>
            </ul>`);
    }

    saveCurrentState() {
        if (!this.state.gameStarted) return;

        const saveState = {
            timestamp: Date.now(),
            gameState: this.state
        };

        try {
            localStorage.setItem('savedGameState', JSON.stringify(saveState));
            
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

            const savedState = localStorage.getItem('savedGameState');
            if (savedState) {
                const { timestamp, gameState } = JSON.parse(savedState);
                
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

    calculateRates() {
        return {
            foulsRate: this.state.totalMoves ? (this.state.fouls / this.state.totalMoves) * 100 : 0,
            scoopsRate: this.state.totalMoves ? (this.state.scoops / this.state.totalMoves) * 100 : 0
        };
    }

    getGameStatistics() {
        const rates = this.calculateRates();
        return {
            totalGames: this.state.totalGames,
            totalMoves: this.state.totalMoves,
            fouls: this.state.fouls,
            scoops: this.state.scoops,
            foulsRate: rates.foulsRate.toFixed(1) + '%',
            scoopsRate: rates.scoopsRate.toFixed(1) + '%'
        };
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
            window.game.ui.openSidePanel();
        } else {
            window.game.ui.closeSidePanel();
        }
    }

    xDown = null;
    yDown = null;
}
