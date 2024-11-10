// web/static/js/ui.js

class GameUI {
    constructor(game) {
        this.game = game;
        this.selectedCard = null;
        this.draggedCard = null;
        this.isMobile = window.innerWidth <= 768;
        this.animationEnabled = true;
        this.initializeElements();
        this.setupDragAndDrop();
        this.setupResponsiveUI();
        this.setupAnimationControl();
    }

    initializeElements() {
        this.elements = {
            mainMenu: document.getElementById('mainMenu'),
            gameContainer: document.getElementById('gameContainer'),
            playersContainer: document.getElementById('playersContainer'),
            playerHand: document.getElementById('playerHand'),
            removedCards: document.getElementById('removedCards'),
            moveHistory: document.getElementById('moveHistory'),
            gameStatus: document.getElementById('currentTurn'),
            gameTimer: document.getElementById('gameTimer'),
            cardSlots: document.getElementById('cardSlots'),
            trainingControls: document.getElementById('trainingControls'),
            sidePanel: document.getElementById('sidePanel'),
            menuButton: document.getElementById('menuButton'),
            mobileMenu: document.getElementById('mobileMenu'),
            animationControl: document.getElementById('animationControl'),
            foulsRate: document.getElementById('foulsRate'),
            scoopsRate: document.getElementById('scoopsRate'),
            fantasyStatus: document.getElementById('fantasyStatus')
        };

        // Инициализация мобильного меню
        if (this.isMobile) {
            this.initializeMobileMenu();
        }

        // Инициализация всплывающих подсказок
        this.initializeTooltips();
    }

    setupAnimationControl() {
        if (this.elements.animationControl) {
            this.elements.animationControl.addEventListener('change', (e) => {
                this.animationEnabled = e.target.value !== 'off';
                document.body.classList.toggle('animations-disabled', !this.animationEnabled);
                localStorage.setItem('animationPreference', e.target.value);
            });

            // Загрузка сохраненных настроек
            const savedPreference = localStorage.getItem('animationPreference');
            if (savedPreference) {
                this.elements.animationControl.value = savedPreference;
                this.animationEnabled = savedPreference !== 'off';
                document.body.classList.toggle('animations-disabled', !this.animationEnabled);
            }
        }
    }

