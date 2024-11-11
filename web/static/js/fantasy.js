class FantasyManager {
    constructor() {
        // Проверка готовности DOM
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initialize());
        } else {
            this.initialize();
        }

        this.state = {
            active: false,
            mode: 'normal',
            cardsCount: 0,
            consecutiveFantasies: 0,
            progressiveBonus: null,
            foulsRate: 0,
            scoopsRate: 0,
            totalAttempts: 0,
            successfulAttempts: 0,
            lastUpdate: Date.now(),
            patterns: new Map(),
            triggers: new Set(),
            history: []
        };

        this.eventHandlers = new Map();
        this.animations = new Map();
    }

    async initialize() {
        try {
            await this.initializeElements();
            this.setupEventListeners();
            this.loadSettings();
            await this.loadPatterns();
            this.startAutoUpdate();
            this.setupAnimations();
            this.initializeAnalytics();
        } catch (error) {
            console.error('Fantasy initialization failed:', error);
            this.handleInitializationError(error);
        }
    }

    async initializeElements() {
        this.elements = {
            container: await this.waitForElement('fantasyStatus'),
            mode: await this.waitForElement('fantasyMode'),
            cards: await this.waitForElement('fantasyCards'),
            consecutive: await this.waitForElement('consecutiveFantasies'),
            successRate: await this.waitForElement('fantasySuccessRate'),
            foulsRate: await this.waitForElement('foulsRate'),
            scoopsRate: await this.waitForElement('scoopsRate'),
            progressiveBonus: await this.waitForElement('progressiveBonus'),
            patternsList: await this.waitForElement('patternsList'),
            triggersList: await this.waitForElement('triggersList')
        };

        this.validateElements();
    }

    waitForElement(id) {
        return new Promise((resolve, reject) => {
            const element = document.getElementById(id);
            if (element) {
                resolve(element);
                return;
            }

            const observer = new MutationObserver((mutations, obs) => {
                const element = document.getElementById(id);
                if (element) {
                    obs.disconnect();
                    resolve(element);
                }
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true
            });

            // Таймаут для предотвращения бесконечного ожидания
            setTimeout(() => {
                observer.disconnect();
                reject(new Error(`Element ${id} not found`));
            }, 5000);
        });
    }

    validateElements() {
        const requiredElements = ['container', 'mode', 'cards', 'consecutive'];
        const missingElements = requiredElements.filter(id => !this.elements[id]);
        
        if (missingElements.length > 0) {
            throw new Error(`Missing required elements: ${missingElements.join(', ')}`);
        }
    }

    setupEventListeners() {
        // Обработчики WebSocket
        this.addEventHandler(socket, 'fantasy_update', data => this.handleFantasyUpdate(data));
        this.addEventHandler(socket, 'statistics_update', data => this.handleStatisticsUpdate(data));

        // Обработчики UI
        if (this.elements.mode) {
            this.addEventHandler(this.elements.mode, 'change', e => this.handleModeChange(e));
        }

        // Обработчики анимации
        const animationToggle = document.getElementById('animationToggle');
        if (animationToggle) {
            this.addEventHandler(animationToggle, 'change', e => this.handleAnimationToggle(e));
        }

        // Обработчики паттернов
        if (this.elements.patternsList) {
            this.addEventHandler(this.elements.patternsList, 'click', e => this.handlePatternClick(e));
        }
    }

    addEventHandler(element, event, handler) {
        if (!element) return;

        const boundHandler = handler.bind(this);
        element.addEventListener(event, boundHandler);

        if (!this.eventHandlers.has(element)) {
            this.eventHandlers.set(element, new Map());
        }
        this.eventHandlers.get(element).set(event, boundHandler);
    }

    removeEventHandler(element, event) {
        if (!this.eventHandlers.has(element)) return;

        const handlers = this.eventHandlers.get(element);
        const handler = handlers.get(event);
        
        if (handler) {
            element.removeEventListener(event, handler);
            handlers.delete(event);
        }

        if (handlers.size === 0) {
            this.eventHandlers.delete(element);
        }
    }

    async loadPatterns() {
        try {
            const response = await fetch('/api/fantasy/patterns');
            const data = await response.json();
            
            if (data.status === 'ok') {
                this.patterns = new Map(Object.entries(data.patterns));
                this.updatePatternsDisplay();
            }
        } catch (error) {
            console.error('Failed to load fantasy patterns:', error);
        }
    }

    startAutoUpdate() {
        // Очищаем предыдущий интервал, если он существует
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }

        this.updateInterval = setInterval(() => this.requestUpdate(), 2000);
    }

    setupAnimations() {
        this.animations.set('fantasy', {
            keyframes: [
                { transform: 'scale(1)', opacity: '1' },
                { transform: 'scale(1.1)', opacity: '0.8' },
                { transform: 'scale(1)', opacity: '1' }
            ],
            options: {
                duration: 500,
                iterations: 1
            }
        });

        this.animations.set('bonus', {
            keyframes: [
                { transform: 'translateY(0)', opacity: '1' },
                { transform: 'translateY(-10px)', opacity: '0.8' },
                { transform: 'translateY(0)', opacity: '1' }
            ],
            options: {
                duration: 300,
                iterations: 1
            }
        });
    }

    initializeAnalytics() {
        this.analytics = {
            patterns: new Map(),
            triggers: new Map(),
            timings: [],
            successRates: []
        };
    }

    async requestUpdate() {
        if (Date.now() - this.state.lastUpdate < 1000) {
            return; // Предотвращаем слишком частые обновления
        }

        try {
            const response = await fetch('/api/fantasy/status');
            const data = await response.json();
            
            if (data.status === 'ok') {
                this.updateFantasyStatus(data.fantasy_status);
                this.updateStatistics(data.statistics);
                this.state.lastUpdate = Date.now();
            }
        } catch (error) {
            console.error('Error updating fantasy status:', error);
            this.handleUpdateError(error);
        }
    }

    updateFantasyStatus(status) {
        const previousState = { ...this.state };
        this.state = { ...this.state, ...status };

        // Обновляем отображение
        this.updateStatusDisplay();

        // Проверяем изменения состояния
        if (!previousState.active && this.state.active) {
            this.handleFantasyActivation();
        } else if (previousState.active && !this.state.active) {
            this.handleFantasyDeactivation();
        }


// Проверяем изменение прогрессивного бонуса
        if (previousState.progressiveBonus !== this.state.progressiveBonus) {
            this.handleProgressiveBonusChange();
        }

        // Обновляем аналитику
        this.updateAnalytics();
    }

    updateStatusDisplay() {
        if (!this.elements.container) return;

        // Обновляем основную информацию
        this.elements.mode.textContent = this.state.mode;
        this.elements.cards.textContent = this.state.cardsCount;
        this.elements.consecutive.textContent = this.state.consecutiveFantasies;

        // Обновляем индикатор активной фантазии
        this.elements.container.classList.toggle('fantasy-active', this.state.active);

        // Обновляем прогрессивный бонус
        if (this.state.progressiveBonus) {
            this.elements.progressiveBonus.style.display = 'block';
            this.elements.progressiveBonus.querySelector('.bonus-value').textContent = 
                this.state.progressiveBonus;
        } else {
            this.elements.progressiveBonus.style.display = 'none';
        }

        // Анимируем изменения если фантазия активна
        if (this.state.active) {
            this.playFantasyAnimation();
        }
    }

    updateStatistics(statistics) {
        // Обновляем основную статистику
        if (this.elements.successRate) {
            const successRate = ((statistics.successfulAttempts / 
                statistics.totalAttempts) * 100 || 0).toFixed(1);
            this.elements.successRate.textContent = `${successRate}%`;
        }

        // Обновляем статистику фолов и скупов
        if (this.elements.foulsRate) {
            this.elements.foulsRate.textContent = 
                `${(statistics.foulsRate * 100).toFixed(1)}%`;
        }
        if (this.elements.scoopsRate) {
            this.elements.scoopsRate.textContent = 
                `${(statistics.scoopsRate * 100).toFixed(1)}%`;
        }

        // Обновляем графики если они есть
        this.updateCharts(statistics);

        // Сохраняем историю для аналитики
        this.updateAnalyticsHistory(statistics);
    }

    updateCharts(statistics) {
        if (!this.charts) return;

        if (this.charts.progress) {
            this.updateProgressChart(statistics);
        }
        if (this.charts.distribution) {
            this.updateDistributionChart(statistics);
        }
    }

    updateProgressChart(statistics) {
        const chart = this.charts.progress;
        chart.data.datasets[0].data = statistics.progressData;
        chart.update('none'); // Обновляем без анимации для производительности
    }

    updateDistributionChart(statistics) {
        const chart = this.charts.distribution;
        chart.data.datasets[0].data = statistics.distributionData;
        chart.update('none');
    }

    handleFantasyActivation() {
        // Воспроизводим звук активации если звук включен
        if (document.body.classList.contains('sound-enabled')) {
            this.playSound('fantasyActivate');
        }

        // Показываем уведомление
        this.showNotification('Fantasy Mode Activated!', 'success');

        // Анимируем активацию
        this.playFantasyAnimation();

        // Обновляем триггеры
        this.updateTriggersList();

        // Отправляем аналитику
        this.trackFantasyActivation();
    }

    handleFantasyDeactivation() {
        // Обновляем статистику
        this.updateDeactivationStatistics();

        // Показываем результаты
        this.showFantasyResults();

        // Сбрасываем состояние UI
        this.resetFantasyUI();
    }

    handleProgressiveBonusChange() {
        if (!this.state.progressiveBonus) return;

        // Анимируем изменение бонуса
        this.playBonusAnimation();

        // Обновляем отображение
        this.updateBonusDisplay();

        // Отправляем аналитику
        this.trackBonusChange();
    }

    playFantasyAnimation() {
        if (!this.animations.has('fantasy') || 
            document.body.classList.contains('animations-disabled')) {
            return;
        }

        const animation = this.animations.get('fantasy');
        this.elements.container.animate(
            animation.keyframes,
            animation.options
        );
    }

    playBonusAnimation() {
        if (!this.animations.has('bonus') || 
            document.body.classList.contains('animations-disabled')) {
            return;
        }

        const animation = this.animations.get('bonus');
        this.elements.progressiveBonus.animate(
            animation.keyframes,
            animation.options
        );
    }

    playSound(soundName) {
        // Проверяем поддержку Web Audio API
        if (!window.AudioContext && !window.webkitAudioContext) return;

        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }

        if (this.sounds?.has(soundName)) {
            const source = this.audioContext.createBufferSource();
            source.buffer = this.sounds.get(soundName);
            source.connect(this.audioContext.destination);
            source.start(0);
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `fantasy-notification ${type}`;
        notification.textContent = message;

        document.body.appendChild(notification);

        // Анимация появления
        requestAnimationFrame(() => {
            notification.classList.add('show');
            setTimeout(() => {
                notification.classList.add('hide');
                setTimeout(() => notification.remove(), 300);
            }, 3000);
        });
    }

    updateAnalytics() {
        // Обновляем статистику паттернов
        this.patterns.forEach((pattern, id) => {
            if (!this.analytics.patterns.has(id)) {
                this.analytics.patterns.set(id, {
                    uses: 0,
                    successes: 0,
                    failures: 0
                });
            }
        });

        // Обновляем статистику триггеров
        this.state.triggers.forEach(trigger => {
            if (!this.analytics.triggers.has(trigger)) {
                this.analytics.triggers.set(trigger, {
                    activations: 0,
                    lastActivation: null
                });
            }
        });

        // Обновляем временную статистику
        this.analytics.timings.push({
            timestamp: Date.now(),
            duration: this.state.active ? Date.now() - this.state.lastUpdate : 0
        });

        // Ограничиваем размер истории
        if (this.analytics.timings.length > 100) {
            this.analytics.timings.shift();
        }
    }

    updateAnalyticsHistory(statistics) {
        this.analytics.successRates.push({
            timestamp: Date.now(),
            rate: (statistics.successfulAttempts / statistics.totalAttempts) || 0
        });

        // Ограничиваем размер истории
        if (this.analytics.successRates.length > 100) {
            this.analytics.successRates.shift();
        }
    }

    getAnalytics() {
        return {
            patterns: Object.fromEntries(this.analytics.patterns),
            triggers: Object.fromEntries(this.analytics.triggers),
            timings: this.analytics.timings,
            successRates: this.analytics.successRates,
            summary: this.getAnalyticsSummary()
        };
    }

    getAnalyticsSummary() {
        return {
            averageSuccessRate: this.calculateAverageSuccessRate(),
            averageDuration: this.calculateAverageDuration(),
            mostUsedPatterns: this.getMostUsedPatterns(),
            mostEffectiveTriggers: this.getMostEffectiveTriggers(),
            trends: this.calculateTrends()
        };
    }

    calculateAverageSuccessRate() {
        if (this.analytics.successRates.length === 0) return 0;
        
        const sum = this.analytics.successRates.reduce(
            (acc, curr) => acc + curr.rate, 0
        );
        return sum / this.analytics.successRates.length;
    }

    calculateAverageDuration() {
        if (this.analytics.timings.length === 0) return 0;
        
        const sum = this.analytics.timings.reduce(
            (acc, curr) => acc + curr.duration, 0
        );
        return sum / this.analytics.timings.length;
    }

    getMostUsedPatterns(limit = 5) {
        return Array.from(this.analytics.patterns.entries())
            .sort((a, b) => b[1].uses - a[1].uses)
            .slice(0, limit)
            .map(([id, stats]) => ({
                id,
                pattern: this.patterns.get(id),
                ...stats
            }));
    }

    getMostEffectiveTriggers(limit = 5) {
        return Array.from(this.analytics.triggers.entries())
            .sort((a, b) => b[1].activations - a[1].activations)
            .slice(0, limit)
            .map(([trigger, stats]) => ({
                trigger,
                ...stats
            }));
    }

    calculateTrends() {
        const recentSuccessRates = this.analytics.successRates.slice(-20);
        const recentTimings = this.analytics.timings.slice(-20);

        return {
            successRateTrend: this.calculateTrend(recentSuccessRates.map(r => r.rate)),
            durationTrend: this.calculateTrend(recentTimings.map(t => t.duration)),
            improvement: this.calculateImprovement(recentSuccessRates)
        };
    }

    calculateTrend(values) {
        if (values.length < 2) return 0;

        const xMean = (values.length - 1) / 2;
        const yMean = values.reduce((a, b) => a + b) / values.length;

        let numerator = 0;
        let denominator = 0;

        values.forEach((y, x) => {
            numerator += (x - xMean) * (y - yMean);
            denominator += Math.pow(x - xMean, 2);
        });

        return denominator === 0 ? 0 : numerator / denominator;
    }

    calculateImprovement(rates) {
        if (rates.length < 10) return 0;

        const midPoint = Math.floor(rates.length / 2);
        const firstHalf = rates.slice(0, midPoint);
        const secondHalf = rates.slice(midPoint);

        const firstAvg = firstHalf.reduce((a, b) => a + b.rate, 0) / firstHalf.length;
        const secondAvg = secondHalf.reduce((a, b) => a + b.rate, 0) / secondHalf.length;

        return ((secondAvg - firstAvg) / firstAvg) * 100;
    }

    exportData() {
        const data = {
            state: this.state,
            analytics: this.getAnalytics(),
            patterns: Array.from(this.patterns.entries()),
            timestamp: new Date().toISOString()
        };

        const blob = new Blob([JSON.stringify(data, null, 2)], {
            type: 'application/json'
        });

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `fantasy-data-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    cleanup() {
        // Очищаем все обработчики событий
        this.eventHandlers.forEach((handlers, element) => {
            handlers.forEach((handler, event) => {
                element.removeEventListener(event, handler);
            });
        });
        this.eventHandlers.clear();

        // Останавливаем автообновление
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }

        // Очищаем аудио контекст
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }

        // Очищаем анимации
        this.animations.clear();

        // Сохраняем текущее состояние
        this.saveState();
    }

    saveState() {
        try {
            localStorage.setItem('fantasyState', JSON.stringify({
                state: this.state,
                analytics: this.getAnalytics(),
                timestamp: Date.now()
            }));
        } catch (error) {
            console.error('Failed to save fantasy state:', error);
        }
    }

    loadState() {
        try {
            const saved = localStorage.getItem('fantasyState');
            if (saved) {
                const data = JSON.parse(saved);
                // Проверяем актуальность данных (не старше 24 часов)
                if (Date.now() - data.timestamp < 24 * 60 * 60 * 1000) {
                    this.state = { ...this.state, ...data.state };
                    this.analytics = { ...this.analytics, ...data.analytics };
                    return true;
                }
            }
        } catch (error) {
            console.error('Failed to load fantasy state:', error);
        }
        return false;
    }

    handleError(error) {
        console.error('Fantasy error:', error);
        this.showNotification('An error occurred', 'error');
        
        // Отправляем ошибку в систему аналитики
        this.trackError(error);
    }

    trackError(error) {
        try {
            fetch('/api/fantasy/error', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    error: error.message,
                    stack: error.stack,
                    state: this.state,
                    timestamp: Date.now()
                })
            });
        } catch (e) {
            console.error('Failed to track error:', e);
        }
    }
}

// Экспорт класса
export default FantasyManager;
