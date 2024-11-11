class GameUI {
    constructor(game) {
        this.game = game;
        this.selectedCard = null;
        this.draggedCard = null;
        this.isMobile = 'ontouchstart' in window || window.innerWidth <= 768;
        this.animationEnabled = true;
        this.touchStartX = null;
        this.touchStartY = null;
        this.eventListeners = new Map();
        
        // Инициализация после загрузки DOM
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    async init() {
        try {
            await this.initializeElements();
            this.setupEventListeners();
            this.loadSettings();
            this.setupResponsiveUI();
            this.setupDragAndDrop();
            
            if (this.isMobile) {
                this.initializeMobileUI();
            }

            // Инициализация анимаций
            this.setupAnimations();
            
            // Инициализация доступности
            this.setupAccessibility();
        } catch (error) {
            console.error('UI initialization failed:', error);
            this.showError('Failed to initialize game interface');
        }
    }

    async initializeElements() {
        // Создаем промис для каждого критического элемента
        const elementPromises = [
            this.waitForElement('mainMenu'),
            this.waitForElement('gameContainer'),
            this.waitForElement('playersContainer')
        ];

        try {
            const [mainMenu, gameContainer, playersContainer] = await Promise.all(elementPromises);
            
            this.elements = {
                mainMenu,
                gameContainer,
                playersContainer,
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

            // Проверяем наличие всех необходимых элементов
            this.validateElements();
        } catch (error) {
            throw new Error(`Failed to initialize UI elements: ${error.message}`);
        }
    }

    waitForElement(id) {
        return new Promise((resolve, reject) => {
            const element = document.getElementById(id);
            if (element) {
                resolve(element);
            } else {
                const observer = new MutationObserver((mutations, obs) => {
                    const element = document.getElementById(id);
                    if (element) {
                        obs.disconnect();
                        resolve(element);
                    }
                });

                observer.observe(document.body, {
                    childList: true,
                    subtree: true
                });

                // Таймаут на случай, если элемент не появится
                setTimeout(() => {
                    observer.disconnect();
                    reject(new Error(`Element ${id} not found`));
                }, 5000);
            }
        });
    }

    validateElements() {
        const requiredElements = ['mainMenu', 'gameContainer', 'playersContainer'];
        const missingElements = requiredElements.filter(id => !this.elements[id]);
        
        if (missingElements.length > 0) {
            throw new Error(`Missing required elements: ${missingElements.join(', ')}`);
        }
    }

    setupEventListeners() {
        // Используем Map для хранения привязанных обработчиков
        this.addEventHandler(this.elements.menuButton, 'click', () => this.toggleMenu());
        this.addEventHandler(this.elements.themeToggle, 'click', () => this.toggleTheme());
        this.addEventHandler(this.elements.startGame, 'click', () => this.game.startGame());
        
        // Настройки
        this.setupSettingsListeners();
        
        // Обработка изменения размера окна
        this.addEventHandler(window, 'resize', 
            this.debounce(() => this.updateResponsiveLayout(), 250)
        );

        // Обработка клавиатуры
        this.addEventHandler(document, 'keydown', 
            (e) => this.handleKeyboardInput(e)
        );

        // Обработка событий перетаскивания
        this.setupDragAndDropListeners();
    }

    addEventHandler(element, event, handler) {
        if (!element) return;

        const boundHandler = handler.bind(this);
        element.addEventListener(event, boundHandler);
        
        // Сохраняем привязку для возможности удаления
        if (!this.eventListeners.has(element)) {
            this.eventListeners.set(element, new Map());
        }
        this.eventListeners.get(element).set(event, boundHandler);
    }

    removeEventHandler(element, event) {
        if (!element || !this.eventListeners.has(element)) return;

        const handlers = this.eventListeners.get(element);
        const handler = handlers.get(event);
        
        if (handler) {
            element.removeEventListener(event, handler);
            handlers.delete(event);
        }

        if (handlers.size === 0) {
            this.eventListeners.delete(element);
        }
    }

    setupSettingsListeners() {
        if (this.elements.aiThinkTime) {
            this.addEventHandler(this.elements.aiThinkTime, 'input', (e) => {
                const value = parseInt(e.target.value);
                if (!isNaN(value)) {
                    this.game.setAIThinkTime(value);
                    document.getElementById('thinkTimeValue').textContent = `${value}s`;
                }
            });
        }

        if (this.elements.fantasyType) {
            this.addEventHandler(this.elements.fantasyType, 'change', (e) => {
                this.game.setFantasyMode(e.target.value);
            });
        }

        if (this.elements.soundToggle) {
            this.addEventHandler(this.elements.soundToggle, 'change', (e) => {
                this.toggleSound(e.target.checked);
            });
        }

        if (this.elements.animationControl) {
            this.addEventHandler(this.elements.animationControl, 'change', (e) => {
                this.setAnimationState(e.target.value);
            });
        }
    }

    setupDragAndDropListeners() {
        if (this.isMobile) {
            this.setupTouchDragAndDrop();
        } else {
            this.setupMouseDragAndDrop();
        }
    }

    setupMouseDragAndDrop() {
        this.addEventHandler(document, 'dragstart', (e) => {
            if (!e.target.classList.contains('card')) return;
            
            this.draggedCard = e.target;
            e.target.classList.add('dragging');
            e.dataTransfer.setData('text/plain', '');
            this.highlightValidDropZones(this.draggedCard);
        });

        this.addEventHandler(document, 'dragend', (e) => {
            if (!e.target.classList.contains('card')) return;
            e.target.classList.remove('dragging');
            this.clearHighlightedDropZones();
            this.draggedCard = null;
        });

        // Настройка зон для дропа
        document.querySelectorAll('.card-slot').forEach(slot => {
            this.addEventHandler(slot, 'dragover', (e) => {
                if (!this.isValidDropTarget(slot)) return;
                
                e.preventDefault();
                slot.classList.add('droppable');
            });

            this.addEventHandler(slot, 'dragleave', () => {
                slot.classList.remove('droppable');
            });

            this.addEventHandler(slot, 'drop', (e) => {
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

        this.addEventHandler(document, 'touchstart', (e) => {
            if (!e.target.classList.contains('card')) return;
            
            touchCard = e.target;
            moved = false;
            const touch = e.touches[0];
            initialX = touch.clientX - touchCard.offsetLeft;
            initialY = touch.clientY - touchCard.offsetTop;
            touchCard.classList.add('dragging');
        }, { passive: false });

        this.addEventHandler(document, 'touchmove', (e) => {
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

        this.addEventHandler(document, 'touchend', (e) => {
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

    setupAnimations() {
        // Настройка CSS переменных для анимаций
        document.documentElement.style.setProperty(
            '--animation-duration', 
            this.animationEnabled ? '0.3s' : '0s'
        );

        // Наблюдатель за изменениями для анимаций
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && 
                    mutation.attributeName === 'class') {
                    this.handleAnimationClass(mutation.target);
                }
            });
        });

        // Наблюдаем за изменениями классов у карт
        document.querySelectorAll('.card').forEach(card => {
            observer.observe(card, { attributes: true });
        });
    }

    setupAccessibility() {
        // Добавляем ARIA-атрибуты
        this.elements.gameContainer.setAttribute('role', 'main');
        this.elements.playerHand.setAttribute('role', 'region');
        this.elements.playerHand.setAttribute('aria-label', 'Your cards');

        // Добавляем поддержку клавиатурной навигации
        this.setupKeyboardNavigation();

        // Добавляем живые регионы для обновления состояния
        this.elements.gameStatus.setAttribute('role', 'status');
        this.elements.gameStatus.setAttribute('aria-live', 'polite');
    }

    setupKeyboardNavigation() {
        const focusableElements = this.elements.gameContainer
            .querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
        
        const firstFocusable = focusableElements[0];
        const lastFocusable = focusableElements[focusableElements.length - 1];

        this.addEventHandler(this.elements.gameContainer, 'keydown', (e) => {
            if (e.key === 'Tab') {
                if (e.shiftKey) {
                    if (document.activeElement === firstFocusable) {
                        e.preventDefault();
                        lastFocusable.focus();
                    }
                } else {
                    if (document.activeElement === lastFocusable) {
                        e.preventDefault();
                        firstFocusable.focus();
                    }
                }
            }
        });
    }

    updateLayout() {
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

    updateControlsLayout(isLandscape) {
        if (this.elements.sidePanel) {
            this.elements.sidePanel.classList.toggle('landscape', isLandscape);
        }

        if (this.elements.trainingControls) {
            this.elements.trainingControls.classList.toggle('landscape', isLandscape);
        }
    }

    handleAnimationClass(element) {
        if (!this.animationEnabled) {
            element.style.transition = 'none';
            return;
        }

        if (element.classList.contains('card-moving')) {
            element.addEventListener('transitionend', () => {
                element.classList.remove('card-moving');
            }, { once: true });
        }
    }

    async animateMove(move) {
        if (!this.animationEnabled) {
            this.applyMove(move);
            return;
        }

        const card = this.findCard(move.card);
        const targetSlot = this.findSlot(move.position);

        if (!card || !targetSlot) {
            console.error('Animation failed: card or slot not found');
            this.applyMove(move);
            return;
        }

        await this.animateCardMovement(card, targetSlot);
        this.applyMove(move);
    }

    async animateCardMovement(card, targetSlot) {
        return new Promise(resolve => {
            const cardRect = card.getBoundingClientRect();
            const targetRect = targetSlot.getBoundingClientRect();

            const translateX = targetRect.left - cardRect.left;
            const translateY = targetRect.top - cardRect.top;

            card.style.transition = 'transform 0.3s ease-out';
            card.style.transform = `translate(${translateX}px, ${translateY}px)`;

            card.addEventListener('transitionend', () => {
                card.style.transition = '';
                card.style.transform = '';
                resolve();
            }, { once: true });
        });
    }

    applyMove(move) {
        const card = this.findCard(move.card);
        const slot = this.findSlot(move.position);

        if (card && slot) {
            slot.appendChild(card);
            slot.classList.add('occupied');
            this.updateGameState();
        }
    }

    updateGameState() {
        // Обновляем отображение статистики
        this.updateStatistics();
        
        // Обновляем историю ходов
        this.updateMoveHistory();
        
        // Обновляем состояние фантазии
        this.updateFantasyStatus();
        
        // Обновляем индикаторы прогресса
        this.updateProgressIndicators();
    }

    updateStatistics() {
        const stats = this.game.getStatistics();
        Object.entries(stats).forEach(([key, value]) => {
            const element = document.getElementById(key);
            if (element) {
                element.textContent = value;
                this.animateStatUpdate(element);
            }
        });
    }

    animateStatUpdate(element) {
        if (!this.animationEnabled) return;

        element.classList.add('updated');
        setTimeout(() => element.classList.remove('updated'), 300);
    }

    updateMoveHistory(move) {
        if (!this.elements.moveHistory || !move) return;

        const moveElement = document.createElement('div');
        moveElement.className = 'move-item';
        moveElement.innerHTML = `
            <span class="move-player">${this.getPlayerName(move.player)}</span>
            <span class="move-card">${this.formatCard(move.card)}</span>
            <span class="move-position">Position: ${move.position}</span>
        `;

        this.elements.moveHistory.insertBefore(moveElement, this.elements.moveHistory.firstChild);
        this.trimMoveHistory();
    }

    updateFantasyStatus(status) {
        if (!this.elements.fantasyStatus) return;

        const statusText = status.active ? 
            `Fantasy active (${status.cardsCount} cards)` : 
            'Fantasy inactive';

        this.elements.fantasyStatus.textContent = statusText;
        this.elements.fantasyStatus.classList.toggle('active', status.active);

        if (status.progressiveBonus) {
            this.elements.fantasyStatus.setAttribute(
                'data-bonus',
                `Progressive bonus: ${status.progressiveBonus}`
            );
        }
    }

    updateProgressIndicators() {
        const progress = this.game.getProgress();
        
        // Обновляем индикатор прогресса игры
        if (this.elements.gameProgress) {
            this.elements.gameProgress.style.width = `${progress.game}%`;
        }

        // Обновляем индикатор времени хода
        if (this.elements.turnProgress) {
            this.elements.turnProgress.style.width = `${progress.turn}%`;
        }
    }

    showError(message, duration = 3000) {
        const toast = document.createElement('div');
        toast.className = 'error-toast';
        toast.setAttribute('role', 'alert');
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        requestAnimationFrame(() => {
            toast.classList.add('show');
            
            setTimeout(() => {
                toast.classList.add('fade-out');
                setTimeout(() => toast.remove(), 300);
            }, duration);
        });
    }

    showMessage(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.setAttribute('role', 'status');
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        requestAnimationFrame(() => {
            toast.classList.add('show');
            
            setTimeout(() => {
                toast.classList.add('fade-out');
                setTimeout(() => toast.remove(), 300);
            }, duration);
        });
    }

    showGameOver(result) {
        const modal = document.createElement('div');
        modal.className = 'game-over-modal';
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-modal', 'true');
        
        modal.innerHTML = `
            <div class="game-over-content">
                <h2>Game Over</h2>
                <div class="game-results">
                    <h3>${result.winner === 0 ? 'You won!' : `${this.getPlayerName(result.winner)} won!`}</h3>
                    <div class="results-details">
                        <p>Your score: ${result.playerScore}</p>
                        ${result.aiScores.map((score, i) => 
                            `<p>${this.getPlayerName(i + 1)} score: ${score}</p>`
                        ).join('')}
                        <p>Royalties: ${result.royalties}</p>
                        <p>Fouls: ${((result.fouls / result.totalMoves) * 100).toFixed(1)}%</p>
                        <p>Scoops: ${((result.scoops / result.totalMoves) * 100).toFixed(1)}%</p>
                        ${result.fantasyAchieved ? '<p class="fantasy-achieved">Fantasy achieved!</p>' : ''}
                    </div>
                </div>
                <div class="game-over-buttons">
                    <button class="new-game">New Game</button>
                    <button class="return-menu">Return to Menu</button>
                </div>
            </div>
        `;

        this.setupGameOverListeners(modal);
        document.body.appendChild(modal);

        // Анимация появления
        requestAnimationFrame(() => modal.classList.add('show'));
    }

    setupGameOverListeners(modal) {
        modal.querySelector('.new-game').addEventListener('click', () => {
            modal.classList.remove('show');
            setTimeout(() => {
                modal.remove();
                this.game.startGame();
            }, 300);
        });

        modal.querySelector('.return-menu').addEventListener('click', () => {
            modal.classList.remove('show');
            setTimeout(() => {
                modal.remove();
                this.game.returnToMenu();
            }, 300);
        });
    }

    // Утилиты
    getPlayerName(player) {
        return player === 0 ? 'You' : 
            this.game.state.agents[player - 1]?.name.replace('Agent', 'AI ') || 
            `Player ${player}`;
    }

    formatCard(card) {
        return `${card.rank}${this.getSuitSymbol(card.suit)}`;
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

    findCard(cardData) {
        return document.querySelector(
            `.card[data-rank="${cardData.rank}"][data-suit="${cardData.suit}"]`
        );
    }

    findSlot(position) {
        return document.querySelector(`.card-slot[data-position="${position}"]`);
    }

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

    cleanup() {
        // Удаляем все обработчики событий
        this.eventListeners.forEach((handlers, element) => {
            handlers.forEach((handler, event) => {
                element.removeEventListener(event, handler);
            });
        });
        this.eventListeners.clear();

        // Очищаем все интервалы и таймауты
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }

        // Удаляем все модальные окна
        document.querySelectorAll('.modal').forEach(modal => modal.remove());
        
        // Очищаем все уведомления
        document.querySelectorAll('.toast').forEach(toast => toast.remove());
    }

    // Методы для работы с темой
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

        // Вызываем событие изменения темы
        this.dispatchThemeChange(newTheme);
    }

    dispatchThemeChange(theme) {
        const event = new CustomEvent('themechange', {
            detail: { theme }
        });
        document.dispatchEvent(event);
    }

    // Методы для работы со звуком
    toggleSound(enabled) {
        document.body.classList.toggle('sound-enabled', enabled);
        localStorage.setItem('soundEnabled', enabled);
        
        if (enabled) {
            this.initializeSoundSystem();
        } else {
            this.cleanupSoundSystem();
        }
    }

    initializeSoundSystem() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.loadSounds();
        }
    }

    async loadSounds() {
        this.sounds = new Map();
        const soundFiles = {
            cardPlace: 'sounds/card-place.mp3',
            cardFlip: 'sounds/card-flip.mp3',
            victory: 'sounds/victory.mp3',
            error: 'sounds/error.mp3'
        };

        try {
            for (const [name, file] of Object.entries(soundFiles)) {
                const response = await fetch(file);
                const arrayBuffer = await response.arrayBuffer();
                const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
                this.sounds.set(name, audioBuffer);
            }
        } catch (error) {
            console.error('Failed to load sounds:', error);
        }
    }

    playSound(name) {
        if (!this.audioContext || !this.sounds.has(name)) return;

        const source = this.audioContext.createBufferSource();
        source.buffer = this.sounds.get(name);
        source.connect(this.audioContext.destination);
        source.start(0);
    }

    cleanupSoundSystem() {
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
        this.sounds?.clear();
    }

    // Методы для работы с анимациями
    setAnimationState(value) {
        this.animationEnabled = value !== 'off';
        document.body.classList.toggle('animations-disabled', !this.animationEnabled);
        localStorage.setItem('animationState', value);
        
        // Обновляем CSS переменные
        document.documentElement.style.setProperty(
            '--animation-duration',
            this.animationEnabled ? '0.3s' : '0s'
        );
    }

    // Методы для работы с мобильной версией
    initializeMobileUI() {
        this.setupTouchEvents();
        this.createMobileMenu();
        this.adjustLayoutForMobile();

        // Добавляем обработчики для жестов
        this.setupGestureHandlers();
    }

    setupGestureHandlers() {
        let touchStartX = 0;
        let touchStartY = 0;
        let touchStartTime = 0;

        this.addEventHandler(document, 'touchstart', (e) => {
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
            touchStartTime = Date.now();
        });

        this.addEventHandler(document, 'touchend', (e) => {
            const touchEndX = e.changedTouches[0].clientX;
            const touchEndY = e.changedTouches[0].clientY;
            const touchEndTime = Date.now();

            const deltaX = touchEndX - touchStartX;
            const deltaY = touchEndY - touchStartY;
            const deltaTime = touchEndTime - touchStartTime;

            // Определяем тип жеста
            if (deltaTime < 300) { // Быстрый жест
                if (Math.abs(deltaX) > 50 && Math.abs(deltaY) < 30) {
                    // Горизонтальный свайп
                    if (deltaX > 0) {
                        this.handleSwipeRight();
                    } else {
                        this.handleSwipeLeft();
                    }
                }
            }
        });
    }

    handleSwipeRight() {
        if (this.elements.sidePanel?.classList.contains('active')) {
            this.closeSidePanel();
        }
    }

    handleSwipeLeft() {
        if (!this.elements.sidePanel?.classList.contains('active')) {
            this.openSidePanel();
        }
    }

    // Методы для работы с доступностью
    announceGameState(message) {
        const announcer = document.getElementById('gameAnnouncer') || 
            this.createAnnouncer();
        
        announcer.textContent = message;
    }

    createAnnouncer() {
        const announcer = document.createElement('div');
        announcer.id = 'gameAnnouncer';
        announcer.className = 'screen-reader-only';
        announcer.setAttribute('role', 'status');
        announcer.setAttribute('aria-live', 'polite');
        document.body.appendChild(announcer);
        return announcer;
    }
}

// Экспорт класса
export default GameUI;