    initializeMobileMenu() {
        const mobileMenuHTML = `
            <div id="mobileMenu" class="mobile-menu">
                <div class="mobile-menu-header">
                    <h3>Меню</h3>
                    <button class="close-menu">×</button>
                </div>
                <div class="mobile-menu-content">
                    <button class="menu-item" data-action="newGame">Новая игра</button>
                    <button class="menu-item" data-action="statistics">Статистика</button>
                    <button class="menu-item" data-action="settings">Настройки</button>
                    <button class="menu-item" data-action="tutorial">Обучение</button>
                    <button class="menu-item" data-action="returnToMenu">Вернуться в меню</button>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', mobileMenuHTML);

        // Обработчики для мобильного меню
        document.querySelector('.close-menu').addEventListener('click', () => {
            this.closeMobileMenu();
        });

        document.querySelectorAll('.menu-item').forEach(item => {
            item.addEventListener('click', (e) => {
                this.handleMobileMenuAction(e.target.dataset.action);
            });
        });
    }

    initializeTooltips() {
        const tooltips = [
            {
                element: this.elements.foulsRate,
                text: 'Процент ходов, нарушающих правило старшинства комбинаций'
            },
            {
                element: this.elements.scoopsRate,
                text: 'Процент ситуаций, когда игрок выигрывает все три ряда'
            },
            {
                element: this.elements.fantasyStatus,
                text: 'Текущий статус фантазии и бонусы'
            }
        ];

        tooltips.forEach(({element, text}) => {
            if (element) {
                element.setAttribute('data-tooltip', text);
                element.classList.add('has-tooltip');
            }
        });
    }

    setupDragAndDrop() {
        if (this.isMobile) {
            this.setupTouchDragAndDrop();
        } else {
            this.setupMouseDragAndDrop();
        }
    }

    setupMouseDragAndDrop() {
        document.addEventListener('dragstart', (e) => {
            if (e.target.classList.contains('card')) {
                this.draggedCard = e.target;
                e.target.classList.add('dragging');
                e.dataTransfer.setData('text/plain', '');
            }
        });

        document.addEventListener('dragend', (e) => {
            if (e.target.classList.contains('card')) {
                e.target.classList.remove('dragging');
                this.draggedCard = null;
            }
        });

        document.querySelectorAll('.card-slot').forEach(slot => {
            slot.addEventListener('dragover', (e) => {
                e.preventDefault();
                if (this.isValidDropTarget(slot)) {
                    slot.classList.add('droppable');
                }
            });

            slot.addEventListener('dragleave', (e) => {
                slot.classList.remove('droppable');
            });

            slot.addEventListener('drop', (e) => {
                e.preventDefault();
                slot.classList.remove('droppable');
                if (this.draggedCard && this.isValidDropTarget(slot)) {
                    this.handleCardDrop(this.draggedCard, slot);
                }
            });
        });
    }

    setupTouchDragAndDrop() {
        let touchCard = null;
        let initialX = 0;
        let initialY = 0;

        document.addEventListener('touchstart', (e) => {
            if (e.target.classList.contains('card')) {
                touchCard = e.target;
                const touch = e.touches[0];
                initialX = touch.clientX - touchCard.offsetLeft;
                initialY = touch.clientY - touchCard.offsetTop;
                touchCard.classList.add('dragging');
            }
        }, { passive: false });

        document.addEventListener('touchmove', (e) => {
            if (touchCard) {
                e.preventDefault();
                const touch = e.touches[0];
                touchCard.style.position = 'fixed';
                touchCard.style.left = `${touch.clientX - initialX}px`;
                touchCard.style.top = `${touch.clientY - initialY}px`;
                
                const slot = this.getTouchTargetSlot(touch.clientX, touch.clientY);
                if (slot && this.isValidDropTarget(slot)) {
                    slot.classList.add('droppable');
                }
            }
        }, { passive: false });

        document.addEventListener('touchend', (e) => {
            if (touchCard) {
                const touch = e.changedTouches[0];
                const slot = this.getTouchTargetSlot(touch.clientX, touch.clientY);
                
                if (slot && this.isValidDropTarget(slot)) {
                    this.handleCardDrop(touchCard, slot);
                } else {
                    this.resetCardPosition(touchCard);
                }
                
                touchCard.classList.remove('dragging');
            touchCard = null;
            
            // Очищаем подсветку всех слотов
            document.querySelectorAll('.card-slot').forEach(slot => {
                slot.classList.remove('droppable');
            });
        }
    });
}

getTouchTargetSlot(x, y) {
    const elements = document.elementsFromPoint(x, y);
    return elements.find(el => el.classList.contains('card-slot'));
}

resetCardPosition(card) {
    card.style.position = '';
    card.style.left = '';
    card.style.top = '';
}

isValidDropTarget(slot) {
    if (!this.draggedCard || slot.classList.contains('occupied')) {
        return false;
    }

    const card = this.getCardData(this.draggedCard);
    const position = parseInt(slot.dataset.position);
    
    return this.game.isValidMove(card, position);
}

handleCardDrop(card, slot) {
    const cardData = this.getCardData(card);
    const position = parseInt(slot.dataset.position);

    if (this.animationEnabled) {
        this.animateCardPlacement(card, slot, () => {
            this.game.makeMove(cardData, position);
        });
    } else {
        this.game.makeMove(cardData, position);
    }
}

animateCardPlacement(card, slot, callback) {
    const cardRect = card.getBoundingClientRect();
    const slotRect = slot.getBoundingClientRect();
    
    const deltaX = slotRect.left - cardRect.left;
    const deltaY = slotRect.top - cardRect.top;

    card.style.transition = 'transform 0.3s ease-out';
    card.style.transform = `translate(${deltaX}px, ${deltaY}px)`;

    card.addEventListener('transitionend', () => {
        card.style.transition = '';
        card.style.transform = '';
        callback();
    }, { once: true });
}

updateGameState(state) {
    // Обновляем статус игры
    this.elements.gameStatus.textContent = 
        state.currentPlayer === 0 ? 'Ваш ход' : `Ход ${this.getPlayerName(state.currentPlayer)}`;

    // Обновляем таймер
    if (state.currentPlayer === 0) {
        this.startTimer();
    } else {
        this.stopTimer();
    }

    // Обновляем карты в руке
    this.updatePlayerHand(state.playerCards);

    // Обновляем доски всех игроков
    this.updateBoards(state);

    // Обновляем вышедшие карты
    this.updateRemovedCards(state.removedCards);

    // Обновляем историю ходов
    if (state.lastMove) {
        this.addMoveToHistory(state.lastMove);
    }

    // Обновляем статус фантазии
    this.updateFantasyStatus(state.fantasyStatus);

    // Обновляем статистику
    this.updateStatistics(state);

    // Обновляем боковую панель
    this.updateSidePanel(state);
}

updateStatistics(state) {
    // Обновляем показатели фолов и скупов
    if (this.elements.foulsRate) {
        this.elements.foulsRate.textContent = 
            `${((state.fouls / state.totalMoves) * 100).toFixed(1)}%`;
    }
    if (this.elements.scoopsRate) {
        this.elements.scoopsRate.textContent = 
            `${((state.scoops / state.totalMoves) * 100).toFixed(1)}%`;
    }
}

updateFantasyStatus(status) {
    if (this.elements.fantasyStatus) {
        const statusText = status.active ? 
            `Фантазия активна (${status.cardsCount} карт)` : 
            'Фантазия неактивна';
        
        this.elements.fantasyStatus.textContent = statusText;
        this.elements.fantasyStatus.classList.toggle('active', status.active);

        if (status.progressiveBonus) {
            this.elements.fantasyStatus.setAttribute(
                'data-bonus',
                `Прогрессивный бонус: ${status.progressiveBonus}`
            );
        }
    }
}

showAIThinking(player, thinkTime = 30) {
    const overlay = document.createElement('div');
    overlay.className = 'thinking-overlay';
    
    const content = `
        <div class="thinking-content">
            <div class="spinner"></div>
            <p>${this.getPlayerName(player)} думает...</p>
            ${this.animationEnabled ? `
                <div class="progress-bar">
                    <div class="progress" style="animation-duration: ${thinkTime}s"></div>
                </div>
            ` : ''}
        </div>
    `;
    
    overlay.innerHTML = content;
    document.body.appendChild(overlay);
}

hideAIThinking() {
    const overlay = document.querySelector('.thinking-overlay');
    if (overlay) {
        overlay.classList.add('fade-out');
        setTimeout(() => overlay.remove(), 300);
    }
}

showGameOver(result) {
    const modal = document.createElement('div');
    modal.className = 'game-over-modal';
    
    const content = `
        <div class="game-over-content">
            <h2>Игра окончена</h2>
            <div class="game-results">
                <h3>${result.winner === 0 ? 'Вы победили!' : `${this.getPlayerName(result.winner)} победил!`}</h3>
                <div class="results-details">
                    <p>Ваш счёт: ${result.playerScore}</p>
                    ${result.aiScores.map((score, i) => 
                        `<p>${this.getPlayerName(i + 1)} счёт: ${score}</p>`
                    ).join('')}
                    <p>Роялти: ${result.royalties}</p>
                    <p>Фолы: ${((result.fouls / result.totalMoves) * 100).toFixed(1)}%</p>
                    <p>Скупы: ${((result.scoops / result.totalMoves) * 100).toFixed(1)}%</p>
                    ${result.fantasyAchieved ? '<p class="fantasy-achieved">Фантазия достигнута!</p>' : ''}
                </div>
            </div>
            <div class="game-over-buttons">
                <button class="new-game">Новая игра</button>
                <button class="return-menu">Вернуться в меню</button>
            </div>
        </div>
    `;
    
    modal.innerHTML = content;

    modal.querySelector('.new-game').addEventListener('click', () => {
        modal.remove();
        this.game.startGame();
    });

    modal.querySelector('.return-menu').addEventListener('click', () => {
        modal.remove();
        this.game.returnToMenu();
    });

    document.body.appendChild(modal);
}

showError(message) {
    const toast = document.createElement('div');
    toast.className = 'error-toast';
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

return player === 0 ? 'Вы' : 
            this.game.state.agents[player - 1]?.name.replace('Agent', 'AI ') || `Игрок ${player}`;
    }

    toggleMobileMenu() {
        const menu = document.getElementById('mobileMenu');
        menu.classList.toggle('active');
        
        // Добавляем затемнение фона
        if (menu.classList.contains('active')) {
            const overlay = document.createElement('div');
            overlay.className = 'mobile-menu-overlay';
            overlay.addEventListener('click', () => this.closeMobileMenu());
            document.body.appendChild(overlay);
        } else {
            document.querySelector('.mobile-menu-overlay')?.remove();
        }
    }

    closeMobileMenu() {
        const menu = document.getElementById('mobileMenu');
        menu.classList.remove('active');
        document.querySelector('.mobile-menu-overlay')?.remove();
    }

    handleMobileMenuAction(action) {
        switch(action) {
            case 'newGame':
                this.game.startGame();
                break;
            case 'statistics':
                this.game.showFullStatistics();
                break;
            case 'settings':
                this.showSettingsModal();
                break;
            case 'tutorial':
                this.game.showTutorial();
                break;
            case 'returnToMenu':
                this.game.showConfirmDialog(
                    "Вернуться в меню",
                    "Вы уверены, что хотите вернуться в главное меню?",
                    () => this.game.returnToMenu()
                );
                break;
        }
        this.closeMobileMenu();
    }

    showSettingsModal() {
        const modal = document.createElement('div');
        modal.className = 'settings-modal';
        modal.innerHTML = `
            <div class="settings-content">
                <h2>Настройки</h2>
                <div class="settings-group">
                    <label>Анимация:</label>
                    <select id="animationSetting">
                        <option value="normal">Нормальная</option>
                        <option value="fast">Быстрая</option>
                        <option value="off">Выключена</option>
                    </select>
                </div>
                <div class="settings-group">
                    <label>Звуковые эффекты:</label>
                    <label class="switch">
                        <input type="checkbox" id="soundSetting">
                        <span class="slider round"></span>
                    </label>
                </div>
                <div class="settings-group">
                    <label>Тема:</label>
                    <select id="themeSetting">
                        <option value="light">Светлая</option>
                        <option value="dark">Тёмная</option>
                        <option value="auto">Системная</option>
                    </select>
                </div>
                <div class="settings-buttons">
                    <button class="save-settings">Сохранить</button>
                    <button class="cancel-settings">Отмена</button>
                </div>
            </div>
        `;

        // Загружаем текущие настройки
        const currentSettings = this.loadSettings();
        modal.querySelector('#animationSetting').value = currentSettings.animation;
        modal.querySelector('#soundSetting').checked = currentSettings.sound;
        modal.querySelector('#themeSetting').value = currentSettings.theme;

        // Добавляем обработчики
        modal.querySelector('.save-settings').addEventListener('click', () => {
            const newSettings = {
                animation: modal.querySelector('#animationSetting').value,
                sound: modal.querySelector('#soundSetting').checked,
                theme: modal.querySelector('#themeSetting').value
            };
            this.saveSettings(newSettings);
            modal.remove();
        });

        modal.querySelector('.cancel-settings').addEventListener('click', () => {
            modal.remove();
        });

        document.body.appendChild(modal);
    }

    loadSettings() {
        const defaultSettings = {
            animation: 'normal',
            sound: true,
            theme: 'light'
        };
        
        try {
            return JSON.parse(localStorage.getItem('gameSettings')) || defaultSettings;
        } catch {
            return defaultSettings;
        }
    }

    saveSettings(settings) {
        localStorage.setItem('gameSettings', JSON.stringify(settings));
        this.applySettings(settings);
    }

    applySettings(settings) {
        // Применяем анимацию
        this.animationEnabled = settings.animation !== 'off';
        document.body.classList.toggle('animations-disabled', !this.animationEnabled);

        // Применяем звук
        document.body.classList.toggle('sound-enabled', settings.sound);

        // Применяем тему
        document.body.className = document.body.className.replace(/theme-\w+/, '');
        document.body.classList.add(`theme-${settings.theme}`);
    }

    showConfirmDialog({ title, message, onConfirm, onCancel }) {
        const dialog = document.createElement('div');
        dialog.className = 'confirm-dialog';
        dialog.innerHTML = `
            <div class="confirm-dialog-content">
                <h3>${title}</h3>
                <p>${message}</p>
                <div class="confirm-dialog-buttons">
                    <button class="confirm-yes">Да</button>
                    <button class="confirm-no">Нет</button>
                </div>
            </div>
        `;

        dialog.querySelector('.confirm-yes').addEventListener('click', () => {
            onConfirm();
            dialog.remove();
        });

        dialog.querySelector('.confirm-no').addEventListener('click', () => {
            if (onCancel) onCancel();
            dialog.remove();
        });

        document.body.appendChild(dialog);
    }

    setupResponsiveUI() {
        window.addEventListener('resize', () => {
            this.isMobile = window.innerWidth <= 768;
            this.updateLayout();
        });

        // Начальная настройка layout
        this.updateLayout();
    }

    updateLayout() {
        if (this.isMobile) {
            document.body.classList.add('mobile');
            this.setupMobileLayout();
        } else {
            document.body.classList.remove('mobile');
            this.setupDesktopLayout();
        }
    }

    setupMobileLayout() {
        // Настройка мобильного интерфейса
        this.elements.sidePanel?.classList.add('mobile-panel');
        
        // Обработка ориентации
        if (window.innerWidth > window.innerHeight) {
            document.body.classList.add('landscape');
            this.adjustLayoutForLandscape();
        } else {
            document.body.classList.remove('landscape');
            this.adjustLayoutForPortrait();
        }
    }

    setupDesktopLayout() {
        // Настройка десктопного интерфейса
        this.elements.sidePanel?.classList.remove('mobile-panel');
        this.resetLayout();
    }

    adjustLayoutForLandscape() {
        if (this.elements.playersContainer) {
            this.elements.playersContainer.style.gridTemplateColumns = 'repeat(auto-fit, minmax(250px, 1fr))';
        }
    }

    adjustLayoutForPortrait() {
        if (this.elements.playersContainer) {
            this.elements.playersContainer.style.gridTemplateColumns = '1fr';
        }
    }

    resetLayout() {
        if (this.elements.playersContainer) {
            this.elements.playersContainer.style.gridTemplateColumns = '';
        }
    }
}

// Экспортируем класс
export default GameUI;
