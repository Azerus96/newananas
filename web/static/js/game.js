class Game {
    constructor() {
        this.gameState = null;
        this.selectedCard = null;
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        document.getElementById('newGameBtn').addEventListener('click', () => this.startNewGame());
        
        // Добавляем обработчики для карт и улиц
        document.querySelectorAll('.street').forEach(street => {
            street.addEventListener('click', (e) => this.handleStreetClick(e));
        });
    }

    async startNewGame() {
        const opponentType = document.getElementById('opponentSelect').value;
        
        try {
            const response = await fetch('/api/new_game', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    opponent_type: opponentType
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
                    card: card,
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
            
            if (this.selectedCard && this.selectedCard.rank === card.rank && 
                this.selectedCard.suit === card.suit) {
                cardElement.classList.add('selected');
            }
            
            handElement.appendChild(cardElement);
        });
    }

    createCardElement(card) {
        const element = document.createElement('div');
        element.className = `card ${card.color}`;
        element.textContent = `${card.rank}${card.suit}`;
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

    showGameResult() {
        const result = this.gameState.result;
        const message = `
            Game Over!
            Winner: ${result.winner === 1 ? 'You' : 'Opponent'}
            Your Score: ${result.player1_score} (Royalties: ${result.player1_royalties})
            Opponent Score: ${result.player2_score} (Royalties: ${result.player2_royalties})
        `;
        
        alert(message);
    }

    showError(message) {
        const statusElement = document.getElementById('gameStatus');
        statusElement.textContent = `Error: ${message}`;
        statusElement.style.color = 'red';
        
        setTimeout(() => {
            statusElement.style.color = '';
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
}

// Инициализация игры при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.game = new Game();
});
