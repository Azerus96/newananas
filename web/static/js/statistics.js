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
            foulsRate: 0,
            scoopsRate: 0,
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
                        },
                        {
                            label: 'Fouls Rate',
                            data: [],
                            borderColor: '#dc3545',
                            tension: 0.1,
                            fill: false
                        },
                        {
                            label: 'Scoops Rate',
                            data: [],
                            borderColor: '#ffc107',
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
                    labels: [
                        'Win Rate',
                        'Fantasy Rate',
                        'Avg Score',
                        'Think Time',
                        'Royalties',
                        'Fouls Rate',
                        'Scoops Rate'
                    ],
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

        // График распределения комбинаций
        this.charts.combinations = new Chart(
            document.getElementById('combinationsChart').getContext('2d'),
            {
                type: 'bar',
                data: {
                    labels: [
                        'High Card',
                        'Pair',
                        'Two Pair',
                        'Three of a Kind',
                        'Straight',
                        'Flush',
                        'Full House',
                        'Four of a Kind',
                        'Straight Flush',
                        'Royal Flush'
                    ],
                    datasets: [
                        {
                            label: 'Top Row',
                            data: [],
                            backgroundColor: 'rgba(0, 123, 255, 0.5)'
                        },
                        {
                            label: 'Middle Row',
                            data: [],
                            backgroundColor: 'rgba(40, 167, 69, 0.5)'
                        },
                        {
                            label: 'Bottom Row',
                            data: [],
                            backgroundColor: 'rgba(220, 53, 69, 0.5)'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Frequency'
                            }
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
    }

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
        
        if (this.charts.gameProgress.data.labels.length > 30) {
            this.charts.gameProgress.data.labels.shift();
            this.charts.gameProgress.data.datasets[0].data.shift();
        }
        this.charts.gameProgress.update('none');
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
                fouls: 0,
                scoops: 0,
                positions: {},
                averageScore: 0
            };
        }
        
        const cardStats = this.stats.cardStats[cardId];
        cardStats.played++;
        if (gameState.lastMove.isFoul) cardStats.fouls++;
        if (gameState.lastMove.isScoop) cardStats.scoops++;
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
            fouls: 0,
            scoops: 0,
            totalScore: 0,
            thinkTime: [],
            royalties: 0
        };
    }

    const agentStats = this.stats.agentStats[agent.name];
    agentStats.moves++;
    agentStats.thinkTime.push(gameState.lastMoveTime || 0);
    
    if (gameState.lastMove) {
        if (gameState.lastMove.royalties) {
            agentStats.royalties += gameState.lastMove.royalties;
        }
        if (gameState.lastMove.isFoul) agentStats.fouls++;
        if (gameState.lastMove.isScoop) agentStats.scoops++;
    }
}

updateDisplayedStats() {
    // Основные показатели
    document.getElementById('gamesPlayed').textContent = this.stats.gamesPlayed;
    document.getElementById('winRate').textContent = 
        `${((this.stats.wins / this.stats.gamesPlayed) * 100 || 0).toFixed(1)}%`;
    document.getElementById('fantasyRate').textContent = 
        `${((this.stats.fantasies / this.stats.gamesPlayed) * 100 || 0).toFixed(1)}%`;
    document.getElementById('foulsRate').textContent = 
        `${((this.stats.fouls / this.stats.totalMoves) * 100 || 0).toFixed(1)}%`;
    document.getElementById('scoopsRate').textContent = 
        `${((this.stats.scoops / this.stats.totalMoves) * 100 || 0).toFixed(1)}%`;

    // Дополнительная статистика
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

    // Временная статистика
    if (document.getElementById('averageGameTime')) {
        document.getElementById('averageGameTime').textContent = 
            this.formatTime(this.stats.timeStats.averageGameDuration);
    }
    if (document.getElementById('averageThinkTime')) {
        document.getElementById('averageThinkTime').textContent = 
            `${this.stats.timeStats.averageThinkTime.toFixed(1)}s`;
    }

    // Анимация обновления
    document.querySelectorAll('.stat-value').forEach(el => {
        el.classList.add('updated');
        setTimeout(() => el.classList.remove('updated'), 300);
    });
}

