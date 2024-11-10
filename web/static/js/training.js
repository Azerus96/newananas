// web/static/js/training.js

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
                totalAttempts: 0,
                fouls: 0,
                scoops: 0,
                totalMoves: 0
            }
        };

        this.config = {
            fantasyMode: false,
            progressiveFantasy: false,
            thinkTime: 30,
            animationEnabled: true
        };

        this.initializeElements();
        this.initializeEventListeners();
        this.setupMobileSupport();
        this.loadSettings();
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
            animationControl: document.getElementById('animationControl'),

            // Статистика
            movesCount: document.getElementById('movesCount'),
            avgThinkTime: document.getElementById('avgThinkTime'),
            fantasyRate: document.getElementById('fantasyRate'),
            foulsRate: document.getElementById('foulsRate'),
            scoopsRate: document.getElementById('scoopsRate'),

            // Выбор карт
            ranks: document.querySelectorAll('.rank'),
            suits: document.querySelectorAll('.suit')
        };

        // Инициализация слотов для карт
        this.initializeCardSlots();
        
        // Инициализация подсказок
        this.initializeTooltips();
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

    initializeTooltips() {
        const tooltips = {
            foulsRate: 'Процент нарушений правила старшинства комбинаций',
            scoopsRate: 'Процент ситуаций, когда все три ряда выигрывают',
            fantasyRate: 'Процент успешных фантазий'
        };

        Object.entries(tooltips).forEach(([id, text]) => {
            const element = document.getElementById(id);
            if (element) {
                element.setAttribute('data-tooltip', text);
                element.classList.add('has-tooltip');
            }
        });
    }

    setupMobileSupport() {
        this.isMobile = window.innerWidth <= 768;
        if (this.isMobile) {
            this.setupTouchInteractions();
            this.adjustLayoutForMobile();
        }

        window.addEventListener('orientationchange', () => {
            this.adjustLayoutForMobile();
        });

        window.addEventListener('resize', () => {
            this.isMobile = window.innerWidth <= 768;
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
            this.elements.container.classList.add('landscape-layout');
            this.adjustCardSizeForLandscape();
        } else {
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

        this.elements.animationControl.addEventListener('change', (e) => {
            this.config.animationEnabled = e.target.value !== 'off';
            document.body.classList.toggle('animations-disabled', !this.config.animationEnabled);
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

async startTraining() {
    try {
        const response = await fetch('/api/training/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(this.config)
        });

        const data = await response.json();
        if (data.status === 'ok') {
            this.state.active = true;
            this.state.sessionId = data.session_id;
            this.updateUI(data.initial_state);
            this.showMessage('Тренировка начата');
        } else {
            throw new Error(data.message || 'Failed to start training');
        }
    } catch (error) {
        console.error('Failed to start training:', error);
        this.showError('Не удалось начать тренировку');
    }
}

async requestAIDistribution() {
    if (!this.validateInput()) {
        this.showError('Разместите как минимум 2 входные карты');
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
            if (this.config.animationEnabled) {
                await this.animateAIMove(result.move);
            } else {
                this.applyAIMove(result.move);
            }
            
            this.updateStatistics(result.statistics);
            
            // Проверяем на фолы и скупы
            if (result.move.isFoul) {
                this.state.statistics.fouls++;
            }
            if (result.move.isScoop) {
                this.state.statistics.scoops++;
            }
            this.state.statistics.totalMoves++;
            
        } else {
            throw new Error(result.message);
        }
    } catch (error) {
        console.error('AI distribution failed:', error);
        this.showError('Не удалось получить ход AI');
    } finally {
        this.state.aiThinking = false;
        this.hideAIThinking();
    }
}

validateInput() {
    const inputCards = this.getInputCards();
    return inputCards.length >= 2;
}

getInputCards() {
    const cards = [];
    this.elements.inputCards.querySelectorAll('.card').forEach(cardElement => {
        cards.push(this.getCardData(cardElement));
    });
    return cards;
}

getRemovedCards() {
    const cards = [];
    [this.elements.removedCards.row1, this.elements.removedCards.row2].forEach(row => {
        row.querySelectorAll('.card').forEach(cardElement => {
            cards.push(this.getCardData(cardElement));
        });
    });
    return cards;
}

async animateAIMove(move) {
    for (const action of move.actions) {
        await new Promise(resolve => {
            setTimeout(() => {
                this.applyMoveAction(action);
                resolve();
            }, this.config.animationEnabled ? 300 : 0);
        });
    }
}

applyMoveAction(action) {
    const { card, position, type } = action;
    const targetSlot = this.findSlotByPosition(position);
    
    if (type === 'place') {
        this.placeCard(targetSlot, card);
    } else if (type === 'remove') {
        this.removeCard(targetSlot);
    }
}

updateStatistics(stats) {
    this.state.statistics = { ...this.state.statistics, ...stats };
    
    // Обновляем отображение статистики
    this.elements.movesCount.textContent = this.state.statistics.movesAnalyzed;
    this.elements.avgThinkTime.textContent = 
        `${this.calculateAverageThinkTime().toFixed(2)}s`;
    this.elements.fantasyRate.textContent = 
        `${this.calculateFantasyRate().toFixed(1)}%`;
    this.elements.foulsRate.textContent = 
        `${this.calculateFoulsRate().toFixed(1)}%`;
    this.elements.scoopsRate.textContent = 
        `${this.calculateScoopsRate().toFixed(1)}%`;
}

calculateAverageThinkTime() {
    const times = this.state.statistics.thinkTime;
    return times.length ? times.reduce((a, b) => a + b) / times.length : 0;
}

calculateFantasyRate() {
    const { fantasySuccess, totalAttempts } = this.state.statistics;
    return totalAttempts ? (fantasySuccess / totalAttempts) * 100 : 0;
}

calculateFoulsRate() {
    const { fouls, totalMoves } = this.state.statistics;
    return totalMoves ? (fouls / totalMoves) * 100 : 0;
}

calculateScoopsRate() {
    const { scoops, totalMoves } = this.state.statistics;
    return totalMoves ? (scoops / totalMoves) * 100 : 0;
}

showAIThinking() {
    const overlay = document.createElement('div');
    overlay.className = 'thinking-overlay';
    overlay.innerHTML = `
        <div class="thinking-content">
            <div class="spinner"></div>
            <p>AI анализирует ходы...</p>
            ${this.config.animationEnabled ? `
                <div class="progress-bar">
                    <div class="progress"></div>
                </div>
            ` : ''}
        </div>
    `;
    document.body.appendChild(overlay);

    if (this.config.animationEnabled) {
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
}

hideAIThinking() {
    const overlay = document.querySelector('.thinking-overlay');
    if (overlay) {
        overlay.classList.add('fade-out');
        setTimeout(() => overlay.remove(), 300);
        }
    }

    showMessage(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    showError(message) {
        this.showMessage(message, 'error');
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
                totalAttempts: 0,
                fouls: 0,
                scoops: 0,
                totalMoves: 0
            });
        }, 300);
    }

    clearSelection() {
        this.state.selectedRank = null;
        this.state.selectedSuit = null;
        this.state.selectedSlot = null;

        this.elements.ranks.forEach(button => {
            button.classList.remove('selected');
        });
        this.elements.suits.forEach(button => {
            button.classList.remove('selected');
        });
        document.querySelectorAll('.card-slot').forEach(slot => {
            slot.classList.remove('selected');
        });
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

    loadSettings() {
        try {
            const savedSettings = localStorage.getItem('trainingSettings');
            if (savedSettings) {
                const settings = JSON.parse(savedSettings);
                this.config = { ...this.config, ...settings };
                this.applySettings();
            }
        } catch (error) {
            console.error('Failed to load settings:', error);
        }
    }

    saveSettings() {
        try {
            localStorage.setItem('trainingSettings', JSON.stringify(this.config));
        } catch (error) {
            console.error('Failed to save settings:', error);
        }
    }

    applySettings() {
        // Применяем настройки к UI
        if (this.elements.fantasyMode) {
            this.elements.fantasyMode.checked = this.config.fantasyMode;
        }
        if (this.elements.progressiveFantasy) {
            this.elements.progressiveFantasy.checked = this.config.progressiveFantasy;
        }
        if (this.elements.thinkTime) {
            this.elements.thinkTime.value = this.config.thinkTime;
        }
        if (this.elements.animationControl) {
            this.elements.animationControl.value = this.config.animationEnabled ? 'normal' : 'off';
        }

        // Применяем анимации
        document.body.classList.toggle('animations-disabled', !this.config.animationEnabled);

        // Обновляем видимость карт
        this.updateInputCardsVisibility();
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

    adjustCardSizeForLandscape() {
        document.documentElement.style.setProperty('--card-width', '50px');
        document.documentElement.style.setProperty('--card-height', '70px');
    }

    adjustCardSizeForPortrait() {
        document.documentElement.style.setProperty('--card-width', '60px');
        document.documentElement.style.setProperty('--card-height', '84px');
    }

    exportTrainingData() {
        const data = {
            statistics: this.state.statistics,
            config: this.config,
            timestamp: new Date().toISOString()
        };

        const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `training_data_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.trainingMode = new TrainingMode();
});
