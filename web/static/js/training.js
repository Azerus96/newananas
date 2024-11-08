class TrainingMode {
    constructor() {
        this.state = {
            active: false,
            currentPhase: null,
            aiThinking: false,
            lastMove: null,
            selectedRank: null,
            selectedSuit: null,
            selectedSlot: null,
            statistics: {
                movesAnalyzed: 0,
                thinkTime: [],
                fantasySuccess: 0,
                totalAttempts: 0
            }
        };

        this.config = {
            fantasyMode: false,
            progressiveFantasy: false,
            thinkTime: 30
        };

        this.initializeElements();
        this.initializeEventListeners();
        this.setupMobileSupport();
    }

    initializeElements() {
        this.elements = {
            // Основные элементы
            container: document.querySelector('.container'),
            frontStreet: document.getElementById('frontStreet'),
            middleStreet: document.getElementById('middleStreet'),
            backStreet: document.getElementById('backStreet'),
            inputCards: document.getElementById('inputCards'),
            removedCards: {
                row1: document.getElementById('removedCardsRow1'),
                row2: document.getElementById('removedCardsRow2')
            },

            // Контролы
            fantasyMode: document.getElementById('fantasyMode'),
            progressiveFantasy: document.getElementById('progressiveFantasy'),
            thinkTime: document.getElementById('thinkTime'),
            distributeButton: document.getElementById('distributeCards'),
            clearButton: document.getElementById('clearSelection'),
            startButton: document.getElementById('startTraining'),
            resetButton: document.getElementById('resetBoard'),

            // Статистика
            movesCount: document.getElementById('movesCount'),
            avgThinkTime: document.getElementById('avgThinkTime'),
            fantasyRate: document.getElementById('fantasyRate'),

            // Выбор карт
            ranks: document.querySelectorAll('.rank'),
            suits: document.querySelectorAll('.suit')
        };

        // Инициализация слотов для карт
        this.initializeCardSlots();
    }

    initializeCardSlots() {
        // Создаем слоты для карт в каждой секции
        const createSlots = (container, count) => {
            container.innerHTML = '';
            for (let i = 0; i < count; i++) {
                const slot = document.createElement('div');
                slot.className = 'card-slot';
                slot.dataset.index = i;
                container.appendChild(slot);
            }
        };

        // Инициализация всех слотов
        createSlots(this.elements.frontStreet, 3);
        createSlots(this.elements.middleStreet, 5);
        createSlots(this.elements.backStreet, 5);
        createSlots(this.elements.removedCards.row1, 15);
        createSlots(this.elements.removedCards.row2, 15);
        createSlots(this.elements.inputCards, 17); // Максимальное количество для фантазии
    }

    setupMobileSupport() {
        this.isMobile = window.innerWidth <= 768;
        if (this.isMobile) {
            this.setupTouchInteractions();
            this.adjustLayoutForMobile();
        }

        // Слушаем изменение ориентации
        window.addEventListener('orientationchange', () => {
            this.adjustLayoutForMobile();
        });
    }

    setupTouchInteractions() {
        let touchStartX, touchStartY;
        let currentCard = null;

        document.addEventListener('touchstart', (e) => {
            if (e.target.classList.contains('card')) {
                currentCard = e.target;
                const touch = e.touches[0];
                touchStartX = touch.clientX - currentCard.offsetLeft;
                touchStartY = touch.clientY - currentCard.offsetTop;
                currentCard.classList.add('dragging');
            }
        }, { passive: false });

        document.addEventListener('touchmove', (e) => {
            if (currentCard) {
                e.preventDefault();
                const touch = e.touches[0];
                currentCard.style.position = 'fixed';
                currentCard.style.left = `${touch.clientX - touchStartX}px`;
                currentCard.style.top = `${touch.clientY - touchStartY}px`;
                
                // Подсветка возможных слотов
                this.highlightValidSlots(currentCard);
            }
        }, { passive: false });

        document.addEventListener('touchend', (e) => {
            if (currentCard) {
                const touch = e.changedTouches[0];
                const slot = this.findSlotAtPosition(touch.clientX, touch.clientY);
                
                if (slot && this.isValidMove(currentCard, slot)) {
                    this.moveCardToSlot(currentCard, slot);
                } else {
                    this.resetCardPosition(currentCard);
                }
                
                currentCard.classList.remove('dragging');
                this.clearHighlightedSlots();
                currentCard = null;
            }
        });
    }

adjustLayoutForMobile() {
        const isLandscape = window.innerWidth > window.innerHeight;
        document.body.classList.toggle('landscape', isLandscape);

        if (isLandscape) {
            // Горизонтальная ориентация
            this.elements.container.classList.add('landscape-layout');
            this.adjustCardSizeForLandscape();
        } else {
            // Вертикальная ориентация
            this.elements.container.classList.remove('landscape-layout');
            this.adjustCardSizeForPortrait();
        }
    }

    initializeEventListeners() {
        // Настройки
        this.elements.fantasyMode.addEventListener('change', (e) => {
            this.config.fantasyMode = e.target.checked;
            this.updateInputCardsVisibility();
        });

        this.elements.progressiveFantasy.addEventListener('change', (e) => {
            this.config.progressiveFantasy = e.target.checked;
        });

        this.elements.thinkTime.addEventListener('input', (e) => {
            this.config.thinkTime = parseInt(e.target.value);
        });

        // Кнопки управления
        this.elements.startButton.addEventListener('click', () => this.startTraining());
        this.elements.resetButton.addEventListener('click', () => this.resetBoard());
        this.elements.distributeButton.addEventListener('click', () => this.requestAIDistribution());
        this.elements.clearButton.addEventListener('click', () => this.clearSelection());

        // Выбор карт
        this.elements.ranks.forEach(button => {
            button.addEventListener('click', (e) => this.selectRank(e.target.dataset.rank));
        });

        this.elements.suits.forEach(button => {
            button.addEventListener('click', (e) => this.selectSuit(e.target.dataset.suit));
        });

        // Слоты для карт
        document.querySelectorAll('.card-slot').forEach(slot => {
            slot.addEventListener('click', () => this.handleSlotClick(slot));
        });

        // Обработка клавиатуры
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));

        // Отмена последнего действия
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
                e.preventDefault();
                this.undoLastAction();
            }
        });
    }

    updateInputCardsVisibility() {
        const inputContainer = this.elements.inputCards;
        const slots = inputContainer.querySelectorAll('.card-slot');
        
        slots.forEach((slot, index) => {
            if (this.config.fantasyMode) {
                slot.style.display = index < 17 ? 'block' : 'none';
            } else {
                slot.style.display = index < 5 ? 'block' : 'none';
            }
        });
    }

    selectRank(rank) {
        this.state.selectedRank = rank;
        this.elements.ranks.forEach(button => {
            button.classList.toggle('selected', button.dataset.rank === rank);
        });
        this.tryPlaceCard();
    }

    selectSuit(suit) {
        this.state.selectedSuit = suit;
        this.elements.suits.forEach(button => {
            button.classList.toggle('selected', button.dataset.suit === suit);
        });
        this.tryPlaceCard();
    }

    handleSlotClick(slot) {
        if (this.state.aiThinking) return;

        if (slot.classList.contains('occupied')) {
            // Удаление карты при повторном клике
            this.removeCard(slot);
        } else {
            this.state.selectedSlot = slot;
            this.highlightSelectedSlot();
            this.tryPlaceCard();
        }
    }

    tryPlaceCard() {
        if (this.state.selectedRank && this.state.selectedSuit && this.state.selectedSlot) {
            const card = {
                rank: this.state.selectedRank,
                suit: this.state.selectedSuit
            };

            if (this.isValidCardPlacement(card, this.state.selectedSlot)) {
                this.placeCard(this.state.selectedSlot, card);
                this.clearSelection();
            }
        }
    }

    placeCard(slot, card) {
        const cardElement = this.createCardElement(card);
        
        // Анимация размещения
        cardElement.style.opacity = '0';
        slot.innerHTML = '';
        slot.appendChild(cardElement);
        slot.classList.add('occupied');

        requestAnimationFrame(() => {
            cardElement.style.opacity = '1';
            cardElement.classList.add('card-placed');
        });

        // Сохраняем действие для отмены
        this.saveAction({
            type: 'place',
            slot: slot,
            card: card
        });

        this.updateStatistics();
    }

    removeCard(slot) {
        const cardElement = slot.querySelector('.card');
        if (cardElement) {
            // Анимация удаления
            cardElement.classList.add('card-removing');
            setTimeout(() => {
                slot.innerHTML = '';
                slot.classList.remove('occupied');
            }, 300);

            // Сохраняем действие для отмены
            this.saveAction({
                type: 'remove',
                slot: slot,
                card: this.getCardData(cardElement)
            });
        }
    }

