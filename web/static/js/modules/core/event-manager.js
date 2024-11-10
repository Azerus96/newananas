// web/static/js/modules/core/event-manager.js
export class EventManager {
    constructor() {
        this.handlers = new Map();
    }

    on(event, handler) {
        if (!this.handlers.has(event)) {
            this.handlers.set(event, new Set());
        }
        this.handlers.get(event).add(handler);
        return () => this.off(event, handler);
    }

    emit(event, data) {
        const handlers = this.handlers.get(event);
        if (handlers) {
            handlers.forEach(handler => handler(data));
        }
    }

    off(event, handler) {
        const handlers = this.handlers.get(event);
        if (handlers) {
            handlers.delete(handler);
        }
    }
}
