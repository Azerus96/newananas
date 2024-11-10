// web/static/js/modules/core/state-manager.js
export class StateManager {
    constructor() {
        this.state = {};
        this.history = [];
        this.subscribers = new Set();
    }

    setState(newState) {
        this.history.push({...this.state});
        this.state = {...this.state, ...newState};
        this.notifySubscribers();
    }

    subscribe(callback) {
        this.subscribers.add(callback);
        return () => this.subscribers.delete(callback);
    }

    private notifySubscribers() {
        this.subscribers.forEach(callback => callback(this.state));
    }
}
