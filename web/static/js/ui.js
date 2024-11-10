// web/static/js/ui.js

class GameUI {
    constructor(game) {
        this.game = game;
        this.selectedCard = null;
        this.draggedCard = null;
        this.isMobile = 'ontouchstart' in window || window.innerWidth <= 768;
        this.animationEnabled = true;
        this.touchStartX = null;
        this.touchStartY = null;
        
        // Инициализация после загрузки DOM
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    init() {
        try {
            this.initializeElements();
            this.setupEventListeners();
            this.loadSettings();
            this.setupResponsiveUI();
            this.setupDragAndDrop();
            
            if (this.isMobile) {
                this.initializeMobileUI();
            }
        } catch (error) {
            console.error('UI initialization failed:', error);
            this.showError('Failed to initialize game interface');
        }
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
            themeToggle: document.getElementById('themeToggle'),
            startGame: document.getElementById('startGame'),
            aiThinkTime: document.getElementById('aiThinkTime'),
            fantasyType: document.getElementById('fantasyType'),
            soundToggle: document.getElementById('soundToggle'),
            animationControl: document.getElementById('animationControl')
        };

        // Проверка обязательных элементов
        const requiredElements = ['mainMenu', 'gameContainer', 'playersContainer'];
        const missingElements = requiredElements.filter(id => !this.elements[id]);
        
        if (missingElements.length > 0) {
            throw new Error(`Missing required elements: ${missingElements.join(', ')}`);
        }
    }

    setupEventListeners() {
        // Основные элементы управления
        this.elements.menuButton?.addEventListener('click', () => this.toggleMenu());
        this.elements.themeToggle?.addEventListener('click', () => this.toggleTheme());
        this.elements.startGame?.addEventListener('click', () => this.game.startGame());
        
        // Настройки
        this.elements.aiThinkTime?.addEventListener('input', (e) => {
            const value = parseInt(e.target.value);
            if (!isNaN(value)) {
                this.game.setAIThinkTime(value);
                document.getElementById('thinkTimeValue').textContent = `${value}s`;
            }
        });

        this.elements.fantasyType?.addEventListener('change', (e) => {
            this.game.setFantasyMode(e.target.value);
        });

        this.elements.soundToggle?.addEventListener('change', (e) => {
            this.toggleSound(e.target.checked);
        });

        this.elements.animationControl?.addEventListener('change', (e) => {
            this.setAnimationState(e.target.value);
        });

        // Обработка изменения размера окна
        window.addEventListener('resize', this.debounce(() => {
            this.updateResponsiveLayout();
        }, 250));

        // Обработка клавиатуры
        document.addEventListener('keydown', (e) => this.handleKeyboardInput(e));
    }

            // Утилиты
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Настройка мобильного интерфейса
    initializeMobileUI() {
        this.setupTouchEvents();
        this.createMobileMenu();
        this.adjustLayoutForMobile();
    }

    setupTouchEvents() {
        document.addEventListener('touchstart', (e) => {
            this.touchStartX = e.touches[0].clientX;
            this.touchStartY = e.touches[0].clientY;
        }, { passive: true });

        document.addEventListener('touchmove', (e) => {
            if (!this.touchStartX || !this.touchStartY) return;

            const xDiff = this.touchStartX - e.touches[0].clientX;
            const yDiff = this.touchStartY - e.touches[0].clientY;

            if (Math.abs(xDiff) > Math.abs(yDiff)) {
                if (xDiff > 50) { // Свайп влево
                    this.openSidePanel();
                } else if (xDiff < -50) { // Свайп вправо
                    this.closeSidePanel();
                }
            }
        }, { passive: true });

        document.addEventListener('touchend', () => {
            this.touchStartX = null;
            this.touchStartY = null;
        }, { passive: true });
    }

