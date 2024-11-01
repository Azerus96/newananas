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

    // web/static/js/training.js (продолжение)

    updateStatistics(stats) {
        document.getElementById('movesCount').textContent = stats.moves_analyzed;
        document.getElementById('avgThinkTime').textContent = `${stats.average_think_time.toFixed(2)}s`;
        document.getElementById('fantasyRate').textContent = `${(stats.fantasy_success_rate * 100).toFixed(1)}%`;
        
        // Обновляем дополнительную статистику
        this.updateDetailedStats(stats);
    }

    updateDetailedStats(stats) {
        const detailedStats = {
            'bestCombinations': stats.best_combinations || {},
            'streetSuccess': stats.street_success_rates || {},
            'learningProgress': stats.learning_progress || {}
        };

        // Обновляем графики если они есть
        if (this.charts) {
            this.charts.updateData(detailedStats);
        }
    }

    getInputCards() {
        const cards = [];
        document.querySelectorAll('#inputCards .card-slot').forEach(slot => {
            const cardElement = slot.querySelector('.card');
            if (cardElement) {
                const cardText = cardElement.textContent;
                cards.push({
                    rank: cardText[0],
                    suit: cardText[1]
                });
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
                    const cardText = cardElement.textContent;
                    cards.push({
                        rank: cardText[0],
                        suit: cardText[1]
                    });
                }
            });
        });
        return cards;
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

    resetBoard() {
        // Очищаем все слоты
        document.querySelectorAll('.card-slot').forEach(slot => {
            slot.innerHTML = '';
        });
        
        // Сбрасываем выбранные значения
        this.clearSelection();
        
        // Сбрасываем конфигурацию
        document.getElementById('fantasyMode').checked = false;
        document.getElementById('progressiveFantasy').checked = false;
        document.getElementById('thinkTime').value = 30;
        
        this.currentConfig = {
            fantasyMode: false,
            progressiveFantasy: false,
            thinkTime: 30
        };
    }

    startTraining() {
        this.resetBoard();
        this.initializeCharts();
        this.updateStatistics({
            moves_analyzed: 0,
            average_think_time: 0,
            fantasy_success_rate: 0
        });
    }

    initializeCharts() {
        this.charts = new TrainingCharts();
    }
}

class TrainingCharts {
    constructor() {
        this.setupChartContainers();
        this.initializeCharts();
    }

    setupChartContainers() {
        const chartsContainer = document.createElement('div');
        chartsContainer.className = 'charts-container';
        chartsContainer.innerHTML = `
            <div class="chart-wrapper">
                <canvas id="combinationsChart"></canvas>
            </div>
            <div class="chart-wrapper">
                <canvas id="successRateChart"></canvas>
            </div>
            <div class="chart-wrapper">
                <canvas id="learningChart"></canvas>
            </div>
        `;
        
        document.querySelector('.statistics-panel').appendChild(chartsContainer);
    }

    initializeCharts() {
        // Инициализация графика комбинаций
        this.combinationsChart = new Chart(
            document.getElementById('combinationsChart').getContext('2d'),
            {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Best Combinations',
                        data: [],
                        backgroundColor: 'rgba(54, 162, 235, 0.5)'
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            }
        );

        // Инициализация графика успешности
        this.successRateChart = new Chart(
            document.getElementById('successRateChart').getContext('2d'),
            {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Success Rate',
                        data: [],
                        borderColor: 'rgba(75, 192, 192, 1)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 1
                        }
                    }
                }
            }
        );

        // Инициализация графика прогресса обучения
        this.learningChart = new Chart(
            document.getElementById('learningChart').getContext('2d'),
            {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Learning Progress',
                        data: [],
                        borderColor: 'rgba(153, 102, 255, 1)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            }
        );
    }

    updateData(stats) {
        this.updateCombinationsChart(stats.bestCombinations);
        this.updateSuccessRateChart(stats.streetSuccess);
        this.updateLearningChart(stats.learningProgress);
    }

    updateCombinationsChart(combinations) {
        this.combinationsChart.data.labels = Object.keys(combinations);
        this.combinationsChart.data.datasets[0].data = Object.values(combinations);
        this.combinationsChart.update();
    }

    updateSuccessRateChart(successRates) {
        this.successRateChart.data.labels = Object.keys(successRates);
        this.successRateChart.data.datasets[0].data = Object.values(successRates);
        this.successRateChart.update();
    }

    updateLearningChart(progress) {
        this.learningChart.data.labels = progress.map((_, index) => `Episode ${index + 1}`);
        this.learningChart.data.datasets[0].data = progress;
        this.learningChart.update();
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.trainingMode = new TrainingMode();
});
