// web/static/js/game.js

class Game {
    constructor() {
        this.gameState = null;
        this.selectedCard = null;
        this.initializeEventListeners();
        this.updateAgentsList();
    }

    initializeEventListeners() {
        document.getElementById('newGameBtn').addEventListener('click', () => this.startNewGame());
        
        // Добавляем обработчики для карт и улиц
        document.querySelectorAll('.street').forEach(street => {
            street.addEventListener('click', (e) => this.handleStreetClick(e));
        });

        // Добавляем обработчик для меню выбора агента
        document.getElementById('opponentSelect').addEventListener('change', () => {
            this.updateGameControls();
        });
    }

    async updateAgentsList() {
        try {
            const response = await fetch('/api/agents');
            const data = await response.json();
            
            const select = document.getElementById('opponentSelect');
            select.innerHTML = data.agents.map(agent => 
                `<option value="${agent.id}">${agent.name}</option>`
            ).join('');
            
            this.updateGameControls();
        } catch (error) {
            console.error('Failed to load agents:', error);
            this.showError('Failed to load available agents');
        }
    }

    updateGameControls() {
        const selectedAgent = document.getElementById('opponentSelect').value;
        const configPanel = document.getElementById('agentConfig');
        if (configPanel) {
            // Показываем специфичные для агента настройки
            configPanel.innerHTML = this.getAgentConfigHTML(selectedAgent);
        }
    }

    getAgentConfigHTML(agentType) {
        switch(agentType) {
            case 'dqn':
            case 'a3c':
            case 'ppo':
                return `
                    <div class="agent-settings">
                        <label>
                            <input type="checkbox" id="useLatestModel" checked>
                            Use latest trained model
                        </label>
                        <label>
                            Think time (ms):
                            <input type="number" id="thinkTime" value="1000" min="100" max="5000">
                        </label>
                    </div>
                `;
            default:
                return '';
        }
    }