    createMobileMenu() {
        if (document.getElementById('mobileMenu')) return;

        const menuHTML = `
            <div id="mobileMenu" class="mobile-menu">
                <div class="mobile-menu-header">
                    <h3>Меню</h3>
                    <button class="close-menu" aria-label="Закрыть меню">×</button>
                </div>
                <div class="mobile-menu-content">
                    <button class="menu-item" data-action="newGame">
                        <i class="fas fa-play"></i> Новая игра
                    </button>
                    <button class="menu-item" data-action="statistics">
                        <i class="fas fa-chart-bar"></i> Статистика
                    </button>
                    <button class="menu-item" data-action="settings">
                        <i class="fas fa-cog"></i> Настройки
                    </button>
                    <button class="menu-item" data-action="tutorial">
                        <i class="fas fa-question-circle"></i> Обучение
                    </button>
                    <button class="menu-item" data-action="returnToMenu">
                        <i class="fas fa-home"></i> В главное меню
                    </button>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', menuHTML);
        this.setupMobileMenuListeners();
    }

    setupMobileMenuListeners() {
        const menu = document.getElementById('mobileMenu');
        if (!menu) return;

        menu.querySelector('.close-menu').addEventListener('click', () => {
            this.closeMobileMenu();
        });

        menu.querySelectorAll('.menu-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const action = e.target.closest('.menu-item').dataset.action;
                this.handleMobileMenuAction(action);
            });
        });
    }

    handleMobileMenuAction(action) {
        this.closeMobileMenu();
        
        switch(action) {
            case 'newGame':
                this.game.startGame();
                break;
            case 'statistics':
                this.showStatistics();
                break;
            case 'settings':
                this.showSettings();
                break;
            case 'tutorial':
                this.showTutorial();
                break;
            case 'returnToMenu':
                this.confirmReturnToMenu();
                break;
        }
    }

    adjustLayoutForMobile() {
        const isLandscape = window.innerWidth > window.innerHeight;
        document.body.classList.toggle('landscape', isLandscape);
        
        if (this.elements.playersContainer) {
            this.elements.playersContainer.style.gridTemplateColumns = 
                isLandscape ? 'repeat(auto-fit, minmax(250px, 1fr))' : '1fr';
        }

        this.adjustCardSizes(isLandscape);
        this.updateControlsLayout(isLandscape);
    }

    adjustCardSizes(isLandscape) {
        const cardWidth = isLandscape ? '50px' : '60px';
        const cardHeight = isLandscape ? '70px' : '84px';
        
        document.documentElement.style.setProperty('--card-width', cardWidth);
        document.documentElement.style.setProperty('--card-height', cardHeight);
    }

// Управление интерфейсом
    setupDragAndDrop() {
        if (this.isMobile) {
            this.setupTouchDragAndDrop();
        } else {
            this.setupMouseDragAndDrop();
        }
    }

    setupMouseDragAndDrop() {
        document.addEventListener('dragstart', (e) => {
            if (!e.target.classList.contains('card')) return;
            
            this.draggedCard = e.target;
            e.target.classList.add('dragging');
            e.dataTransfer.setData('text/plain', '');
            this.highlightValidDropZones(this.draggedCard);
        });

        document.addEventListener('dragend', (e) => {
            if (!e.target.classList.contains('card')) return;
            
            e.target.classList.remove('dragging');
            this.clearHighlightedDropZones();
            this.draggedCard = null;
        });

        this.setupDropZones();
    }

    setupDropZones() {
        document.querySelectorAll('.card-slot').forEach(slot => {
            slot.addEventListener('dragover', (e) => {
                if (!this.isValidDropTarget(slot)) return;
                
                e.preventDefault();
                slot.classList.add('droppable');
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
        let moved = false;

        document.addEventListener('touchstart', (e) => {
            if (!e.target.classList.contains('card')) return;
            
            touchCard = e.target;
            moved = false;
            const touch = e.touches[0];
            initialX = touch.clientX - touchCard.offsetLeft;
            initialY = touch.clientY - touchCard.offsetTop;
            touchCard.classList.add('dragging');
        }, { passive: false });

        document.addEventListener('touchmove', (e) => {
            if (!touchCard) return;
            
            e.preventDefault();
            moved = true;
            const touch = e.touches[0];
            
            touchCard.style.position = 'fixed';
            touchCard.style.left = `${touch.clientX - initialX}px`;
            touchCard.style.top = `${touch.clientY - initialY}px`;
            
            const dropTarget = this.findDropTargetAtPoint(touch.clientX, touch.clientY);
            this.updateDropZoneHighlight(dropTarget);
        }, { passive: false });

        document.addEventListener('touchend', (e) => {
            if (!touchCard) return;
            
            const touch = e.changedTouches[0];
            const dropTarget = this.findDropTargetAtPoint(touch.clientX, touch.clientY);
            
            if (!moved) {
                this.handleCardTap(touchCard);
            } else if (dropTarget && this.isValidDropTarget(dropTarget)) {
                this.handleCardDrop(touchCard, dropTarget);
            } else {
                this.resetCardPosition(touchCard);
            }
            
            touchCard.classList.remove('dragging');
            this.clearHighlightedDropZones();
            touchCard = null;
        });
    }

    findDropTargetAtPoint(x, y) {
        const elements = document.elementsFromPoint(x, y);
        return elements.find(el => el.classList.contains('card-slot'));
    }

    updateDropZoneHighlight(target) {
        this.clearHighlightedDropZones();
        if (target && this.isValidDropTarget(target)) {
            target.classList.add('droppable');
        }
    }

    handleCardTap(card) {
        if (this.selectedCard === card) {
            this.deselectCard();
        } else {
            this.selectCard(card);
        }
    }

    selectCard(card) {
        if (this.selectedCard) {
            this.selectedCard.classList.remove('selected');
        }
        this.selectedCard = card;
        card.classList.add('selected');
        this.highlightValidDropZones(card);
    }

    deselectCard() {
        if (this.selectedCard) {
            this.selectedCard.classList.remove('selected');
            this.selectedCard = null;
            this.clearHighlightedDropZones();
        }
    }

    highlightValidDropZones(card) {
        document.querySelectorAll('.card-slot').forEach(slot => {
            if (this.isValidDropTarget(slot)) {
                slot.classList.add('valid-target');
            }
        });
    }

    clearHighlightedDropZones() {
        document.querySelectorAll('.card-slot').forEach(slot => {
            slot.classList.remove('droppable', 'valid-target');
        });
    }

// Управление состоянием игры и UI
    handleCardDrop(card, slot) {
        if (!this.isValidDropTarget(slot)) return;

        const cardData = this.getCardData(card);
        const position = parseInt(slot.dataset.position);

        if (this.animationEnabled) {
            this.animateCardPlacement(card, slot, () => {
                this.game.makeMove(cardData, position);
            });
        } else {
            this.game.makeMove(cardData, position);
        }
    }

    animateCardPlacement(card, slot, callback) {
        if (!this.animationEnabled) {
            callback();
            return;
        }

        const cardRect = card.getBoundingClientRect();
        const slotRect = slot.getBoundingClientRect();
        const deltaX = slotRect.left - cardRect.left;
        const deltaY = slotRect.top - cardRect.top;

        card.style.transition = 'transform 0.3s ease-out';
        card.style.transform = `translate(${deltaX}px, ${deltaY}px)`;

        const handleTransitionEnd = () => {
            card.style.transition = '';
            card.style.transform = '';
            card.removeEventListener('transitionend', handleTransitionEnd);
            callback();
        };

        card.addEventListener('transitionend', handleTransitionEnd, { once: true });
    }

    updateGameState(state) {
        try {
            this.updateGameStatus(state);
            this.updatePlayerHand(state.playerCards);
            this.updateBoards(state);
            this.updateRemovedCards(state.removedCards);
            this.updateMoveHistory(state.lastMove);
            this.updateFantasyStatus(state.fantasyStatus);
            this.updateStatistics(state);
            this.updateSidePanel(state);
        } catch (error) {
            console.error('Failed to update game state:', error);
            this.showError('Failed to update game state');
        }
    }

    updateGameStatus(state) {
        if (!this.elements.gameStatus) return;

        const statusText = state.currentPlayer === 0 
            ? 'Ваш ход' 
            : `Ход ${this.getPlayerName(state.currentPlayer)}`;
        
        this.elements.gameStatus.textContent = statusText;

        if (state.currentPlayer === 0) {
            this.startTimer();
        } else {
            this.stopTimer();
        }
    }

    updatePlayerHand(cards) {
        if (!this.elements.playerHand) return;

        this.elements.playerHand.innerHTML = '';
        cards.forEach(card => {
            const cardElement = this.createCardElement(card);
            this.elements.playerHand.appendChild(cardElement);
        });
    }

    updateBoards(state) {
        if (!this.elements.playersContainer) return;

        // Очищаем контейнер
        this.elements.playersContainer.innerHTML = '';
        
        // Создаем доски для каждого игрока
        state.players.forEach((player, index) => {
            const board = this.createPlayerBoard(player, index);
            this.elements.playersContainer.appendChild(board);
        });

        // Обновляем layout
        this.elements.playersContainer.setAttribute('data-players', state.players.length);
    }

    createPlayerBoard(player, index) {
        const template = document.getElementById('playerBoardTemplate');
        if (!template) {
            console.error('Player board template not found');
            return document.createElement('div');
        }

        const board = template.content.cloneNode(true).firstElementChild;
        
        // Заполняем информацию об игроке
        board.querySelector('.player-name').textContent = this.getPlayerName(index);
        board.querySelector('.player-score').textContent = player.score;
        
        // Заполняем карты на доске
        this.fillPlayerBoard(board, player.cards);
        
        return board;
    }

    fillPlayerBoard(board, cards) {
        cards.forEach((card, position) => {
            if (!card) return;
            
            const slot = board.querySelector(`[data-position="${position}"]`);
            if (!slot) return;

            const cardElement = this.createCardElement(card);
            slot.appendChild(cardElement);
            slot.classList.add('occupied');
        });
    }

    createCardElement(card) {
        const element = document.createElement('div');
        element.className = `card ${card.color}`;
        element.draggable = true;
        element.dataset.rank = card.rank;
        element.dataset.suit = card.suit;

        element.innerHTML = `
            <span class="card-rank">${card.rank}</span>
            <span class="card-suit">${this.getSuitSymbol(card.suit)}</span>
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

// Обновление UI элементов и обработка взаимодействий
    updateRemovedCards(cards) {
        if (!this.elements.removedCards) return;

        this.elements.removedCards.innerHTML = '';
        cards.forEach(card => {
            const cardElement = this.createCardElement(card);
            cardElement.draggable = false; // Убираем возможность перетаскивания
            this.elements.removedCards.appendChild(cardElement);
        });
    }

    updateMoveHistory(move) {
        if (!this.elements.moveHistory || !move) return;

        const moveElement = document.createElement('div');
        moveElement.className = 'move-item';
        moveElement.innerHTML = `
            <span class="move-player">${this.getPlayerName(move.player)}</span>
            <span class="move-card">${move.card.rank}${this.getSuitSymbol(move.card.suit)}</span>
            <span class="move-position">Position: ${move.position}</span>
        `;

        this.elements.moveHistory.insertBefore(moveElement, this.elements.moveHistory.firstChild);
        this.trimMoveHistory();
    }

    trimMoveHistory(maxMoves = 10) {
        if (!this.elements.moveHistory) return;

        while (this.elements.moveHistory.children.length > maxMoves) {
            this.elements.moveHistory.removeChild(this.elements.moveHistory.lastChild);
        }
    }

    updateFantasyStatus(status) {
        if (!this.elements.fantasyStatus) return;

        const statusText = status.active ? 
            `Фантазия активна (${status.cardsCount} карт)` : 
            'Фантазия неактивна';

        this.elements.fantasyStatus.textContent = statusText;
        this.elements.fantasyStatus.classList.toggle('active', status.active);

        if (status.progressiveBonus) {
            this.elements.fantasyStatus.setAttribute(
                'data-bonus',
                `Прогрессивный бонус: ${status.progressiveBonus}`
            );
        }
    }

    updateStatistics(state) {
        const stats = {
            foulsRate: state.fouls / state.totalMoves * 100 || 0,
            scoopsRate: state.scoops / state.totalMoves * 100 || 0,
            winRate: state.wins / state.gamesPlayed * 100 || 0
        };

        Object.entries(stats).forEach(([key, value]) => {
            const element = document.getElementById(key);
            if (element) {
                element.textContent = `${value.toFixed(1)}%`;
                this.animateStatUpdate(element);
            }
        });
    }

    animateStatUpdate(element) {
        element.classList.add('updated');
        setTimeout(() => element.classList.remove('updated'), 300);
    }

    showAIThinking(player, thinkTime = 30) {
        const overlay = document.createElement('div');
        overlay.className = 'thinking-overlay';
        
        overlay.innerHTML = `
            <div class="thinking-content">
                <div class="spinner"></div>
                <p>${this.getPlayerName(player)} думает...</p>
                ${this.animationEnabled ? `
                    <div class="progress-bar">
                        <div class="progress" style="animation-duration: ${thinkTime}s"></div>
                    </div>
                ` : ''}
            </div>
        `;
        
        document.body.appendChild(overlay);
    }

    hideAIThinking() {
        const overlay = document.querySelector('.thinking-overlay');
        if (!overlay) return;

        overlay.classList.add('fade-out');
        setTimeout(() => overlay.remove(), 300);
    }

    showGameOver(result) {
        const modal = document.createElement('div');
        modal.className = 'game-over-modal';
        
        modal.innerHTML = `
            <div class="game-over-content">
                <h2>Игра окончена</h2>
                <div class="game-results">
                    <h3>${result.winner === 0 ? 'Вы победили!' : `${this.getPlayerName(result.winner)} победил!`}</h3>
                    <div class="results-details">
                        <p>Ваш счёт: ${result.playerScore}</p>
                        ${result.aiScores.map((score, i) => 
                            `<p>${this.getPlayerName(i + 1)} счёт: ${score}</p>`
                        ).join('')}
                        <p>Роялти: ${result.royalties}</p>
                        <p>Фолы: ${((result.fouls / result.totalMoves) * 100).toFixed(1)}%</p>
                        <p>Скупы: ${((result.scoops / result.totalMoves) * 100).toFixed(1)}%</p>
                        ${result.fantasyAchieved ? '<p class="fantasy-achieved">Фантазия достигнута!</p>' : ''}
                    </div>
                </div>
                <div class="game-over-buttons">
                    <button class="new-game">Новая игра</button>
                    <button class="return-menu">Вернуться в меню</button>
                </div>
            </div>
        `;

        this.setupGameOverListeners(modal);
        document.body.appendChild(modal);
    }

// Вспомогательные методы и обработчики
    setupGameOverListeners(modal) {
        modal.querySelector('.new-game').addEventListener('click', () => {
            modal.remove();
            this.game.startGame();
        });

        modal.querySelector('.return-menu').addEventListener('click', () => {
            modal.remove();
            this.game.returnToMenu();
        });
    }

    showError(message, duration = 3000) {
        const toast = document.createElement('div');
        toast.className = 'error-toast';
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        // Анимация появления
        requestAnimationFrame(() => {
            toast.classList.add('show');
        });
        
        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    showMessage(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        requestAnimationFrame(() => toast.classList.add('show'));
        
        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    toggleTheme() {
        const currentTheme = document.body.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        
        document.body.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        // Обновляем иконку
        const themeIcon = this.elements.themeToggle?.querySelector('i');
        if (themeIcon) {
            themeIcon.className = `fas fa-${newTheme === 'light' ? 'sun' : 'moon'}`;
        }
    }

    toggleSound(enabled) {
        document.body.classList.toggle('sound-enabled', enabled);
        localStorage.setItem('soundEnabled', enabled);
    }

    setAnimationState(value) {
        this.animationEnabled = value !== 'off';
        document.body.classList.toggle('animations-disabled', !this.animationEnabled);
        localStorage.setItem('animationState', value);
    }

    loadSettings() {
        // Загрузка темы
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.body.setAttribute('data-theme', savedTheme);

        // Загрузка настроек звука
        const soundEnabled = localStorage.getItem('soundEnabled') !== 'false';
        this.toggleSound(soundEnabled);

        // Загрузка настроек анимации
        const animationState = localStorage.getItem('animationState') || 'normal';
        this.setAnimationState(animationState);

        // Применяем настройки к элементам управления
        if (this.elements.animationControl) {
            this.elements.animationControl.value = animationState;
        }
        if (this.elements.soundToggle) {
            this.elements.soundToggle.checked = soundEnabled;
        }
    }

    handleKeyboardInput(e) {
        // Отменяем обработку, если открыто модальное окно
        if (document.querySelector('.modal.active')) return;

        if (e.ctrlKey || e.metaKey) {
            switch(e.key.toLowerCase()) {
                case 'z':
                    e.preventDefault();
                    this.game.undoLastMove();
                    break;
                case 's':
                    e.preventDefault();
                    this.game.saveGame();
                    break;
                case 'f':
                    e.preventDefault();
                    this.toggleFullscreen();
                    break;
            }
        } else if (e.key === 'Escape') {
            this.handleEscapeKey();
        }
    }

    handleEscapeKey() {
        // Закрываем модальные окна в порядке приоритета
        const modalElements = [
            '.game-over-modal',
            '.settings-modal',
            '.mobile-menu.active',
            '.side-panel.active'
        ];

        for (const selector of modalElements) {
            const element = document.querySelector(selector);
            if (element) {
                if (selector.includes('mobile-menu')) {
                    this.closeMobileMenu();
                } else if (selector.includes('side-panel')) {
                    this.closeSidePanel();
                } else {
                    element.remove();
                }
                return;
            }
        }
    }

    toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch(err => {
                this.showError('Error attempting to enable fullscreen');
            });
        } else {
            document.exitFullscreen();
        }
    }

    getPlayerName(player) {
        return player === 0 ? 'Вы' : 
            this.game.state.agents[player - 1]?.name.replace('Agent', 'AI ') || 
            `Игрок ${player}`;
    }

    isValidDropTarget(slot) {
        if (!slot || !this.draggedCard || slot.classList.contains('occupied')) {
            return false;
        }

        const card = this.getCardData(this.draggedCard);
        const position = parseInt(slot.dataset.position);
        
        return this.game.isValidMove(card, position);
    }

    getCardData(cardElement) {
        return {
            rank: cardElement.dataset.rank,
            suit: cardElement.dataset.suit,
            color: cardElement.classList.contains('red') ? 'red' : 'black'
        };
    }
}

// Экспортируем класс
export default GameUI;
