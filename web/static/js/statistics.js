// web/static/js/statistics.js

class GameStatistics {
    constructor() {
        this.statsContainer = document.getElementById('statisticsPanel');
        this.recommendationsContainer = document.getElementById('recommendationsPanel');
        this.initialize();
    }

    initialize() {
        this.createStatisticsPanel();
        this.createRecommendationsPanel();
        this.startAutoUpdate();
    }

    createStatisticsPanel() {
        this.statsContainer.innerHTML = `
            <div class="stats-section">
                <h3>Game Statistics</h3>
                <div class="stats-grid">
                    <div class="stat-item">
                        <span class="stat-label">Games Played</span>
                        <span class="stat-value" id="gamesPlayed">0</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Win Rate</span>
                        <span class="stat-value" id="winRate">0%</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Fantasy Rate</span>
                        <span class="stat-value" id="fantasyRate">0%</span>
                    </div>
                </div>
            </div>
            <div class="stats-section">
                <h3>Card Statistics</h3>
                <div id="cardStats" class="card-stats-container"></div>
            </div>
        `;
    }

    createRecommendationsPanel() {
        this.recommendationsContainer.innerHTML = `
            <div class="recommendations-section">
                <h3>Move Recommendations</h3>
                <div id="moveRecommendations" class="recommendations-grid"></div>
            </div>
        `;
    }

    startAutoUpdate() {
        setInterval(() => this.updateStatistics(), 5000);
    }

    async updateStatistics() {
        try {
            const response = await fetch('/api/game/statistics');
            const data = await response.json();
            
            if (data.status === 'ok') {
                this.updateStatisticsDisplay(data.statistics);
                this.updateRecommendations(data.statistics.recommendations);
            }
        } catch (error) {
            console.error('Error updating statistics:', error);
        }
    }

    updateStatisticsDisplay(statistics) {
        // Обновляем основные показатели
        document.getElementById('gamesPlayed').textContent = 
            statistics.session_stats.games_played;
        document.getElementById('winRate').textContent = 
            `${(statistics.session_stats.win_rate * 100).toFixed(1)}%`;
        document.getElementById('fantasyRate').textContent = 
            `${(statistics.session_stats.fantasy_rate * 100).toFixed(1)}%`;

        // Обновляем статистику карт
        this.updateCardStatistics(statistics.card_stats);
    }

    updateCardStatistics(cardStats) {
        const container = document.getElementById('cardStats');
        container.innerHTML = '';

        // Добавляем статистику по самым успешным картам
        cardStats.most_successful_cards.forEach(cardStat => {
            const cardElement = document.createElement('div');
            cardElement.className = 'card-stat-item';
            cardElement.innerHTML = `
                <div class="card ${cardStat.card.suit === 'h' || cardStat.card.suit === 'd' ? 'red' : 'black'}">
                    ${cardStat.card.rank}${cardStat.card.suit}
                </div>
                <div class="card-stat-details">
                    <div>Success: ${(cardStat.success_rate * 100).toFixed(1)}%</div>
                    <div>Used: ${cardStat.appearances} times</div>
                </div>
            `;
            container.appendChild(cardElement);
        });
    }

    updateRecommendations(recommendations) {
        const container = document.getElementById('moveRecommendations');
        container.innerHTML = '';

        Object.entries(recommendations).forEach(([street, moves]) => {
            const streetElement = document.createElement('div');
            streetElement.className = 'street-recommendations';
            streetElement.innerHTML = `
                <h4>${street}</h4>
                <div class="recommended-moves">
                    ${moves.map(move => this.createMoveElement(move)).join('')}
                </div>
            `;
            container.appendChild(streetElement);
        });
    }

    createMoveElement(move) {
        const [card, score, reasoning] = move;
        return `
            <div class="recommended-move">
                <div class="card ${card.suit === 'h' || card.suit === 'd' ? 'red' : 'black'}">
                    ${card.rank}${card.suit}
                </div>
                <div class="move-details">
                    <div class="move-score">Score: ${(score * 100).toFixed(1)}%</div>
                    <div class="move-reasoning">${reasoning}</div>
                </div>
            </div>
        `;
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.gameStatistics = new GameStatistics();
});
