class GameStatistics {
    constructor() {
        this.stats = {
            gamesPlayed: 0,
            wins: 0,
            fantasies: 0,
            averageScore: 0,
            winStreak: 0,
            bestScore: 0,
            cardStats: {},
            history: [],
            agentStats: {},
            timeStats: {
                averageGameDuration: 0,
                averageThinkTime: 0
            }
        };

        this.charts = {};
        this.initializeCharts();
        this.loadStats();
        this.setupAutoUpdate();
    }

    initializeCharts() {
        // График прогресса
        this.charts.progress = new Chart(
            document.getElementById('progressChart').getContext('2d'),
            {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'Win Rate',
                            data: [],
                            borderColor: '#007bff',
                            tension: 0.1,
                            fill: false
                        },
                        {
                            label: 'Fantasy Rate',
                            data: [],
                            borderColor: '#28a745',
                            tension: 0.1,
                            fill: false
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                callback: value => value + '%'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'bottom'
                        },
                        tooltip: {
                            callbacks: {
                                label: (context) => {
                                    return `${context.dataset.label}: ${context.parsed.y.toFixed(1)}%`;
                                }
                            }
                        }
                    },
                    animation: {
                        duration: 750,
                        easing: 'easeInOutQuart'
                    }
                }
            }
        );

        // График текущей игры
        this.charts.gameProgress = new Chart(
            document.getElementById('gameProgressChart').getContext('2d'),
            {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'Score Difference',
                            data: [],
                            borderColor: '#17a2b8',
                            backgroundColor: 'rgba(23, 162, 184, 0.1)',
                            tension: 0.1,
                            fill: true
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: false
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    animation: {
                        duration: 500
                    }
                }
            }
        );

        // График статистики по агентам
        this.charts.agentStats = new Chart(
            document.getElementById('agentStatsChart').getContext('2d'),
            {
                type: 'radar',
                data: {
                    labels: ['Win Rate', 'Fantasy Rate', 'Avg Score', 'Think Time', 'Royalties'],
                    datasets: []
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        r: {
                            beginAtZero: true,
                            max: 100
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            }
        );

    async loadStats() {
        try {
            const response = await fetch('/api/statistics');
            const data = await response.json();
            if (data.status === 'ok') {
                this.stats = data.statistics;
                this.updateDisplayedStats();
                this.updateCharts();
                this.updateAgentComparison();
            }
        } catch (error) {
            console.error('Failed to load statistics:', error);
            this.showError('Failed to load statistics');
        }
    }

    setupAutoUpdate() {
        // Обновление каждые 30 секунд
        setInterval(() => this.loadStats(), 30000);
    }

    updateStats(gameState) {
        // Обновляем текущую игру
        this.updateGameProgress(gameState);
        
        // Обновляем статистику карт
        this.updateCardStats(gameState);
        
        // Обновляем статистику агентов
        if (gameState.currentPlayer !== 0) {
            this.updateAgentStats(gameState);
        }
        
        // Обновляем отображение
        this.updateDisplayedStats();
        this.updateCharts();
    }

    updateGameProgress(gameState) {
        const scoreDiff = gameState.scores[0] - gameState.scores[1];
        
        this.charts.gameProgress.data.labels.push(gameState.moveNumber);
        this.charts.gameProgress.data.datasets[0].data.push(scoreDiff);
        
        // Ограничиваем количество точек на графике
        if (this.charts.gameProgress.data.labels.length > 30) {
            this.charts.gameProgress.data.labels.shift();
            this.charts.gameProgress.data.datasets[0].data.shift();
        }
        
        this.charts.gameProgress.update('none'); // Обновляем без анимации
    }

    updateCardStats(gameState) {
        if (gameState.lastMove) {
            const card = gameState.lastMove.card;
            const cardId = `${card.rank}${card.suit}`;
            
            if (!this.stats.cardStats[cardId]) {
                this.stats.cardStats[cardId] = {
                    played: 0,
                    wins: 0,
                    fantasies: 0,
                    positions: {},
                    averageScore: 0
                };
            }
            
            const cardStats = this.stats.cardStats[cardId];
            cardStats.played++;
            cardStats.positions[gameState.lastMove.position] = 
                (cardStats.positions[gameState.lastMove.position] || 0) + 1;
        }
    }

    updateAgentStats(gameState) {
        const agent = gameState.agents[gameState.currentPlayer - 1];
        if (!agent) return;

        if (!this.stats.agentStats[agent.name]) {
            this.stats.agentStats[agent.name] = {
                moves: 0,
                wins: 0,
                fantasies: 0,
                totalScore: 0,
                thinkTime: [],
                royalties: 0
            };
        }

        const agentStats = this.stats.agentStats[agent.name];
        agentStats.moves++;
        agentStats.thinkTime.push(gameState.lastMoveTime || 0);
        
        if (gameState.lastMove?.royalties) {
            agentStats.royalties += gameState.lastMove.royalties;
        }
    }

    updateDisplayedStats() {
        // Обновляем основные показатели
        document.getElementById('gamesPlayed').textContent = this.stats.gamesPlayed;
        document.getElementById('winRate').textContent = 
            `${((this.stats.wins / this.stats.gamesPlayed) * 100 || 0).toFixed(1)}%`;
        document.getElementById('fantasyRate').textContent = 
            `${((this.stats.fantasies / this.stats.gamesPlayed) * 100 || 0).toFixed(1)}%`;

        // Обновляем дополнительную статистику
        if (document.getElementById('bestScore')) {
            document.getElementById('bestScore').textContent = this.stats.bestScore;
        }
        if (document.getElementById('winStreak')) {
            document.getElementById('winStreak').textContent = this.stats.winStreak;
        }
        if (document.getElementById('averageScore')) {
            document.getElementById('averageScore').textContent = 
                this.stats.averageScore.toFixed(1);
        }

        // Обновляем временную статистику
        if (document.getElementById('averageGameTime')) {
            document.getElementById('averageGameTime').textContent = 
                this.formatTime(this.stats.timeStats.averageGameDuration);
        }
        if (document.getElementById('averageThinkTime')) {
            document.getElementById('averageThinkTime').textContent = 
                `${this.stats.timeStats.averageThinkTime.toFixed(1)}s`;
        }
    }

    updateCharts() {
        // Обновляем график прогресса
        const recentGames = this.stats.history.slice(-50);
        const winRates = this.calculateMovingAverage(
            recentGames.map(game => game.result.winner === 0 ? 100 : 0)
        );
        const fantasyRates = this.calculateMovingAverage(
            recentGames.map(game => game.result.fantasyAchieved ? 100 : 0)
        );

        this.charts.progress.data.labels = Array.from(
            {length: winRates.length}, 
            (_, i) => `Game ${this.stats.gamesPlayed - winRates.length + i + 1}`
        );
        this.charts.progress.data.datasets[0].data = winRates;
        this.charts.progress.data.datasets[1].data = fantasyRates;
        this.charts.progress.update();

        // Обновляем статистику агентов
        this.updateAgentComparison();
    }

    updateAgentComparison() {
        const agentNames = Object.keys(this.stats.agentStats);
        const colors = ['#007bff', '#28a745', '#dc3545', '#ffc107'];

        this.charts.agentStats.data.datasets = agentNames.map((name, index) => {
            const stats = this.stats.agentStats[name];
            const winRate = (stats.wins / stats.moves) * 100 || 0;
            const fantasyRate = (stats.fantasies / stats.moves) * 100 || 0;
            const avgScore = stats.totalScore / stats.moves || 0;
            const avgThinkTime = stats.thinkTime.reduce((a, b) => a + b, 0) / stats.thinkTime.length || 0;
            const avgRoyalties = stats.royalties / stats.moves || 0;

            return {
                label: name.replace('Agent', ''),
                data: [winRate, fantasyRate, avgScore, avgThinkTime, avgRoyalties],
                borderColor: colors[index % colors.length],
                backgroundColor: `${colors[index % colors.length]}40`
            };
        });

        this.charts.agentStats.update();
    }

    calculateMovingAverage(data, windowSize = 10) {
        const result = [];
        for (let i = 0; i < data.length; i++) {
            const start = Math.max(0, i - windowSize + 1);
            const window = data.slice(start, i + 1);
            result.push(window.reduce((a, b) => a + b, 0) / window.length);
        }
        return result;
    }

    saveGameResult(result) {
        this.stats.gamesPlayed++;
        if (result.winner === 0) {
            this.stats.wins++;
            this.stats.winStreak++;
        } else {
            this.stats.winStreak = 0;
        }

        if (result.fantasyAchieved) {
            this.stats.fantasies++;
        }

        this.stats.averageScore = 
            (this.stats.averageScore * (this.stats.gamesPlayed - 1) + result.playerScore) / 
            this.stats.gamesPlayed;

        if (result.playerScore > this.stats.bestScore) {
            this.stats.bestScore = result.playerScore;
            this.showAchievement('New Best Score!');
        }

        this.stats.history.push({
            timestamp: Date.now(),
            result: result
        });

        this.updateCharts();
        this.saveStats();
    }

    async saveStats() {
        try {
            await fetch('/api/statistics', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(this.stats)
            });
        } catch (error) {
            console.error('Failed to save statistics:', error);
        }
    }

    showAchievement(message) {
        const achievement = document.createElement('div');
        achievement.className = 'achievement';
        achievement.innerHTML = `
            <div class="achievement-content">
                <i class="fas fa-trophy"></i>
                <span>${message}</span>
            </div>
        `;

        document.body.appendChild(achievement);

        setTimeout(() => {
            achievement.classList.add('show');
            setTimeout(() => {
                achievement.classList.remove('show');
                setTimeout(() => achievement.remove(), 300);
            }, 3000);
        }, 100);
    }

    showError(message) {
        const error = document.createElement('div');
        error.className = 'error-toast';
        error.textContent = message;
        
        document.body.appendChild(error);
        
        setTimeout(() => {
            error.classList.add('fade-out');
            setTimeout(() => error.remove(), 300);
        }, 3000);
    }

    formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    exportStats() {
        const exportData = {
            timestamp: Date.now(),
            stats: this.stats,
            analysis: this.generateAnalysis()
        };

        const blob = new Blob([JSON.stringify(exportData, null, 2)], 
            {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `ofc_stats_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    generateAnalysis() {
        return {
            overall: {
                totalGames: this.stats.gamesPlayed,
                winRate: this.stats.wins / this.stats.gamesPlayed,
                fantasyRate: this.stats.fantasies / this.stats.gamesPlayed,
                averageScore: this.stats.averageScore,
                bestScore: this.stats.bestScore,
                currentStreak: this.stats.winStreak
            },
            agents: this.stats.agentStats,
            trends: this.analyzeTrends(),
            recommendations: this.generateRecommendations()
        };
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.gameStats = new GameStatistics();
});
