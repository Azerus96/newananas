// web/static/js/ui.js

class GameUI {
    constructor(game) {
        this.game = game;
        this.selectedCard = null;
        this.draggedCard = null;
        this.initializeElements();
        this.setupDragAndDrop();
    }

    initializeElements() {
        this.elements = {
            mainMenu: document.getElementById('mainMenu'),
            gameContainer: document.getElementById('gameContainer'),
            playersContainer: document.getElementById('playersContainer'),
            playerHand: document.getElementById('playerHand'),
            removedCards: document.getElementById('removedCards'),
            moveHistory: document.getElementById('moveHistory'),
            gameStatus: document.getElementById('currentTurn'),
            gameTimer: document.getElementById('gameTimer'),
            cardSlots: document.getElementById('cardSlots'),
            trainingControls: document.getElementById('trainingControls')
        };
    }

    setupDragAndDrop() {
        // Настройка Drag & Drop для карт
        document.addEventListener('dragstart', (e) => {
            if (e.target.classList.contains('card')) {
                this.draggedCard = e.target;
                e.target.classList.add('dragging');
            }
        });

        document.addEventListener('dragend', (e) => {
            if (e.target.classList.contains('card')) {
                e.target.classList.remove('dragging');
                this.draggedCard = null;
            }
        });

        // Настройка слотов для карт
        document.querySelectorAll('.card-slot').forEach(slot => {
            slot.addEventListener('dragover', (e) => {
                e.preventDefault();
                if (this.isValidDropTarget(slot)) {
                    slot.classList.add('droppable');
                }
            });

            slot.addEventListener('dragleave', (e) => {
                slot.classList.remove('droppable');
            });

            slot.addEventListener('drop', (e) => {
                e.preventDefault();
                slot.classList.remove('droppable');
                if (this.draggedCard && this.isValidDropTarget(slot)) {
                    this.handleCardDrop(this.draggedCard, slot);
                }
            });
        });
    }

    switchToGame() {
        this.elements.mainMenu.style.display = 'none';
        this.elements.gameContainer.style.display = 'grid';
        this.initializeGameBoard();
    }

    initializeGameBoard() {
        // Создаем доски для всех игроков
        this.elements.playersContainer.innerHTML = '';
        const template = document.getElementById('playerBoardTemplate');
        
        for (let i = 0; i < this.game.state.players; i++) {
            const board = template.content.cloneNode(true);
            const boardElement = board.querySelector('.player-board');
            boardElement.dataset.player = i;
            
            // Настраиваем информацию об игроке
            const playerInfo = boardElement.querySelector('.player-info');
            playerInfo.querySelector('.player-name').textContent = 
                i === 0 ? 'You' : `AI ${i}`;
            
            this.elements.playersContainer.appendChild(board);
        }

        // Устанавливаем правильный layout
        this.elements.playersContainer.dataset.players = this.game.state.players;
    }

    updateGameState(state) {
        // Обновляем статус игры
        this.elements.gameStatus.textContent = 
            state.currentPlayer === 0 ? 'Your turn' : `AI ${state.currentPlayer} thinking...`;

        // Обновляем карты в руке
        this.updatePlayerHand(state.playerCards);

        // Обновляем доски всех игроков
        this.updateBoards(state);

        // Обновляем вышедшие карты
        this.updateRemovedCards(state.removedCards);

        // Обновляем историю ходов
        if (state.lastMove) {
            this.addMoveToHistory(state.lastMove);
        }

        // Обновляем статус фантазии
        this.updateFantasyStatus(state.inFantasy);
    }

    updatePlayerHand(cards) {
        this.elements.playerHand.innerHTML = '';
        cards.forEach(card => {
            const cardElement = this.createCardElement(card);
            cardElement.draggable = true;
            cardElement.addEventListener('click', () => this.handleCardClick(cardElement));
            this.elements.playerHand.appendChild(cardElement);
        });
    }

    createCardElement(card) {
        const element = document.createElement('div');
        element.className = `card ${card.suit === 'h' || card.suit === 'd' ? 'red' : 'black'}`;
        element.dataset.card = JSON.stringify(card);
        element.innerHTML = `
            <div class="card-inner">
                <span class="card-value">${card.rank}</span>
                <span class="card-suit">${this.getSuitSymbol(card.suit)}</span>
            </div>
        `;
        return element;
    }

    getSuitSymbol(suit) {
        const symbols = {
            'h': '♥',
            'd': '♦',
            'c': '♣',
            's': '♠'
        };
        return symbols[suit] || suit;
    }

    updateBoards(state) {
        state.boards.forEach((board, playerIndex) => {
            const boardElement = document.querySelector(`.player-board[data-player="${playerIndex}"]`);
            if (!boardElement) return;

            // Обновляем карты на каждой улице
            ['top', 'middle', 'bottom'].forEach((row, rowIndex) => {
                const slots = boardElement.querySelector(`.pyramid-row.${row}`).children;
                const cards = board[row];
                
                for (let i = 0; i < slots.length; i++) {
                    const slot = slots[i];
                    const card = cards[i];
                    
                    slot.innerHTML = '';
                    if (card) {
                        slot.appendChild(this.createCardElement(card));
                        slot.classList.add('occupied');
                    } else {
                        slot.classList.remove('occupied');
                    }
                }
            });

            // Обновляем счет
            boardElement.querySelector('.player-score').textContent = 
                `Score: ${state.scores[playerIndex]}`;
        });
    }

    updateRemovedCards(cards) {
        this.elements.removedCards.innerHTML = '';
        cards.forEach(card => {
            const cardElement = this.createCardElement(card);
            cardElement.classList.add('removed');
            this.elements.removedCards.appendChild(cardElement);
        });
    }

