class GameUI {
    constructor(game) {
        this.game = game;
        this.selectedCard = null;
        this.draggedCard = null;
        this.isMobile = window.innerWidth <= 768;
        this.initializeElements();
        this.setupDragAndDrop();
        this.setupResponsiveUI();
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
            trainingControls: document.getElementById('trainingControls'),
            sidePanel: document.getElementById('sidePanel'),
            menuButton: document.getElementById('menuButton'),
            mobileMenu: document.getElementById('mobileMenu')
        };

        // Инициализация мобильного меню
        if (this.isMobile) {
            this.initializeMobileMenu();
        }
    }

    initializeMobileMenu() {
        const mobileMenuHTML = `
            <div id="mobileMenu" class="mobile-menu">
                <div class="mobile-menu-header">
                    <h3>Menu</h3>
                    <button class="close-menu">×</button>
                </div>
                <div class="mobile-menu-content">
                    <button class="menu-item" data-action="newGame">New Game</button>
                    <button class="menu-item" data-action="statistics">Statistics</button>
                    <button class="menu-item" data-action="settings">Settings</button>
                    <button class="menu-item" data-action="returnToMenu">Return to Menu</button>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', mobileMenuHTML);

        // Обработчики для мобильного меню
        document.querySelector('.close-menu').addEventListener('click', () => {
            this.closeMobileMenu();
        });

        document.querySelectorAll('.menu-item').forEach(item => {
            item.addEventListener('click', (e) => {
                this.handleMobileMenuAction(e.target.dataset.action);
            });
        });
    }

    setupDragAndDrop() {
        if (this.isMobile) {
            this.setupTouchDragAndDrop();
        } else {
            this.setupMouseDragAndDrop();
        }
    }

    setupMouseDragAndDrop() {
        document.addEventListener('dragstart', (e) => {
            if (e.target.classList.contains('card')) {
                this.draggedCard = e.target;
                e.target.classList.add('dragging');
                e.dataTransfer.setData('text/plain', ''); // Для Firefox
            }
        });

        document.addEventListener('dragend', (e) => {
            if (e.target.classList.contains('card')) {
                e.target.classList.remove('dragging');
                this.draggedCard = null;
            }
        });

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

setupTouchDragAndDrop() {
        let touchCard = null;
        let initialX = 0;
        let initialY = 0;

        document.addEventListener('touchstart', (e) => {
            if (e.target.classList.contains('card')) {
                touchCard = e.target;
                const touch = e.touches[0];
                initialX = touch.clientX - touchCard.offsetLeft;
                initialY = touch.clientY - touchCard.offsetTop;
                touchCard.classList.add('dragging');
            }
        }, { passive: false });

        document.addEventListener('touchmove', (e) => {
            if (touchCard) {
                e.preventDefault();
                const touch = e.touches[0];
                touchCard.style.position = 'fixed';
                touchCard.style.left = `${touch.clientX - initialX}px`;
                touchCard.style.top = `${touch.clientY - initialY}px`;
                
                // Проверяем слоты под пальцем
                const slot = this.getTouchTargetSlot(touch.clientX, touch.clientY);
                if (slot && this.isValidDropTarget(slot)) {
                    slot.classList.add('droppable');
                }
            }
        }, { passive: false });

        document.addEventListener('touchend', (e) => {
            if (touchCard) {
                const touch = e.changedTouches[0];
                const slot = this.getTouchTargetSlot(touch.clientX, touch.clientY);
                
                if (slot && this.isValidDropTarget(slot)) {
                    this.handleCardDrop(touchCard, slot);
                } else {
                    this.resetCardPosition(touchCard);
                }
                
                touchCard.classList.remove('dragging');
                touchCard = null;
            }
        });
    }

    getTouchTargetSlot(x, y) {
        const elements = document.elementsFromPoint(x, y);
        return elements.find(el => el.classList.contains('card-slot'));
    }

    resetCardPosition(card) {
        card.style.position = '';
        card.style.left = '';
        card.style.top = '';
    }

    switchToGame() {
        this.elements.mainMenu.style.display = 'none';
        this.elements.gameContainer.style.display = 'grid';
        this.initializeGameBoard();
        
        if (this.isMobile) {
            this.setupMobileLayout();
        }
    }

    setupMobileLayout() {
        document.body.classList.add('mobile');
        this.elements.sidePanel.classList.add('mobile-panel');
        this.updateMobileOrientation();
        
        // Слушаем изменение ориентации
        window.addEventListener('orientationchange', () => {
            this.updateMobileOrientation();
        });
    }

    updateMobileOrientation() {
        const isLandscape = window.innerWidth > window.innerHeight;
        document.body.classList.toggle('landscape', isLandscape);
        this.adjustBoardLayout(isLandscape);
    }

    adjustBoardLayout(isLandscape) {
        const container = this.elements.playersContainer;
        const playerCount = this.game.state.players;

        if (isLandscape) {
            container.classList.add('landscape-layout');
            // Горизонтальное расположение
            if (playerCount === 2) {
                container.style.gridTemplateAreas = '"opponent player"';
            } else if (playerCount === 3) {
                container.style.gridTemplateAreas = '"opponent1 opponent2 player"';
            }
        } else {
            container.classList.remove('landscape-layout');
            // Вертикальное расположение
            if (playerCount === 2) {
                container.style.gridTemplateAreas = '"opponent" "player"';
            } else if (playerCount === 3) {
                container.style.gridTemplateAreas = '"opponent1" "opponent2" "player"';
            }
        }
    }

    initializeGameBoard() {
        this.elements.playersContainer.innerHTML = '';
        const template = document.getElementById('playerBoardTemplate');
        const playerCount = this.game.state.players;

        for (let i = 0; i < playerCount; i++) {
            const board = template.content.cloneNode(true);
            const boardElement = board.querySelector('.player-board');
            boardElement.dataset.player = i;

            // Настраиваем информацию об игроке
            const playerInfo = boardElement.querySelector('.player-info');
            const playerName = i === 0 ? 'You' : this.getAgentName(i);
            playerInfo.querySelector('.player-name').textContent = playerName;

            this.elements.playersContainer.appendChild(board);
        }

        this.setupBoardLayout();
    }

    getAgentName(playerIndex) {
        const agent = this.game.state.agents[playerIndex - 1];
        return agent ? agent.name.replace('Agent', '') : `AI ${playerIndex}`;
    }

setupBoardLayout() {
        const container = this.elements.playersContainer;
        const playerCount = this.game.state.players;
        container.className = `players-container players-${playerCount}`;

        if (this.isMobile) {
            this.adjustBoardLayout(window.innerWidth > window.innerHeight);
        } else {
            // Десктопное расположение
            if (playerCount === 1) {
                container.style.gridTemplateAreas = '"player"';
            } else if (playerCount === 2) {
                container.style.gridTemplateAreas = '"opponent" "player"';
            } else {
                container.style.gridTemplateAreas = '"opponent1 opponent2" "player player"';
            }
        }
    }

    updateGameState(state) {
        // Обновляем статус игры
        this.elements.gameStatus.textContent = 
            state.currentPlayer === 0 ? 'Your turn' : `${this.getAgentName(state.currentPlayer)}'s turn`;

        // Обновляем таймер
        if (state.currentPlayer === 0) {
            this.startTimer();
        } else {
            this.stopTimer();
        }

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
        this.updateFantasyStatus(state.fantasyStatus);

        // Обновляем боковую панель
        this.updateSidePanel(state);
    }

    startTimer() {
        this.stopTimer();
        let seconds = 0;
        this.timer = setInterval(() => {
            seconds++;
            this.elements.gameTimer.textContent = this.formatTime(seconds);
        }, 1000);
    }

    stopTimer() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    }

    formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    toggleMobileMenu() {
        const menu = document.getElementById('mobileMenu');
        menu.classList.toggle('active');
    }

    handleMobileMenuAction(action) {
        switch(action) {
            case 'newGame':
                this.game.startGame();
                break;
            case 'statistics':
                this.game.showFullStatistics();
                break;
            case 'settings':
                this.showSettingsModal();
                break;
            case 'returnToMenu':
                this.game.showConfirmDialog(
                    "Return to Menu",
                    "Are you sure you want to return to the main menu?",
                    () => this.game.returnToMenu()
                );
                break;
        }
        this.closeMobileMenu();
    }

    showConfirmDialog({ title, message, onConfirm, onCancel }) {
        const dialog = document.createElement('div');
        dialog.className = 'confirm-dialog';
        dialog.innerHTML = `
            <div class="confirm-dialog-content">
                <h3>${title}</h3>
                <p>${message}</p>
                <div class="confirm-dialog-buttons">
                    <button class="confirm-yes">Yes</button>
                    <button class="confirm-no">No</button>
                </div>
            </div>
        `;

        dialog.querySelector('.confirm-yes').addEventListener('click', onConfirm);
        dialog.querySelector('.confirm-no').addEventListener('click', onCancel || this.hideConfirmDialog);

        document.body.appendChild(dialog);
    }

    hideConfirmDialog() {
        const dialog = document.querySelector('.confirm-dialog');
        if (dialog) {
            dialog.remove();
        }
    }

    showError(message) {
        const toast = document.createElement('div');
        toast.className = 'error-toast';
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    showAIThinking(player) {
        const overlay = document.createElement('div');
        overlay.className = 'thinking-overlay';
        overlay.innerHTML = `
            <div class="thinking-content">
                <div class="spinner"></div>
                <p>${this.getAgentName(player)} thinking...</p>
            </div>
        `;
        document.body.appendChild(overlay);
    }

    hideAIThinking() {
        const overlay = document.querySelector('.thinking-overlay');
        if (overlay) {
            overlay.remove();
        }
    }

    showGameOver(result) {
        const modal = document.createElement('div');
        modal.className = 'game-over-modal';
        modal.innerHTML = `
            <div class="game-over-content">
                <h2>Game Over</h2>
                <div class="game-results">
                    <h3>${result.winner === 0 ? 'You Won!' : `${this.getAgentName(result.winner)} Won!`}</h3>
                    <div class="results-details">
                        <p>Your Score: ${result.playerScore}</p>
                        ${result.aiScores.map((score, i) => 
                            `<p>${this.getAgentName(i + 1)} Score: ${score}</p>`
                        ).join('')}
                        <p>Royalties: ${result.royalties}</p>
                        ${result.fantasyAchieved ? '<p class="fantasy-achieved">Fantasy Achieved!</p>' : ''}
                    </div>
                </div>
                <div class="game-over-buttons">
                    <button class="new-game">New Game</button>
                    <button class="return-menu">Return to Menu</button>
                </div>
            </div>
        `;

        modal.querySelector('.new-game').addEventListener('click', () => {
            modal.remove();
            this.game.startGame();
        });

        modal.querySelector('.return-menu').addEventListener('click', () => {
            modal.remove();
            this.game.returnToMenu();
        });

        document.body.appendChild(modal);
    }
}

// Экспорт класса
export default GameUI;
