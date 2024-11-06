// web/static/js/statistics.js

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
            history: []
        };
        
        this.initializeCharts();
        this.loadStats();
    }

    initializeCharts() {
        // График прогресса
        this.progressChart = new Chart(
            document.getElementById('progressChart').getContext('2d'),
            {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Win Rate',
                        data: [],
                        borderColor: '#007bff',
                        tension: 0.1
                    }, {
                        label: 'Fantasy Rate',
                        data: [],
                        borderColor: '#28a745',
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

        // График текущей игры
        this.gameProgressChart = new Chart(
            document.getElementById('gameProgressChart').getContext('2d'),
            {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Score Difference',
                        data: [],
                        borderColor: '#17a2b8',
                        tension: 0.1,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: false
                        }
                    },
                    animation: {
                        duration: 500
                    }
                }
            }
        );
    }

    async loadStats() {
        try {
            const response = await fetch('/api/statistics');
            const data = await response.json();
            if (data.status === 'ok') {
                this.stats = data.statistics;
                this.updateDisplayedStats();
                this.updateCharts();
            }
        } catch (error) {
            console.error('Failed to load statistics:', error);
        }
    }

    updateStats(gameState) {
        // Обновляем текущую игру
        this.updateGameProgress(gameState);
        
        // Обновляем статистику карт
        this.updateCardStats(gameState);
        
        // Обновляем отображение
        this.updateDisplayedStats();
    }

    updateGameProgress(gameState) {
        const scoreDiff = gameState.scores[0] - gameState.scores[1];
        
        this.gameProgressChart.data.labels.push(gameState.moveNumber);
        this.gameProgressChart.data.datasets[0].data.push(scoreDiff);
        
        // Ограничиваем количество точек на графике
        if (this.gameProgressChart.data.labels.length > 30) {
            this.gameProgressChart.data.labels.shift();
            this.gameProgressChart.data.datasets[0].data.shift();
        }
        
        this.gameProgressChart.update();
    }

    updateCardStats(gameState) {
        // Обновляем статистику по каждой сыгранной карте
        if (gameState.lastMove) {
            const card = gameState.lastMove.card;
            if (!this.stats.cardStats[card.id]) {
                this.stats.cardStats[card.id] = {
                    played: 0,
                    wins: 0,
                    fantasies: 0,
                    positions: {}
                };
            }
            
            this.stats.cardStats[card.id].played++;
            this.stats.cardStats[card.id].positions[gameState.lastMove.position] = 
                (this.stats.cardStats[card.id].positions[gameState.lastMove.position] || 0) + 1;
        }
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
        }

        this.stats.history.push({
            timestamp: Date.now(),
            result: result
        });

        this.updateCharts();
        this.saveStats();
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
    }

    updateCharts() {
        // Обновляем график прогресса
        const recentGames = this.stats.history.slice(-50);
        const winRates = this.calculateMovingAverage(
            recentGames.map(game => game.result.winner === 0 ? 1 : 0)
        );
        const fantasyRates = this.calculateMovingAverage(
            recentGames.map(game => game.result.fantasyAchieved ? 1 : 0)
        );

        this.progressChart.data.labels = 
            Array.from({length: winRates.length}, (_, i) => i + 1);
        this.progressChart.data.datasets[0].data = winRates;
        this.progressChart.data.datasets[1].data = fantasyRates;
        this.progressChart.update();
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

    generateReport() {
        return {
            overall: {
                gamesPlayed: this.stats.gamesPlayed,
                winRate: this.stats.wins / this.stats.gamesPlayed,
                fantasyRate: this.stats.fantasies / this.stats.gamesPlayed,
                averageScore: this.stats.averageScore,
                bestScore: this.stats.bestScore,
                currentStreak: this.stats.winStreak
            },
            cards: this.analyzeCardStats(),
            recent: this.analyzeRecentGames(),
            trends: this.analyzeTrends()
        };
    }

    analyzeCardStats() {
        const cardStats = {};
        for (const [cardId, stats] of Object.entries(this.stats.cardStats)) {
            cardStats[cardId] = {
                playRate: stats.played / this.stats.gamesPlayed,
                winRate: stats.wins / stats.played,
                fantasyRate: stats.fantasies / stats.played,
                bestPositions: this.findBestPositions(stats.positions)
            };
        }
        return cardStats;
    }

    findBestPositions(positions) {
        return Object.entries(positions)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 3)
            .map(([pos, count]) => ({
                position: pos,
                frequency: count
            }));
    }

    analyzeRecentGames() {
        const recent = this.stats.history.slice(-20);
        return {
            winRate: recent.filter(g => g.result.winner === 0).length / recent.length,
            averageScore: recent.reduce((sum, g) => sum + g.result.playerScore, 0) / recent.length,
            fantasyRate: recent.filter(g => g.result.fantasyAchieved).length / recent.length,
            commonPatterns: this.findCommonPatterns(recent)
        };
    }

    findCommonPatterns(games) {
        const patterns = {};
        games.forEach(game => {
            game.result.moves.forEach((move, index) => {
                const key = `${move.card.rank}${move.card.suit}_${move.position}`;
                if (!patterns[key]) {
                    patterns[key] = {
                        count: 0,
                        success: 0,
                        averagePosition: index
                    };
                }
                patterns[key].count++;
                if (game.result.winner === 0) {
                    patterns[key].success++;
                }
                patterns[key].averagePosition = 
                    (patterns[key].averagePosition * (patterns[key].count - 1) + index) / 
                    patterns[key].count;
            });
        });

        return Object.entries(patterns)
            .filter(([, stats]) => stats.count >= 3)
            .sort(([, a], [, b]) => (b.success / b.count) - (a.success / a.count))
            .slice(0, 5)
            .map(([pattern, stats]) => ({
                pattern,
                successRate: stats.success / stats.count,
                frequency: stats.count / games.length,
                averagePosition: Math.round(stats.averagePosition)
            }));
    }

    analyzeTrends() {
        const windowSize = 20;
        const history = this.stats.history;
        
        const trends = {
            winRate: this.calculateTrend(
                history.map(g => g.result.winner === 0 ? 1 : 0),
                windowSize
            ),
            scoreProgress: this.calculateTrend(
                history.map(g => g.result.playerScore),
                windowSize
            ),
            fantasySuccess: this.calculateTrend(
                history.map(g => g.result.fantasyAchieved ? 1 : 0),
                windowSize
            )
        };

        return {
            ...trends,
            improvement: this.calculateImprovement(trends)
        };
    }

    calculateTrend(data, windowSize) {
        const averages = this.calculateMovingAverage(data, windowSize);
        const recentAvg = averages.slice(-10);
        const slope = this.calculateSlope(recentAvg);
        
        return {
            current: averages[averages.length - 1],
            trend: slope > 0 ? 'improving' : slope < 0 ? 'declining' : 'stable',
            changeRate: Math.abs(slope)
        };
    }

    calculateSlope(data) {
        const n = data.length;
        if (n < 2) return 0;
        
        const xMean = (n - 1) / 2;
        const yMean = data.reduce((a, b) => a + b, 0) / n;
        
        let numerator = 0;
        let denominator = 0;
        
        data.forEach((y, x) => {
            numerator += (x - xMean) * (y - yMean);
            denominator += Math.pow(x - xMean, 2);
        });
        
        return denominator ? numerator / denominator : 0;
    }

    calculateImprovement(trends) {
        const weights = {
            winRate: 0.5,
            scoreProgress: 0.3,
            fantasySuccess: 0.2
        };

        const weightedImprovement = 
            (trends.winRate.changeRate * weights.winRate) +
            (trends.scoreProgress.changeRate * weights.scoreProgress) +
            (trends.fantasySuccess.changeRate * weights.fantasySuccess);

        return {
            overall: weightedImprovement,
            rating: this.getImprovementRating(weightedImprovement),
            recommendations: this.generateRecommendations(trends)
        };
    }

    getImprovementRating(improvement) {
        if (improvement > 0.1) return 'Excellent';
        if (improvement > 0.05) return 'Good';
        if (improvement > 0) return 'Steady';
        if (improvement > -0.05) return 'Needs Work';
        return 'Needs Significant Improvement';
    }

    generateRecommendations(trends) {
        const recommendations = [];

        if (trends.winRate.trend === 'declining') {
            recommendations.push({
                area: 'Strategy',
                suggestion: 'Focus on basic strategy and card placement',
                priority: 'High'
            });
        }

        if (trends.fantasySuccess.current < 0.2) {
            recommendations.push({
                area: 'Fantasy',
                suggestion: 'Practice fantasy setups in training mode',
                priority: 'Medium'
            });
        }

        if (trends.scoreProgress.trend === 'stable') {
            recommendations.push({
                area: 'Scoring',
                suggestion: 'Try more aggressive royalty combinations',
                priority: 'Medium'
            });
        }

        return recommendations;
    }

    exportStats() {
        const exportData = {
            timestamp: Date.now(),
            stats: this.stats,
            analysis: this.generateReport()
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
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.gameStats = new GameStatistics();
});