    addMoveToHistory(move) {
        const moveElement = document.createElement('div');
        moveElement.className = 'history-item';
        moveElement.textContent = `${move.player === 0 ? 'You' : 'AI ' + move.player}: ${move.card.rank}${move.card.suit} to ${move.position}`;
        this.elements.moveHistory.appendChild(moveElement);
        this.elements.moveHistory.scrollTop = this.elements.moveHistory.scrollHeight;
    }

    updateFantasyStatus(inFantasy) {
        document.body.classList.toggle('fantasy-mode', inFantasy);
        // Дополнительные визуальные эффекты для режима фантазии
    }

    handleCardClick(cardElement) {
        if (this.selectedCard === cardElement) {
            this.deselectCard();
        } else {
            this.selectCard(cardElement);
        }
    }

    selectCard(cardElement) {
        if (this.selectedCard) {
            this.selectedCard.classList.remove('selected');
        }
        this.selectedCard = cardElement;
        cardElement.classList.add('selected');
        this.highlightValidSlots();
    }

    deselectCard() {
        if (this.selectedCard) {
            this.selectedCard.classList.remove('selected');
            this.selectedCard = null;
            this.clearHighlightedSlots();
        }
    }

    highlightValidSlots() {
        const card = JSON.parse(this.selectedCard.dataset.card);
        document.querySelectorAll('.card-slot').forEach(slot => {
            if (this.isValidMove(card, slot)) {
                slot.classList.add('valid-target');
            }
        });
    }

    clearHighlightedSlots() {
        document.querySelectorAll('.card-slot').forEach(slot => {
            slot.classList.remove('valid-target');
        });
    }

    isValidMove(card, slot) {
        if (slot.classList.contains('occupied')) return false;
        
        const position = parseInt(slot.dataset.position);
        const row = this.getRowFromPosition(position);
        
        // Проверяем правила размещения карт
        return this.game.isValidCardPlacement(card, row, position);
    }

    getRowFromPosition(position) {
        if (position < 3) return 'top';
        if (position < 8) return 'middle';
        return 'bottom';
    }

    async handleCardDrop(cardElement, slot) {
        const card = JSON.parse(cardElement.dataset.card);
        const position = parseInt(slot.dataset.position);
        
        if (await this.game.makeMove(card, position)) {
            this.animateCardPlacement(cardElement, slot);
        }
    }

    animateCardPlacement(cardElement, targetSlot) {
        const clone = cardElement.cloneNode(true);
        const rect = cardElement.getBoundingClientRect();
        const targetRect = targetSlot.getBoundingClientRect();
        
        clone.style.position = 'fixed';
        clone.style.top = `${rect.top}px`;
        clone.style.left = `${rect.left}px`;
        clone.style.width = `${rect.width}px`;
        clone.style.height = `${rect.height}px`;
        clone.style.transition = 'all 0.3s ease';
        
        document.body.appendChild(clone);
        
        requestAnimationFrame(() => {
            clone.style.top = `${targetRect.top}px`;
            clone.style.left = `${targetRect.left}px`;
        });
        
        setTimeout(() => {
            clone.remove();
            targetSlot.appendChild(this.createCardElement(JSON.parse(cardElement.dataset.card)));
            targetSlot.classList.add('occupied');
            cardElement.remove();
        }, 300);
    }

    showAIThinking() {
        const thinkingOverlay = document.createElement('div');
        thinkingOverlay.className = 'thinking-overlay';
        thinkingOverlay.innerHTML = `
            <div class="thinking-content">
                <div class="spinner"></div>
                <p>AI thinking...</p>
            </div>
        `;
        document.body.appendChild(thinkingOverlay);
    }

    hideAIThinking() {
        const overlay = document.querySelector('.thinking-overlay');
        if (overlay) {
            overlay.remove();
        }
    }

    showGameOver(result) {
        const modal = document.getElementById('gameEndModal');
        const resultsDiv = document.getElementById('gameResults');
        
        resultsDiv.innerHTML = `
            <div class="game-results">
                <h3>${result.winner === 0 ? 'You Won!' : 'AI Won!'}</h3>
                <div class="results-details">
                    <p>Your Score: ${result.playerScore}</p>
                    <p>AI Score: ${result.aiScore}</p>
                    <p>Royalties: ${result.royalties}</p>
                    ${result.fantasyAchieved ? '<p class="fantasy-achieved">Fantasy Achieved!</p>' : ''}
                </div>
            </div>
        `;
        
        modal.style.display = 'flex';
    }

    showError(message) {
        const errorToast = document.createElement('div');
        errorToast.className = 'error-toast';
        errorToast.textContent = message;
        
        document.body.appendChild(errorToast);
        
        setTimeout(() => {
            errorToast.classList.add('fade-out');
            setTimeout(() => errorToast.remove(), 300);
        }, 3000);
    }

    updatePlayerCount(count) {
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.classList.toggle('active', parseInt(btn.dataset.players) === count);
        });
        this.updateAgentSelectors(this.game.state.availableAgents || [], count);
    }

    updateAgentSelectors(agents, playerCount) {
        const container = document.getElementById('aiSelectors');
        container.innerHTML = '';
        
        for (let i = 1; i < playerCount; i++) {
            const selector = document.createElement('div');
            selector.className = 'ai-selector';
            selector.innerHTML = `
                <h4>AI Player ${i}</h4>
                <select class="agent-select">
                    ${agents.map(agent => `
                        <option value="${agent.id}">${agent.name}</option>
                    `).join('')}
                </select>
                <div class="agent-options">
                    <label>
                        <input type="checkbox" id="useLatestModel" checked>
                        Use latest model
                    </label>
                </div>
            `;
            container.appendChild(selector);
        }
    }
}
