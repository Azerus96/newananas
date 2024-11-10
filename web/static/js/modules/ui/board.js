// web/static/js/modules/ui/board.js
export class BoardUI {
    constructor(container, config = {}) {
        this.container = container;
        this.config = {
            cardWidth: 70,
            cardHeight: 100,
            spacing: 10,
            animation: true,
            ...config
        };
        
        this.cards = new Map();
        this.slots = new Map();
        this.draggedCard = null;
        
        this.initialize();
    }

    initialize() {
        this.createBoard();
        this.setupEventListeners();
    }

    createBoard() {
        // Создаем структуру доски
        const streets = ['top', 'middle', 'bottom'];
        const counts = [3, 5, 5];

        streets.forEach((street, index) => {
            const row = document.createElement('div');
            row.className = `street ${street}`;
            
            for (let i = 0; i < counts[index]; i++) {
                const slot = this.createCardSlot(street, i);
                row.appendChild(slot);
            }
            
            this.container.appendChild(row);
        });
    }

    createCardSlot(street, index) {
        const slot = document.createElement('div');
        slot.className = 'card-slot';
        slot.dataset.street = street;
        slot.dataset.index = index;
        
        this.slots.set(`${street}-${index}`, slot);
        return slot;
    }

    // web/static/js/modules/ui/board.js (продолжение)
    setupEventListeners() {
        // Обработка перетаскивания карт
        this.container.addEventListener('dragstart', (e) => {
            if (e.target.matches('.card')) {
                this.handleDragStart(e);
            }
        });

        this.container.addEventListener('dragover', (e) => {
            if (e.target.matches('.card-slot')) {
                this.handleDragOver(e);
            }
        });

        this.container.addEventListener('drop', (e) => {
            if (e.target.matches('.card-slot')) {
                this.handleDrop(e);
            }
        });

        // Обработка касаний для мобильных устройств
        if ('ontouchstart' in window) {
            this.setupTouchEvents();
        }
    }

    setupTouchEvents() {
        let touchStartX, touchStartY;
        let touchedCard = null;

        this.container.addEventListener('touchstart', (e) => {
            const card = e.target.closest('.card');
            if (card) {
                touchedCard = card;
                const touch = e.touches[0];
                touchStartX = touch.clientX - card.offsetLeft;
                touchStartY = touch.clientY - card.offsetTop;
                card.classList.add('dragging');
            }
        });

        this.container.addEventListener('touchmove', (e) => {
            if (touchedCard) {
                e.preventDefault();
                const touch = e.touches[0];
                touchedCard.style.position = 'fixed';
                touchedCard.style.left = `${touch.clientX - touchStartX}px`;
                touchedCard.style.top = `${touch.clientY - touchStartY}px`;
                
                this.highlightValidSlots(touchedCard);
            }
        });

        this.container.addEventListener('touchend', (e) => {
            if (touchedCard) {
                const slot = this.findSlotAtPosition(e.changedTouches[0]);
                if (slot && this.isValidMove(touchedCard, slot)) {
                    this.moveCard(touchedCard, slot);
                } else {
                    this.resetCardPosition(touchedCard);
                }
                touchedCard.classList.remove('dragging');
                this.clearHighlightedSlots();
                touchedCard = null;
            }
        });
    }

    handleDragStart(e) {
        this.draggedCard = e.target;
        e.target.classList.add('dragging');
        e.dataTransfer.setData('text/plain', '');
        this.highlightValidSlots(this.draggedCard);
    }

    handleDragOver(e) {
        e.preventDefault();
        if (this.isValidMove(this.draggedCard, e.target)) {
            e.target.classList.add('droppable');
        }
    }

    handleDrop(e) {
        e.preventDefault();
        const slot = e.target;
        slot.classList.remove('droppable');
        
        if (this.isValidMove(this.draggedCard, slot)) {
            this.moveCard(this.draggedCard, slot);
        }
        
        this.draggedCard.classList.remove('dragging');
        this.clearHighlightedSlots();
        this.draggedCard = null;
    }

    moveCard(card, slot) {
        if (this.config.animation) {
            this.animateCardMove(card, slot);
        } else {
            this.placeCard(card, slot);
        }
    }

    animateCardMove(card, slot) {
        const cardRect = card.getBoundingClientRect();
        const slotRect = slot.getBoundingClientRect();
        const deltaX = slotRect.left - cardRect.left;
        const deltaY = slotRect.top - cardRect.top;

        card.style.transition = 'transform 0.3s ease-out';
        card.style.transform = `translate(${deltaX}px, ${deltaY}px)`;

        card.addEventListener('transitionend', () => {
            this.placeCard(card, slot);
            card.style.transition = '';
            card.style.transform = '';
        }, { once: true });
    }

    placeCard(card, slot) {
        const oldSlot = card.parentElement;
        if (oldSlot) {
            oldSlot.classList.remove('occupied');
        }
        
        slot.appendChild(card);
        slot.classList.add('occupied');
        
        this.emitMoveEvent(card, slot);
    }

    emitMoveEvent(card, slot) {
        const moveEvent = new CustomEvent('cardMoved', {
            detail: {
                card: this.getCardData(card),
                street: slot.dataset.street,
                index: parseInt(slot.dataset.index)
            }
        });
        this.container.dispatchEvent(moveEvent);
    }

    isValidMove(card, slot) {
        if (!card || !slot || slot.classList.contains('occupied')) {
            return false;
        }
        
        // Дополнительная логика проверки валидности хода
        return true;
    }

    highlightValidSlots(card) {
        this.slots.forEach(slot => {
            if (this.isValidMove(card, slot)) {
                slot.classList.add('valid-target');
            }
        });
    }

    clearHighlightedSlots() {
        this.slots.forEach(slot => {
            slot.classList.remove('valid-target', 'droppable');
        });
    }

    getCardData(cardElement) {
        return {
            rank: cardElement.dataset.rank,
            suit: cardElement.dataset.suit,
            color: cardElement.classList.contains('red') ? 'red' : 'black'
        };
    }

    findSlotAtPosition(touch) {
        const elements = document.elementsFromPoint(touch.clientX, touch.clientY);
        return elements.find(el => el.matches('.card-slot'));
    }

    resetCardPosition(card) {
        card.style.position = '';
        card.style.left = '';
        card.style.top = '';
    }

    updateBoard(gameState) {
        // Обновление состояния доски на основе данных игры
        gameState.streets.forEach((street, streetIndex) => {
            street.cards.forEach((cardData, index) => {
                if (cardData) {
                    const slot = this.slots.get(`${streetIndex}-${index}`);
                    if (slot) {
                        this.createAndPlaceCard(cardData, slot);
                    }
                }
            });
        });
    }

    createAndPlaceCard(cardData, slot) {
        const card = document.createElement('div');
        card.className = `card ${cardData.color}`;
        card.dataset.rank = cardData.rank;
        card.dataset.suit = cardData.suit;
        card.draggable = true;

        card.innerHTML = `
            <span class="card-rank">${cardData.rank}</span>
            <span class="card-suit">${this.getSuitSymbol(cardData.suit)}</span>
        `;

        this.placeCard(card, slot);
    }

    getSuitSymbol(suit) {
        const symbols = {
            'h': '♥',
            'd': '♦',
            'c': '♣',
            's': '♠'
        };
        return symbols[suit] || suit;
    }
}