async requestAIDistribution() {
        if (!this.validateInput()) {
            this.showError('Please place at least 2 input cards');
            return;
        }

        this.state.aiThinking = true;
        this.showAIThinking();

        try {
            const response = await fetch('/api/training/distribute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    input_cards: this.getInputCards(),
                    removed_cards: this.getRemovedCards(),
                    config: this.config
                })
            });

            const result = await response.json();
            if (result.status === 'ok') {
                await this.handleAIMove(result.move);
                this.updateStatistics(result.statistics);
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            console.error('AI distribution failed:', error);
            this.showError('Failed to get AI move');
        } finally {
            this.state.aiThinking = false;
            this.hideAIThinking();
        }
    }

    handleKeyboard(e) {
        // Быстрые клавиши для рангов
        const rankKeys = {
            'a': 'A', 'k': 'K', 'q': 'Q', 'j': 'J', 't': 'T',
            '2': '2', '3': '3', '4': '4', '5': '5',
            '6': '6', '7': '7', '8': '8', '9': '9'
        };

        // Быстрые клавиши для мастей
        const suitKeys = {
            'h': 'h', 's': 's', 'd': 'd', 'c': 'c'
        };

        const key = e.key.toLowerCase();

        if (rankKeys[key]) {
            this.selectRank(rankKeys[key]);
        } else if (suitKeys[key]) {
            this.selectSuit(suitKeys[key]);
        } else if (e.key === 'Escape') {
            this.clearSelection();
        } else if (e.key === 'Enter') {
            this.requestAIDistribution();
        }
    }

    saveAction(action) {
        if (!this.actionHistory) {
            this.actionHistory = [];
        }
        this.actionHistory.push(action);
    }

    undoLastAction() {
        if (!this.actionHistory || this.actionHistory.length === 0) {
            return;
        }

        const lastAction = this.actionHistory.pop();
        if (lastAction.type === 'place') {
            this.removeCard(lastAction.slot);
        } else if (lastAction.type === 'remove') {
            this.placeCard(lastAction.slot, lastAction.card);
        }
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        
        this.elements.container.prepend(errorDiv);
        
        setTimeout(() => {
            errorDiv.classList.add('fade-out');
            setTimeout(() => errorDiv.remove(), 300);
        }, 3000);
    }

    showAIThinking() {
        const overlay = document.createElement('div');
        overlay.className = 'thinking-overlay';
        overlay.innerHTML = `
            <div class="thinking-content">
                <div class="spinner"></div>
                <p>AI analyzing moves...</p>
                <div class="progress-bar">
                    <div class="progress"></div>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);

        // Анимация прогресса
        const progress = overlay.querySelector('.progress');
        let width = 0;
        const interval = setInterval(() => {
            if (width >= 100) {
                clearInterval(interval);
            } else {
                width++;
                progress.style.width = width + '%';
            }
        }, this.config.thinkTime * 10);
    }

    hideAIThinking() {
        const overlay = document.querySelector('.thinking-overlay');
        if (overlay) {
            overlay.classList.add('fade-out');
            setTimeout(() => overlay.remove(), 300);
        }
    }

    updateStatistics(stats = null) {
        if (stats) {
            this.state.statistics = { ...this.state.statistics, ...stats };
        }

        this.elements.movesCount.textContent = this.state.statistics.movesAnalyzed;
        this.elements.avgThinkTime.textContent = 
            `${this.calculateAverageThinkTime().toFixed(2)}s`;
        this.elements.fantasyRate.textContent = 
            `${this.calculateFantasyRate().toFixed(1)}%`;
    }

    calculateAverageThinkTime() {
        const times = this.state.statistics.thinkTime;
        return times.length ? times.reduce((a, b) => a + b) / times.length : 0;
    }

    calculateFantasyRate() {
        const { fantasySuccess, totalAttempts } = this.state.statistics;
        return totalAttempts ? (fantasySuccess / totalAttempts) * 100 : 0;
    }

    resetBoard() {
        // Анимация сброса
        const cards = document.querySelectorAll('.card');
        cards.forEach(card => {
            card.classList.add('card-removing');
        });

        setTimeout(() => {
            document.querySelectorAll('.card-slot').forEach(slot => {
                slot.innerHTML = '';
                slot.classList.remove('occupied');
            });

            this.clearSelection();
            this.actionHistory = [];
            this.updateStatistics({
                movesAnalyzed: 0,
                thinkTime: [],
                fantasySuccess: 0,
                totalAttempts: 0
            });
        }, 300);
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.trainingMode = new TrainingMode();
});