    async startNewGame() {
        const opponentType = document.getElementById('opponentSelect').value;
        const useLatestModel = document.getElementById('useLatestModel')?.checked ?? true;
        const thinkTime = document.getElementById('thinkTime')?.value ?? 1000;
        
        try {
            const response = await fetch('/api/new_game', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    opponent_type: opponentType,
                    use_latest_model: useLatestModel,
                    think_time: parseInt(thinkTime),
                    progressive_fantasy: document.getElementById('progressiveFantasy')?.checked ?? false
                })
            });
            
            const data = await response.json();
            if (data.status === 'ok') {
                this.gameState = data.game_state;
                this.updateUI();
            } else {
                this.showError(data.message);
            }
        } catch (error) {
            this.showError('Failed to start new game');
            console.error('Error:', error);
        }
    }

    async makeMove(card, street) {
        try {
            const response = await fetch('/api/make_move', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    card: card.to_dict(),
                    street: street
                })
            });
            
            const data = await response.json();
            if (data.status === 'ok') {
                this.gameState = data.game_state;
                this.updateUI();
                
                if (this.gameState.is_game_over) {
                    this.showGameResult();
                }
            } else {
                this.showError(data.message);
            }
        } catch (error) {
            this.showError('Failed to make move');
            console.error('Error:', error);
        }
    }

    handleCardClick(card) {
        if (this.selectedCard === card) {
            this.selectedCard = null;
            this.updateUI();
        } else {
            this.selectedCard = card;
            this.updateUI();
        }
    }

    handleStreetClick(event) {
        if (!this.selectedCard) return;
        
        const streetElement = event.currentTarget;
        const streetId = this.getStreetId(streetElement);
        
        if (this.isValidMove(this.selectedCard, streetId)) {
            this.makeMove(this.selectedCard, streetId);
            this.selectedCard = null;
        }
    }

    updateUI() {
        if (!this.gameState) return;
        
        // Обновляем доски
        this.updateBoard('opponent', this.gameState.opponent_board);
        this.updateBoard('player', this.gameState.player_board);
        
        // Обновляем карты в руке
        this.updatePlayerHand();
        
        // Обновляем статус игры
        this.updateGameStatus();
        
        // Обновляем счет и фантазию
        this.updateScoreAndFantasy();
    }

    updateBoard(player, board) {
        ['front', 'middle', 'back'].forEach(street => {
            const streetElement = document.getElementById(`${player}${street.charAt(0).toUpperCase() + street.slice(1)}`);
            streetElement.innerHTML = '';
            
            board[street].forEach(card => {
                streetElement.appendChild(this.createCardElement(card));
            });
        });
    }

    updatePlayerHand() {
        const handElement = document.getElementById('playerHand');
        handElement.innerHTML = '';
        
        this.gameState.player_cards.forEach(card => {
            const cardElement = this.createCardElement(card);
            cardElement.addEventListener('click', () => this.handleCardClick(card));
            
            if (this.selectedCard && this.selectedCard.id === card.id) {
                cardElement.classList.add('selected');
            }
            
            handElement.appendChild(cardElement);
        });
    }

    createCardElement(card) {
        const element = document.createElement('div');
        element.className = `card ${card.color}`;
        element.textContent = `${card.rank}${card.suit}`;
        element.dataset.cardId = card.id;
        return element;
    }

    updateGameStatus() {
        const statusElement = document.getElementById('gameStatus');
        
        if (this.gameState.is_game_over) {
            const result = this.gameState.result;
            let message = '';
            
            if (result.winner === 1) {
                message = `You won! Score: ${result.player1_score} (Royalties: ${result.player1_royalties})`;
            } else if (result.winner === 2) {
                message = `Opponent won! Score: ${result.player2_score} (Royalties: ${result.player2_royalties})`;
            } else {
                message = 'Game ended in a draw!';
            }
            
            statusElement.textContent = message;
        } else {
            statusElement.textContent = this.gameState.current_player === 1 ? 
                'Your turn' : 'Opponent\'s turn';
        }
    }

    updateScoreAndFantasy() {
        const scoreElement = document.getElementById('score');
        if (scoreElement) {
            scoreElement.textContent = `Score: ${this.gameState.player1_score} - ${this.gameState.player2_score}`;
        }

        const fantasyElement = document.getElementById('fantasy');
        if (fantasyElement && this.gameState.fantasy_status) {
            fantasyElement.textContent = `Fantasy: ${this.gameState.fantasy_status.description}`;
            fantasyElement.className = this.gameState.fantasy_status.active ? 'active' : '';
        }
    }

    showGameResult() {
        const result = this.gameState.result;
        const message = `
            Game Over!
            Winner: ${result.winner === 1 ? 'You' : 'Opponent'}
            Your Score: ${result.player1_score} (Royalties: ${result.player1_royalties})
            Opponent Score: ${result.player2_score} (Royalties: ${result.player2_royalties})
        `;
        
        const modalDiv = document.createElement('div');
        modalDiv.className = 'game-result-modal';
        modalDiv.innerHTML = `
            <div class="modal-content">
                <h2>Game Over</h2>
                <p>${message}</p>
                <button onclick="this.parentElement.parentElement.remove()">Close</button>
                <button onclick="game.startNewGame()">New Game</button>
            </div>
        `;
        
        document.body.appendChild(modalDiv);
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        
        document.querySelector('.container').prepend(errorDiv);
        
        setTimeout(() => {
            errorDiv.remove();
        }, 3000);
    }

    getStreetId(streetElement) {
        if (streetElement.classList.contains('front')) return 0;
        if (streetElement.classList.contains('middle')) return 1;
        if (streetElement.classList.contains('back')) return 2;
        return -1;
    }

    isValidMove(card, streetId) {
        if (!this.gameState || this.gameState.current_player !== 1) return false;
        
        const board = this.gameState.player_board;
        const street = ['front', 'middle', 'back'][streetId];
        
        // Проверяем, что улица не заполнена
        return board[street].length < (streetId === 0 ? 3 : 5);
    }

    async checkGameState() {
        try {
            const response = await fetch('/api/game/state');
            const data = await response.json();
            
            if (data.status === 'ok') {
                this.gameState = data.game_state;
                this.updateUI();
            }
        } catch (error) {
            console.error('Failed to check game state:', error);
        }
    }

    // Методы для работы с анимациями
    animateCard(cardElement, targetElement) {
        const startRect = cardElement.getBoundingClientRect();
        const targetRect = targetElement.getBoundingClientRect();
        
        const clone = cardElement.cloneNode(true);
        clone.style.position = 'fixed';
        clone.style.left = startRect.left + 'px';
        clone.style.top = startRect.top + 'px';
        clone.style.transition = 'all 0.3s ease-in-out';
        
        document.body.appendChild(clone);
        
        setTimeout(() => {
            clone.style.left = targetRect.left + 'px';
            clone.style.top = targetRect.top + 'px';
        }, 0);
        
        setTimeout(() => {
            clone.remove();
            this.updateUI();
        }, 300);
    }

    // Методы для работы с историей ходов
    addToHistory(move) {
        const historyElement = document.getElementById('moveHistory');
        if (historyElement) {
            const moveElement = document.createElement('div');
            moveElement.className = 'history-item';
            moveElement.textContent = `${move.player === 1 ? 'You' : 'Opponent'}: ${move.card.rank}${move.card.suit} to ${move.street}`;
            historyElement.appendChild(moveElement);
            historyElement.scrollTop = historyElement.scrollHeight;
        }
    }
}

// Инициализация игры при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.game = new Game();
});

// Добавляем стили для модального окна результатов
const style = document.createElement('style');
style.textContent = `
    .game-result-modal {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 1000;
    }

    .modal-content {
        background: white;
        padding: 20px;
        border-radius: 8px;
        text-align: center;
    }

    .modal-content button {
        margin: 10px;
        padding: 8px 16px;
        border: none;
        border-radius: 4px;
        background: #007bff;
        color: white;
        cursor: pointer;
    }

    .modal-content button:hover {
        background: #0056b3;
    }

    .error-message {
        position: fixed;
        top: 20px;
        right: 20px;
        background: #ff4444;
        color: white;
        padding: 10px 20px;
        border-radius: 4px;
        animation: slideIn 0.3s ease-out;
    }

    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;

document.head.appendChild(style);
