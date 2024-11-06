class TrainingMode {
    constructor() {
        this.state = {
            active: false,
            currentPhase: null,
            aiThinking: false,
            lastMove: null,
            statistics: {
                movesAnalyzed: 0,
                thinkTime: [],
                fantasySuccess: 0,
                totalAttempts: 0
            }
        };

        this.selectedRank = null;
        this.selectedSuit = null;
        this.selectedInputSlot = null;
        this.currentConfig = {
            fantasyMode: false,
            progressiveFantasy: false,
            thinkTime: 30
        };

        this.initializeEventListeners();
        this.initializeBoard();
    }

    initializeEventListeners() {
        // Настройки
        document.getElementById('fantasyMode').addEventListener('change', (e) => {
            this.currentConfig.fantasyMode = e.target.checked;
        });

        document.getElementById('progressiveFantasy').addEventListener('change', (e) => {
            this.currentConfig.progressiveFantasy = e.target.checked;
        });

        document.getElementById('thinkTime').addEventListener('change', (e) => {
            this.currentConfig.thinkTime = parseInt(e.target.value);
        });

        // Кнопки управления
        document.getElementById('startTraining').addEventListener('click', () => this.startTraining());
        document.getElementById('resetBoard').addEventListener('click', () => this.resetBoard());
        document.getElementById('distributeCards').addEventListener('click', () => this.requestAIDistribution());
        document.getElementById('clearSelection').addEventListener('click', () => this.clearSelection());

        // Выбор карт
        document.querySelectorAll('.rank').forEach(button => {
            button.addEventListener('click', (e) => this.selectRank(e.target.dataset.rank));
        });

        document.querySelectorAll('.suit').forEach(button => {
            button.addEventListener('click', (e) => this.selectSuit(e.target.dataset.suit));
        });

        // Слоты для карт
        this.initializeCardSlots();
    }

    initializeBoard() {
        const streets = {
            'frontStreet': 3,
            'middleStreet': 5,
            'backStreet': 5,
            'inputCards': 16,
            'removedCardsRow1': 13,
            'removedCardsRow2': 13
        };

        Object.entries(streets).forEach(([id, count]) => {
            this.createCardSlots(id, count);
        });
    }

    createCardSlots(containerId, count) {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = '';
        for (let i = 0; i < count; i++) {
            const slot = document.createElement('div');
            slot.className = 'card-slot';
            slot.dataset.index = i;
            slot.addEventListener('click', () => this.handleSlotClick(slot, containerId));
            container.appendChild(slot);
        }
    }

    handleSlotClick(slot, containerId) {
        if (this.state.aiThinking) return;

        if (containerId === 'inputCards') {
            this.selectedInputSlot = slot;
            this.highlightSelectedSlot();
        }

        if (this.selectedRank && this.selectedSuit) {
            this.placeCard(slot, {
                rank: this.selectedRank,
                suit: this.selectedSuit
            });
            this.clearSelection();
        }
    }

    placeCard(slot, card) {
        const cardElement = this.createCardElement(card);
        slot.innerHTML = '';
        slot.appendChild(cardElement);
        slot.classList.add('occupied');
        
        // Анимация размещения
        cardElement.classList.add('card-placed');
        setTimeout(() => cardElement.classList.remove('card-placed'), 300);
    }

    createCardElement(card) {
        const element = document.createElement('div');
        element.className = `card ${card.suit === 'h' || card.suit === 'd' ? 'red' : 'black'}`;
        element.innerHTML = `
            <div class="card-inner">
                <span class="card-value">${card.rank}</span>
                <span class="card-suit">${this.getSuitSymbol(card.suit)}</span>
            </div>
        `;
        return element;
    }

    getSuitSymbol(suit) {
        return {
            'h': '♥',
            'd': '♦',
            'c': '♣',
            's': '♠'
        }[suit] || suit;
    }

    // Продолжение класса TrainingMode...

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
                    config: this.currentConfig,
                    session_id: this.sessionId
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

    async handleAIMove(move) {
        for (const placement of move.placements) {
            await this.animateCardPlacement(placement);
            await new Promise(resolve => setTimeout(resolve, 300));
        }

        this.state.lastMove = move;
        this.updateUI();
    }

    async animateCardPlacement(placement) {
        const { card, street, position } = placement;
        const targetSlot = document.querySelector(`#${street}Street .card-slot[data-index="${position}"]`);
        
        if (!targetSlot) return;

        const cardElement = this.createCardElement(card);
        cardElement.style.position = 'absolute';
        cardElement.style.opacity = '0';
        document.body.appendChild(cardElement);

        const finalRect = targetSlot.getBoundingClientRect();
        cardElement.style.top = `${finalRect.top}px`;
        cardElement.style.left = `${finalRect.left}px`;
        
        // Анимация появления
        await new Promise(resolve => {
            requestAnimationFrame(() => {
                cardElement.style.transition = 'all 0.3s ease-out';
                cardElement.style.opacity = '1';
                setTimeout(resolve, 300);
            });
        });

        // Размещение карты в слоте
        cardElement.remove();
        this.placeCard(targetSlot, card);
    }

    updateStatistics(stats) {
        this.state.statistics = {
            ...this.state.statistics,
            movesAnalyzed: stats.moves_analyzed || 0,
            thinkTime: [...this.state.statistics.thinkTime, stats.think_time || 0],
            fantasySuccess: stats.fantasy_success || 0,
            totalAttempts: stats.total_attempts || 0
        };

        // Обновление UI статистики
        document.getElementById('movesCount').textContent = this.state.statistics.movesAnalyzed;
        document.getElementById('avgThinkTime').textContent = 
            `${this.calculateAverageThinkTime().toFixed(2)}s`;
        document.getElementById('fantasyRate').textContent = 
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

    validateInput() {
        const inputCards = this.getInputCards();
        return inputCards.length >= 2;
    }

    getInputCards() {
        const cards = [];
        document.querySelectorAll('#inputCards .card-slot').forEach(slot => {
            const cardElement = slot.querySelector('.card');
            if (cardElement) {
                const [rank, suit] = this.parseCardElement(cardElement);
                cards.push({ rank, suit });
            }
        });
        return cards;
    }

    getRemovedCards() {
        const cards = [];
        ['removedCardsRow1', 'removedCardsRow2'].forEach(rowId => {
            document.querySelectorAll(`#${rowId} .card-slot`).forEach(slot => {
                const cardElement = slot.querySelector('.card');
                if (cardElement) {
                    const [rank, suit] = this.parseCardElement(cardElement);
                    cards.push({ rank, suit });
                }
            });
        });
        return cards;
    }

    parseCardElement(cardElement) {
        const value = cardElement.querySelector('.card-value').textContent;
        const suit = cardElement.querySelector('.card-suit').textContent;
        return [value, this.getSuitCode(suit)];
    }

    getSuitCode(symbol) {
        const codes = { '♥': 'h', '♦': 'd', '♣': 'c', '♠': 's' };
        return codes[symbol] || symbol;
    }

    showAIThinking() {
        const overlay = document.createElement('div');
        overlay.className = 'thinking-overlay';
        overlay.innerHTML = `
            <div class="thinking-content">
                <div class="spinner"></div>
                <p>AI thinking...</p>
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

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        
        document.querySelector('.container').prepend(errorDiv);
        
        setTimeout(() => {
            errorDiv.classList.add('fade-out');
            setTimeout(() => errorDiv.remove(), 300);
        }, 3000);
    }

    resetBoard() {
        document.querySelectorAll('.card-slot').forEach(slot => {
            slot.innerHTML = '';
            slot.classList.remove('occupied');
        });

        this.clearSelection();
        this.resetConfig();
        this.state.statistics = {
            movesAnalyzed: 0,
            thinkTime: [],
            fantasySuccess: 0,
            totalAttempts: 0
        };
        this.updateStatistics(this.state.statistics);
    }

    resetConfig() {
        this.currentConfig = {
            fantasyMode: false,
            progressiveFantasy: false,
            thinkTime: 30
        };

        document.getElementById('fantasyMode').checked = false;
        document.getElementById('progressiveFantasy').checked = false;
        document.getElementById('thinkTime').value = '30';
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.trainingMode = new TrainingMode();
});
