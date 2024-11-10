// web/static/js/fantasy.js

class FantasyManager {
    constructor() {
        this.container = document.getElementById('fantasyStatus');
        this.state = {
            active: false,
            mode: 'normal',
            cardsCount: 0,
            consecutiveFantasies: 0,
            progressiveBonus: null,
            foulsRate: 0,
            scoopsRate: 0,
            totalAttempts: 0,
            successfulAttempts: 0
        };
        
        this.initialize();
    }

    initialize() {
        this.createFantasyPanel();
        this.setupEventListeners();
        this.startAutoUpdate();
    }

    createFantasyPanel() {
        this.container.innerHTML = `
            <div class="fantasy-panel">
                <div class="fantasy-status">
                    <h3>Fantasy Status</h3>
                    <div class="status-grid">
                        <div class="status-item">
                            <span class="status-label">Mode</span>
                            <span class="status-value" id="fantasyMode">Normal</span>
                        </div>
                        <div class="status-item">
                            <span class="status-label">Cards</span>
                            <span class="status-value" id="fantasyCards">13</span>
                        </div>
                        <div class="status-item">
                            <span class="status-label">Consecutive</span>
                            <span class="status-value" id="consecutiveFantasies">0</span>
                        </div>
                    </div>
                </div>
                
                <div class="fantasy-statistics">
                    <h3>Statistics</h3>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <span class="stat-label">Success Rate</span>
                            <span class="stat-value" id="fantasySuccessRate">0%</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Fouls Rate</span>
                            <span class="stat-value" id="foulsRate">0%</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Scoops Rate</span>
                            <span class="stat-value" id="scoopsRate">0%</span>
                        </div>
                    </div>
                </div>

                <div class="progressive-bonus" id="progressiveBonus" style="display: none;">
                    <span class="bonus-label">Progressive Bonus:</span>
                    <span class="bonus-value"></span>
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        // Слушатели событий для анимации
        const animationToggle = document.getElementById('animationToggle');
        if (animationToggle) {
            animationToggle.addEventListener('change', (e) => {
                document.body.classList.toggle('animations-disabled', !e.target.checked);
            });
        }

        // Обработка событий WebSocket
        socket.on('fantasy_update', (data) => {
            this.updateFantasyStatus(data);
        });

        socket.on('statistics_update', (data) => {
            this.updateStatistics(data);
        });
    }

    startAutoUpdate() {
        setInterval(() => this.requestUpdate(), 2000);
    }

    async requestUpdate() {
        try {
            const response = await fetch('/api/fantasy/status');
            const data = await response.json();
            
            if (data.status === 'ok') {
                this.updateFantasyStatus(data.fantasy_status);
                this.updateStatistics(data.statistics);
            }
        } catch (error) {
            console.error('Error updating fantasy status:', error);
        }
    }

    updateFantasyStatus(status) {
        this.state = { ...this.state, ...status };
        
        // Обновляем отображение
        document.getElementById('fantasyMode').textContent = this.state.mode;
        document.getElementById('fantasyCards').textContent = this.state.cardsCount;
        document.getElementById('consecutiveFantasies').textContent = this.state.consecutiveFantasies;

        // Обновляем индикатор активной фантазии
        this.container.classList.toggle('fantasy-active', this.state.active);

        // Обновляем прогрессивный бонус
        const bonusElement = document.getElementById('progressiveBonus');
        if (this.state.progressiveBonus) {
            bonusElement.style.display = 'block';
            bonusElement.querySelector('.bonus-value').textContent = this.state.progressiveBonus;
        } else {
            bonusElement.style.display = 'none';
        }

        // Анимация при изменении статуса
        if (this.state.active) {
            this.playFantasyAnimation();
        }
    }

    updateStatistics(statistics) {
        // Обновляем основную статистику
        document.getElementById('fantasySuccessRate').textContent = 
            `${((statistics.successfulAttempts / statistics.totalAttempts) * 100 || 0).toFixed(1)}%`;
        
        // Обновляем новые метрики
        document.getElementById('foulsRate').textContent = 
            `${(statistics.foulsRate * 100).toFixed(1)}%`;
        document.getElementById('scoopsRate').textContent = 
            `${(statistics.scoopsRate * 100).toFixed(1)}%`;

        // Обновляем графики если есть
        if (this.charts) {
            this.updateCharts(statistics);
        }
    }

    updateCharts(statistics) {
        // Обновление графиков статистики
        if (this.charts.progress) {
            this.charts.progress.data.datasets[0].data = statistics.progressData;
            this.charts.progress.update();
        }

        if (this.charts.distribution) {
            this.charts.distribution.data.datasets[0].data = statistics.distributionData;
            this.charts.distribution.update();
        }
    }

    playFantasyAnimation() {
        if (document.body.classList.contains('animations-disabled')) {
            return;
        }

        const animation = [
            { transform: 'scale(1)', opacity: '1' },
            { transform: 'scale(1.1)', opacity: '0.8' },
            { transform: 'scale(1)', opacity: '1' }
        ];

        const timing = {
            duration: 500,
            iterations: 1
        };

        this.container.animate(animation, timing);
    }

    // Методы для внешнего взаимодействия
    isFantasyActive() {
        return this.state.active;
    }

    getFantasyMode() {
        return this.state.mode;
    }

    getStatistics() {
        return {
            successRate: (this.state.successfulAttempts / this.state.totalAttempts) || 0,
            foulsRate: this.state.foulsRate,
            scoopsRate: this.state.scoopsRate,
            consecutiveFantasies: this.state.consecutiveFantasies
        };
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.fantasyManager = new FantasyManager();
});
