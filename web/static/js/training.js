// web/static/js/training.js

class TrainingMode {
    constructor() {
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
        // Создаем слоты для карт на всех улицах
        this.createCardSlots('frontStreet', 3);
        this.createCardSlots('middleStreet', 5);
        this.createCardSlots('backStreet', 5);
        this.createCardSlots('inputCards', 16);
        this.createCardSlots('removedCardsRow1', 13);
        this.createCardSlots('removedCardsRow2', 13);
    }

    createCardSlots(containerId, count) {
        const container = document.getElementById(containerId);
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
        if (containerId === 'inputCards') {
            this.selectedInputSlot = slot;
            this.highlightSelectedSlot();
        }
        
        if (this.selectedRank && this.selectedSuit) {
            this.placeCard(slot, containerId);
        }
    }

    selectRank(rank) {
        this.selectedRank = rank;
        this.updateSelectionUI();
        this.tryPlaceCard();
    }

    selectSuit(suit) {
        this.selectedSuit = suit;
        this.updateSelectionUI();
        this.tryPlaceCard();
    }

    tryPlaceCard() {
        if (this.selectedRank && this.selectedSuit && this.selectedInputSlot) {
            const card = this.createCardElement(this.selectedRank, this.selectedSuit);
            this.placeCardInSlot(this.selectedInputSlot, card);
            this.clearSelection();
        }
    }

    placeCardInSlot(slot, card) {
        slot.innerHTML = '';
        slot.appendChild(card);
        slot.classList.add('card-placed');
        setTimeout(() => slot.classList.remove('card-placed'), 300);
    }

    createCardElement(rank, suit) {
        const card = document.createElement('div');
        card.className = `card ${suit === 'h' || suit === 'd' ? 'red' : 'black'}`;
        card.textContent = `${rank}${suit}`;
        return card;
    }

    clearSelection() {
        this.selectedRank = null;
        this.selectedSuit = null;
        this.selectedInputSlot = null;
        this.updateSelectionUI();
    }

    updateSelectionUI() {
        // Обновляем подсветку выбранных кнопок
        document.querySelectorAll('.rank').forEach(button => {
            button.classList.toggle('selected', button.dataset.rank === this.selectedRank);
        });

        document.querySelectorAll('.suit').forEach(button => {
            button.classList.toggle('selected', button.dataset.suit === this.selectedSuit);
        });
    }

    async requestAIDistribution() {
        const inputCards = this.getInputCards();
        const removedCards = this.getRemovedCards();

        try {
            const response = await fetch('/api/training/distribute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    input_cards: inputCards,
                    removed_cards: removedCards,
                    config: this.currentConfig
                })
            });

            const result = await response.json();
            if (result.status === 'ok') {
                this.displayAIMove(result.move);
                this.updateStatistics(result.statistics);
            } else {
                this.showError(result.message);
            }
        } catch (error) {
            this.showError('Failed to communicate with server');
        }
    }

    displayAIMove(move) {
        // Анимированное размещение карт
        move.placements.forEach((placement, index) => {
            setTimeout(() => {
                const {card, street, position} = placement;
                const slot = document.querySelector(`#${street}Street .card-slot[data-index="${position}"]`);
                const cardElement = this.createCardElement(card.rank, card.suit);
                this.placeCardInSlot(slot, cardElement);
            }, index * 300);
        });
    }

    updateStatistics(stats) {
        document.getElementById('movesCount').textContent = stats.moves_analyze