updateCharts() {
    // График прогресса
    const recentGames = this.stats.history.slice(-50);
    const winRates = this.calculateMovingAverage(
        recentGames.map(game => game.result.winner === 0 ? 100 : 0)
    );
    const fantasyRates = this.calculateMovingAverage(
        recentGames.map(game => game.result.fantasyAchieved ? 100 : 0)
    );
    const foulsRates = this.calculateMovingAverage(
        recentGames.map(game => (game.fouls / game.totalMoves) * 100 || 0)
    );
    const scoopsRates = this.calculateMovingAverage(
        recentGames.map(game => (game.scoops / game.totalMoves) * 100 || 0)
    );

    this.charts.progress.data.labels = Array.from(
        {length: winRates.length}, 
        (_, i) => `Game ${this.stats.gamesPlayed - winRates.length + i + 1}`
    );
    this.charts.progress.data.datasets[0].data = winRates;
    this.charts.progress.data.datasets[1].data = fantasyRates;
    this.charts.progress.data.datasets[2].data = foulsRates;
    this.charts.progress.data.datasets[3].data = scoopsRates;
    this.charts.progress.update();

    // Обновляем остальные графики
    this.updateCombinationsChart();
    this.updateAgentComparison();
}

updateCombinationsChart() {
    const combinationStats = this.calculateCombinationStats();
    this.charts.combinations.data.datasets.forEach((dataset, index) => {
        dataset.data = combinationStats[index];
    });
    this.charts.combinations.update();
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
        const foulsRate = (stats.fouls / stats.moves) * 100 || 0;
        const scoopsRate = (stats.scoops / stats.moves) * 100 || 0;

        return {
            label: name.replace('Agent', ''),
            data: [
                winRate,
                fantasyRate,
                avgScore,
                avgThinkTime,
                avgRoyalties,
                foulsRate,
                scoopsRate
            ],
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

calculateCombinationStats() {
    const stats = [[], [], []]; // Top, Middle, Bottom rows
    const combinations = [
        'highCard', 'pair', 'twoPair', 'threeOfKind',
        'straight', 'flush', 'fullHouse', 'fourOfKind',
        'straightFlush', 'royalFlush'
    ];

    combinations.forEach(combo => {
        [0, 1, 2].forEach(row => {
            const count = this.stats.history.reduce((acc, game) => {
                return acc + (game.combinations[row] === combo ? 1 : 0);
            }, 0);
            stats[row].push(count);
        });
    });

    return stats;
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

    // Обновляем статистику фолов и скупов
    this.stats.fouls += result.fouls || 0;
    this.stats.scoops += result.scoops || 0;
    this.stats.totalMoves += result.totalMoves || 0;

    this.stats.history.push({
        timestamp: Date.now(),
        result: result,
        fouls: result.fouls || 0,
        scoops: result.scoops || 0,
        totalMoves: result.totalMoves || 0,
        combinations: result.combinations || {}
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
            foulsRate: this.stats.fouls / this.stats.totalMoves,
            scoopsRate: this.stats.scoops / this.stats.totalMoves,
            averageScore: this.stats.averageScore,
            bestScore: this.stats.bestScore,
            currentStreak: this.stats.winStreak
        },
        agents: this.stats.agentStats,
        trends: this.analyzeTrends(),
        recommendations: this.generateRecommendations()
    };
}

analyzeTrends() {
    const recentGames = this.stats.history.slice(-20);
    return {
        recentWinRate: this.calculateMovingAverage(
            recentGames.map(game => game.result.winner === 0 ? 1 : 0)
        ).pop(),
        recentFoulsRate: this.calculateMovingAverage(
            recentGames.map(game => game.fouls / game.totalMoves)
        ).pop(),
        recentScoopsRate: this.calculateMovingAverage(
            recentGames.map(game => game.scoops / game.totalMoves)
        ).pop(),
        improvement: this.calculateImprovement(recentGames)
    };
}

generateRecommendations() {
    const trends = this.analyzeTrends();
    const recommendations = [];

    if (trends.recentFoulsRate > 0.2) {
        recommendations.push('Try to focus more on maintaining hand hierarchy');
    }
    if (trends.recentScoopsRate < 0.1) {
        recommendations.push('Look for opportunities to win all three rows');
    }
    if (trends.recentWinRate < 0.4) {
        recommendations.push('Consider reviewing the tutorial and basic strategies');
    }

    return recommendations;
}

calculateImprovement(recentGames) {
    if (recentGames.length < 10) return null;

    const firstHalf = recentGames.slice(0, Math.floor(recentGames.length / 2));
    const secondHalf = recentGames.slice(Math.floor(recentGames.length / 2));

    return {
        winRate: this.calculateAverageImprovement(firstHalf, secondHalf, 'winner'),
        foulsRate: this.calculateAverageImprovement(firstHalf, secondHalf, 'fouls'),
        scoopsRate: this.calculateAverageImprovement(firstHalf, secondHalf, 'scoops')
    };
}

calculateAverageImprovement(firstHalf, secondHalf, metric) {
    const firstAvg = firstHalf.reduce((acc, game) => acc + (game[metric] || 0), 0) / firstHalf.length;
    const secondAvg = secondHalf.reduce((acc, game) => acc + (game[metric] || 0), 0) / secondHalf.length;
    return ((secondAvg - firstAvg) / firstAvg) * 100;
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.gameStats = new GameStatistics();

    // Добавляем обработчики для экспорта статистики
    document.getElementById('exportStats')?.addEventListener('click', () => {
        window.gameStats.exportStats();
    });

    // Добавляем обработчики для фильтрации статистики
    document.getElementById('statsFilter')?.addEventListener('change', (e) => {
        const period = e.target.value;
        window.gameStats.filterStatsByPeriod(period);
    });

    // Добавляем обработчики для переключения видов статистики
    document.querySelectorAll('.stats-view-toggle')?.forEach(button => {
        button.addEventListener('click', (e) => {
            const view = e.target.dataset.view;
            window.gameStats.switchStatsView(view);
        });
    });
});

// Дополнительные утилиты для работы со статистикой
class StatisticsUtils {
    static calculatePercentage(value, total) {
        return total > 0 ? (value / total) * 100 : 0;
    }

    static formatPercentage(value) {
        return `${value.toFixed(1)}%`;
    }

    static calculateStreakData(history) {
        let currentStreak = 0;
        let bestStreak = 0;
        let streakType = null;

        history.forEach(game => {
            if (game.result.winner === 0) {
                if (streakType === 'win' || streakType === null) {
                    currentStreak++;
                    streakType = 'win';
                } else {
                    currentStreak = 1;
                    streakType = 'win';
                }
            } else {
                if (streakType === 'loss' || streakType === null) {
                    currentStreak++;
                    streakType = 'loss';
                } else {
                    currentStreak = 1;
                    streakType = 'loss';
                }
            }

            if (streakType === 'win' && currentStreak > bestStreak) {
                bestStreak = currentStreak;
            }
        });

        return {
            currentStreak,
            bestStreak,
            streakType
        };
    }

    static generatePerformanceReport(stats) {
        const report = {
            overall: {
                rating: this.calculateOverallRating(stats),
                strengths: [],
                weaknesses: [],
                recommendations: []
            },
            detailed: {
                handBuilding: this.analyzeHandBuilding(stats),
                fantasyPlay: this.analyzeFantasyPlay(stats),
                consistency: this.analyzeConsistency(stats)
            }
        };

        this.generateRecommendations(report);
        return report;
    }

    static calculateOverallRating(stats) {
        const weights = {
            winRate: 0.4,
            foulsRate: -0.2,
            scoopsRate: 0.2,
            fantasyRate: 0.2
        };

        const winRate = this.calculatePercentage(stats.wins, stats.gamesPlayed);
        const foulsRate = this.calculatePercentage(stats.fouls, stats.totalMoves);
        const scoopsRate = this.calculatePercentage(stats.scoops, stats.totalMoves);
        const fantasyRate = this.calculatePercentage(stats.fantasies, stats.gamesPlayed);

        return (
            winRate * weights.winRate +
            (100 - foulsRate) * weights.foulsRate +
            scoopsRate * weights.scoopsRate +
            fantasyRate * weights.fantasyRate
        );
    }

    static analyzeHandBuilding(stats) {
        return {
            foulsRate: this.calculatePercentage(stats.fouls, stats.totalMoves),
            scoopsRate: this.calculatePercentage(stats.scoops, stats.totalMoves),
            averageScore: stats.averageScore,
            efficiency: this.calculateHandBuildingEfficiency(stats)
        };
    }

    static analyzeFantasyPlay(stats) {
        return {
            fantasyRate: this.calculatePercentage(stats.fantasies, stats.gamesPlayed),
            successRate: this.calculatePercentage(stats.successfulFantasies, stats.fantasies),
            averageCards: stats.averageFantasyCards,
            progressiveRate: this.calculatePercentage(stats.progressiveFantasies, stats.fantasies)
        };
    }

    static analyzeConsistency(stats) {
        const recentGames = stats.history.slice(-20);
        const standardDeviation = this.calculateStandardDeviation(
            recentGames.map(game => game.result.playerScore)
        );

        return {
            scoreDeviation: standardDeviation,
            winStreak: stats.winStreak,
            consistency: 100 - (standardDeviation / stats.averageScore) * 100
        };
    }

    static calculateStandardDeviation(values) {
        const avg = values.reduce((a, b) => a + b) / values.length;
        const squareDiffs = values.map(value => Math.pow(value - avg, 2));
        const avgSquareDiff = squareDiffs.reduce((a, b) => a + b) / squareDiffs.length;
        return Math.sqrt(avgSquareDiff);
    }

    static calculateHandBuildingEfficiency(stats) {
        const maxPossibleScore = stats.gamesPlayed * 100; // Предполагаемый максимум
        return (stats.totalScore / maxPossibleScore) * 100;
    }

    static generateRecommendations(report) {
        const { overall, detailed } = report;

        if (detailed.handBuilding.foulsRate > 20) {
            overall.weaknesses.push('High foul rate');
            overall.recommendations.push('Focus on maintaining proper hand hierarchy');
        }

        if (detailed.fantasyPlay.successRate < 50) {
            overall.weaknesses.push('Low fantasy success rate');
            overall.recommendations.push('Practice fantasy situations in training mode');
        }

        if (detailed.handBuilding.scoopsRate < 10) {
            overall.weaknesses.push('Low scoop rate');
            overall.recommendations.push('Look for more opportunities to win all three rows');
        }

        if (detailed.consistency.consistency < 70) {
            overall.weaknesses.push('Inconsistent play');
            overall.recommendations.push('Work on maintaining consistent performance');
        }

        // Определение сильных сторон
        if (detailed.handBuilding.foulsRate < 10) {
            overall.strengths.push('Excellent hand building discipline');
        }

        if (detailed.fantasyPlay.successRate > 70) {
            overall.strengths.push('Strong fantasy play');
        }

        if (detailed.handBuilding.scoopsRate > 20) {
            overall.strengths.push('Good at finding scoop opportunities');
        }

        if (detailed.consistency.consistency > 85) {
            overall.strengths.push('Very consistent player');
        }
    }
}
