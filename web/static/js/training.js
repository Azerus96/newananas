class TrainingMode {
    constructor() {
        // Проверка готовности DOM
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initialize());
        } else {
            this.initialize();
        }

        this.state = {
            active: false,
            currentPhase: null,
            aiThinking: false,
            lastMove: null,
            selectedRank: null,
            selectedSuit: null,
            selectedSlot: null,
            history: [],
            statistics: {
                movesAnalyzed: 0,
                thinkTime: [],
                fantasySuccess: 0,
                totalAttempts: 0,
                fouls: 0,
                scoops: 0,
                totalMoves: 0,
                patterns: new Map(),
                mistakes: []
            }
        };

        this.config = {
            fantasyMode: false,
            progressiveFantasy: false,
            thinkTime: 30,
            animationEnabled: true,
            soundEnabled: true,
            autoSave: true,
            difficultyLevel: 'medium'
        };

        this.eventHandlers = new Map();
        this.animations = new Map();
        this.sounds = new Map();
    }

    async initialize() {
        try {
            await this.initializeElements();
            this.setupEventListeners();
            await this.loadSettings();
            this.setupAnimations();
            this.setupSoundSystem();
            this.initializeAnalytics();
            
            if (this.config.autoSave) {
                this.loadSavedState();
            }
        } catch (error) {
            console.error('Training mode initialization failed:', error);
            this.handleInitializationError(error);
        }
    }

    async initializeElements() {
        // Основные элементы управления
        this.elements = {
            container: await this.waitForElement('container'),
            frontStreet: await this.waitForElement('frontStreet'),
            middleStreet: await this.waitForElement('middleStreet'),
            backStreet: await this.waitForElement('backStreet'),
            inputCards: await this.waitForElement('inputCards'),
            removedCards: {
                row1: await this.waitForElement('removedCardsRow1'),
                row2: await this.waitForElement('removedCardsRow2')
            },

            // Контролы
            fantasyMode: await this.waitForElement('fantasyMode'),
            progressiveFantasy: await this.waitForElement('progressiveFantasy'),
            thinkTime: await this.waitForElement('thinkTime'),
            distributeButton: await this.waitForElement('distributeCards'),
            clearButton: await this.waitForElement('clearSelection'),
            startButton: await this.waitForElement('startTraining'),
            resetButton: await this.waitForElement('resetBoard'),
            animationControl: await this.waitForElement('animationControl'),

            // Статистика
            movesCount: await this.waitForElement('movesCount'),
            avgThinkTime: await this.waitForElement('avgThinkTime'),
            fantasyRate: await this.waitForElement('fantasyRate'),
            foulsRate: await this.waitForElement('foulsRate'),
            scoopsRate: await this.waitForElement('scoopsRate'),

            // Выбор карт
            ranks: document.querySelectorAll('.rank'),
            suits: document.querySelectorAll('.suit')
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

            setTimeout(() => {
                observer.disconnect();
                reject(new Error(`Element ${id} not found`));
            }, 5000);
        });
    }

    validateElements() {
        const requiredElements = [
            'container', 'frontStreet', 'middleStreet', 'backStreet',
            'inputCards', 'distributeButton', 'clearButton'
        ];

        const missingElements = requiredElements.filter(id => !this.elements[id]);
        
        if (missingElements.length > 0) {
            throw new Error(`Missing required elements: ${missingElements.join(', ')}`);
        }
    }

    setupEventListeners() {
        // Настройки
        this.addEventHandler(this.elements.fantasyMode, 'change', 
            e => this.handleFantasyModeChange(e));
        this.addEventHandler(this.elements.progressiveFantasy, 'change', 
            e => this.handleProgressiveFantasyChange(e));
        this.addEventHandler(this.elements.thinkTime, 'input', 
            e => this.handleThinkTimeChange(e));

        // Кнопки управления
        this.addEventHandler(this.elements.startButton, 'click', 
            () => this.startTraining());
        this.addEventHandler(this.elements.resetButton, 'click', 
            () => this.resetBoard());
        this.addEventHandler(this.elements.distributeButton, 'click', 
            () => this.requestAIDistribution());
        this.addEventHandler(this.elements.clearButton, 'click', 
            () => this.clearSelection());

        // Выбор карт
        this.elements.ranks.forEach(button => {
            this.addEventHandler(button, 'click', 
                e => this.selectRank(e.target.dataset.rank));
        });

        this.elements.suits.forEach(button => {
            this.addEventHandler(button, 'click', 
                e => this.selectSuit(e.target.dataset.suit));
        });

        // Слоты для карт
        document.querySelectorAll('.card-slot').forEach(slot => {
            this.addEventHandler(slot, 'click', 
                () => this.handleSlotClick(slot));
        });

        // Обработка клавиатуры
        this.addEventHandler(document, 'keydown', 
            e => this.handleKeyboard(e));

        // Отмена последнего действия
        this.addEventHandler(document, 'keydown', e => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
                e.preventDefault();
                this.undoLastAction();
            }
        });
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

    async loadSettings() {
        try {
            const savedSettings = localStorage.getItem('trainingSettings');
            if (savedSettings) {
                const settings = JSON.parse(savedSettings);
                this.config = { ...this.config, ...settings };
            }

            // Загружаем звуки если они включены
            if (this.config.soundEnabled) {
                await this.loadSounds();
            }

            this.applySettings();
        } catch (error) {
            console.error('Failed to load settings:', error);
            this.showError('Failed to load settings');
        }
    }

    async loadSounds() {
        const soundFiles = {
            cardPlace: 'sounds/card-place.mp3',
            cardFlip: 'sounds/card-flip.mp3',
            success: 'sounds/success.mp3',
            error: 'sounds/error.mp3',
            fantasy: 'sounds/fantasy.mp3'
        };

        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            
            for (const [name, file] of Object.entries(soundFiles)) {
                const response = await fetch(file);
                const arrayBuffer = await response.arrayBuffer();
                const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
                this.sounds.set(name, audioBuffer);
            }
        } catch (error) {
            console.error('Failed to load sounds:', error);
        }
    }

    setupAnimations() {
        this.animations.set('cardPlace', {
            keyframes: [
                { transform: 'scale(1.1)', opacity: '0.8' },
                { transform: 'scale(1)', opacity: '1' }
            ],
            options: { duration: 300, easing: 'ease-out' }
        });

        this.animations.set('cardRemove', {
            keyframes: [
                { transform: 'scale(1)', opacity: '1' },
                { transform: 'scale(0.8)', opacity: '0' }
            ],
            options: { duration: 300, easing: 'ease-in' }
        });

        this.animations.set('highlight', {
            keyframes: [
                { backgroundColor: 'rgba(0, 123, 255, 0.2)' },
                { backgroundColor: 'transparent' }
            ],
            options: { duration: 500, iterations: 2 }
        });
    }

    initializeAnalytics() {
        this.analytics = {
            sessionStart: Date.now(),
            moves: [],
            patterns: new Map(),
            mistakes: [],
            timings: [],
            improvements: []
        };
    }

    async startTraining() {
        try {
            const response = await fetch('/api/training/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(this.config)
            });

            const data = await response.json();
            if (data.status === 'ok') {
                this.state.active = true;
                this.state.sessionId = data.session_id;
                this.updateUI(data.initial_state);
                this.showMessage('Training started');
                this.trackTrainingStart();
            } else {
                throw new Error(data.message || 'Failed to start training');
            }
        } catch (error) {
            console.error('Failed to start training:', error);
            this.showError('Failed to start training');
        }
    }

    async requestAIDistribution() {
        if (!this.validateInput()) {
            this.showError('Place at least 2 input cards');
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
                    config: this.config
                })
            });

            const result = await response.json();
            if (result.status === 'ok') {
                await this.handleAIMove(result);
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

    async handleAIMove(result) {
        const startTime = performance.now();

        if (this.config.animationEnabled) {
            await this.animateAIMove(result.move);
        } else {
            this.applyAIMove(result.move);
        }

        const duration = performance.now() - startTime;
        this.updateStatistics({
            ...result.statistics,
            moveTime: duration
        });

        this.analyzeMove(result.move);
    }

    async animateAIMove(move) {
        for (const action of move.actions) {
            await new Promise(resolve => {
                setTimeout(() => {
                    this.applyMoveAction(action);
                    resolve();
                }, this.config.animationEnabled ? 300 : 0);
            });
        }
    }

    applyMoveAction(action) {
        const { card, position, type } = action;
        const targetSlot = this.findSlotByPosition(position);
        
        if (type === 'place') {
            this.placeCard(targetSlot, card);
            if (this.config.soundEnabled) {
                this.playSound('cardPlace');
            }
        } else if (type === 'remove') {
            this.removeCard(targetSlot);
            if (this.config.soundEnabled) {
                this.playSound('cardFlip');
            }
        }
    }

    analyzeMove(move) {
        // Анализируем ход и обновляем статистику
        const analysis = {
            timestamp: Date.now(),
            move: move,
            position: move.position,
            pattern: this.identifyPattern(move),
            isFoul: this.checkForFoul(move),
            isScoop: this.checkForScoop(move),
            thinkTime: this.state.aiThinking ? 
                performance.now() - this.state.thinkStartTime : 0
        };

        this.state.history.push(analysis);
        this.updateAnalytics(analysis);
    }

    updateAnalytics(analysis) {
        // Обновляем паттерны
        if (analysis.pattern) {
            const patternStats = this.analytics.patterns.get(analysis.pattern) || {
                count: 0,
                success: 0,
                fails: 0
            };
            patternStats.count++;
            if (analysis.isFoul) {
                patternStats.fails++;
            } else {
                patternStats.success++;
            }
            this.analytics.patterns.set(analysis.pattern, patternStats);
        }

        // Обновляем ошибки
        if (analysis.isFoul) {
            this.analytics.mistakes.push({
                timestamp: Date.now(),
                move: analysis.move,
                type: 'foul'
            });
        }

        // Обновляем временную статистику
        this.analytics.timings.push(analysis.thinkTime);

        // Рассчитываем улучшения
        this.calculateImprovements();
    }

    calculateImprovements() {
        const recentMoves = this.state.history.slice(-20);
        if (recentMoves.length < 10) return;

        const midPoint = Math.floor(recentMoves.length / 2);
        const firstHalf = recentMoves.slice(0, midPoint);
        const secondHalf = recentMoves.slice(midPoint);

        const improvement = {
            timestamp: Date.now(),
            foulsRate: this.calculateImprovement(firstHalf, secondHalf, 'isFoul'),
            scoopsRate: this.calculateImprovement(firstHalf, secondHalf, 'isScoop'),
            thinkTime: this.calculateImprovement(firstHalf, secondHalf, 'thinkTime', true)
        };

        this.analytics.improvements.push(improvement);
    }

    calculateImprovement(firstHalf, secondHalf, property, isTime = false) {
        const firstAvg = firstHalf.reduce((sum, move) => sum + (move[property] ? 1 : 0), 0) / firstHalf.length;
        const secondAvg = secondHalf.reduce((sum, move) => sum + (move[property] ? 1 : 0), 0) / secondHalf.length;

        if (isTime) {
            return ((firstAvg - secondAvg) / firstAvg) * 100; // Уменьшение времени - улучшение
        }
        return ((secondAvg - firstAvg) / firstAvg) * 100; // Увеличение показателя - улучшение
    }

    updateStatistics(stats) {
        this.state.statistics = { ...this.state.statistics, ...stats };
        
        // Обновляем отображение статистики
        if (this.elements.movesCount) {
            this.elements.movesCount.textContent = this.state.statistics.movesAnalyzed;
        }
        if (this.elements.avgThinkTime) {
            this.elements.avgThinkTime.textContent = 
                `${this.calculateAverageThinkTime().toFixed(2)}s`;
        }
        if (this.elements.fantasyRate) {
            this.elements.fantasyRate.textContent = 
                `${this.calculateFantasyRate().toFixed(1)}%`;
        }
        if (this.elements.foulsRate) {
            this.elements.foulsRate.textContent = 
                `${this.calculateFoulsRate().toFixed(1)}%`;
        }
        if (this.elements.scoopsRate) {
            this.elements.scoopsRate.textContent = 
                `${this.calculateScoopsRate().toFixed(1)}%`;
        }

        // Анимируем обновление статистики
        this.animateStatisticsUpdate();
    }

    animateStatisticsUpdate() {
        if (!this.config.animationEnabled) return;

        document.querySelectorAll('.stat-value').forEach(element => {
            element.classList.add('updated');
            setTimeout(() => element.classList.remove('updated'), 300);
        });
    }

    calculateAverageThinkTime() {
        const times = this.state.statistics.thinkTime;
        return times.length ? times.reduce((a, b) => a + b, 0) / times.length : 0;
    }

    calculateFantasyRate() {
        const { fantasySuccess, totalAttempts } = this.state.statistics;
        return totalAttempts ? (fantasySuccess / totalAttempts) * 100 : 0;
    }

    calculateFoulsRate() {
        const { fouls, totalMoves } = this.state.statistics;
        return totalMoves ? (fouls / totalMoves) * 100 : 0;
    }

    calculateScoopsRate() {
        const { scoops, totalMoves } = this.state.statistics;
        return totalMoves ? (scoops / totalMoves) * 100 : 0;
    }

    showAIThinking() {
        const overlay = document.createElement('div');
        overlay.className = 'thinking-overlay';
        overlay.innerHTML = `
            <div class="thinking-content">
                <div class="spinner"></div>
                <p>AI analyzing moves...</p>
                ${this.config.animationEnabled ? `
                    <div class="progress-bar">
                        <div class="progress"></div>
                    </div>
                ` : ''}
            </div>
        `;
        document.body.appendChild(overlay);

        if (this.config.animationEnabled) {
            const progress = overlay.querySelector('.progress');
            let width = 0;
            const interval = setInterval(() => {
                if (width >= 100) {
                    clearInterval(interval);
                } else {
                    width++;
                    progress.style.width = width + '%';
                }
            }, this.config.thinkTime * 10);
        }
    }

    hideAIThinking() {
        const overlay = document.querySelector('.thinking-overlay');
        if (overlay) {
            overlay.classList.add('fade-out');
            setTimeout(() => overlay.remove(), 300);
        }
    }

    showMessage(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        requestAnimationFrame(() => {
            toast.classList.add('show');
            setTimeout(() => {
                toast.classList.add('fade-out');
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        });
    }

    showError(message) {
        this.showMessage(message, 'error');
        if (this.config.soundEnabled) {
            this.playSound('error');
        }
    }

    playSound(name) {
        if (!this.config.soundEnabled || !this.sounds.has(name)) return;

        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const source = audioContext.createBufferSource();
        source.buffer = this.sounds.get(name);
        source.connect(audioContext.destination);
        source.start(0);
    }

    exportTrainingData() {
        const data = {
            statistics: this.state.statistics,
            analytics: this.analytics,
            config: this.config,
            history: this.state.history,
            timestamp: new Date().toISOString()
        };

        const blob = new Blob([JSON.stringify(data, null, 2)], {
            type: 'application/json'
        });

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `training_data_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    cleanup() {
        // Очищаем обработчики событий
        this.eventHandlers.forEach((handlers, element) => {
            handlers.forEach((handler, event) => {
                element.removeEventListener(event, handler);
            });
        });
        this.eventHandlers.clear();

        // Сохраняем состояние если включено автосохранение
        if (this.config.autoSave) {
            this.saveState();
        }

        // Очищаем звуки
        this.sounds.clear();

        // Очищаем анимации
        this.animations.clear();

        // Очищаем UI
        this.resetBoard();
    }
}

// Экспорт класса
export default TrainingMode;
