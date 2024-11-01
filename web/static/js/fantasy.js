// web/static/js/fantasy.js

class FantasyDisplay {
    constructor() {
        this.fantasyContainer = document.getElementById('fantasyStatus');
        this.initialize();
    }

    initialize() {
        this.createFantasyPanel();
        this.startAutoUpdate();
    }

    createFantasyPanel() {
        this.fantasyContainer.innerHTML = `
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
                    <h3>Fantasy Statistics</h3>
                    <div id="fantasyStats" class="stats-container"></div>
                </div>
            </div>
        `;
    }

    startAutoUpdate() {
        setInterval(() => this.updateFantasyStatus(), 2000);
    }

    async updateFantasyStatus() {
        try {
            const response = await fetch('/api/game/fantasy_status');
            const data = await response.json();
            
            if (data.status === 'ok') {
                this.updateStatusDisplay(data.fantasy_status);
                this.updateStatisticsDisplay(data.fantasy_statistics);
            }
        } catch (error) {
            console.error('Error updating fantasy status:', error);
        }
    }

    updateStatusDisplay(status) {
        document.getElementById('fantasyMode').textContent = status.mode;
        document.getElementById('fantasyCards').textContent = status.cards_count;
        document.getElementById('consecutiveFantasies').textContent = 
            status.consecutive_fantasies;

        // Добавляем индикатор активной фантазии
        this.fantasyContainer.classList.toggle('fantasy-active', status.active);

        // Отображаем прогрессивный бонус, если есть

        // Отображаем прогрессивный бонус, если есть
        if (status.progressive_bonus) {
            const bonusElement = document.createElement('div');
            bonusElement.className = 'progressive-bonus';
            bonusElement.innerHTML = `
                <span class="bonus-label">Progressive Bonus:</span>
                <span class="bonus-value">${status.progressive_bonus}</span>
            `;
            this.fantasyContainer.appendChild(bonusElement);
        }
    }

    updateStatisticsDisplay(statistics) {
        const statsContainer = document.getElementById('fantasyStats');
        statsContainer.innerHTML = '';

        // Общая статистика
        const generalStats = document.createElement('div');
        generalStats.className = 'stats-section';
        generalStats.innerHTML = `
            <h4>Overall Statistics</h4>
            <div class="stats-grid">
                <div class="stat-item">
                    <span class="stat-label">Total Entries</span>
                    <span class="stat-value">${statistics.manager_stats.total_entries}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Success Rate</span>
                    <span class="stat-value">${(statistics.manager_stats.success_rate * 100).toFixed(1)}%</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Max Consecutive</span>
                    <span class="stat-value">${statistics.manager_stats.max_consecutive}</span>
                </div>
            </div>
        `;
        statsContainer.appendChild(generalStats);

        // Статистика прогрессивных триггеров
        const triggerStats = document.createElement('div');
        triggerStats.className = 'stats-section';
        triggerStats.innerHTML = `
            <h4>Progressive Triggers</h4>
            <div class="triggers-grid">
                ${Object.entries(statistics.manager_stats.progressive_triggers)
                    .map(([trigger, count]) => `
                        <div class="trigger-item">
                            <span class="trigger-label">${trigger}</span>
                            <span class="trigger-value">${count}</span>
                        </div>
                    `).join('')}
            </div>
        `;
        statsContainer.appendChild(triggerStats);

        // Лучшие паттерны
        const patternsStats = document.createElement('div');
        patternsStats.className = 'stats-section';
        patternsStats.innerHTML = `
            <h4>Best Patterns</h4>
            <div class="patterns-list">
                ${statistics.strategy_stats.best_patterns
                    .map(pattern => `
                        <div class="pattern-item">
                            <span class="pattern-name">${pattern.pattern}</span>
                            <span class="pattern-rate">${(pattern.success_rate * 100).toFixed(1)}%</span>
                            <span class="pattern-uses">(${pattern.total_uses} uses)</span>
                        </div>
                    `).join('')}
            </div>
        `;
        statsContainer.appendChild(patternsStats);
    }
}
