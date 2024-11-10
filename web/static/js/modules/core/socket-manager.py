// web/static/js/modules/core/websocket-manager.js
export class WebSocketManager {
    constructor(url) {
        this.url = url;
        this.socket = null;
        this.eventManager = new EventManager();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
    }

    connect() {
        try {
            this.socket = io(this.url, {
                reconnection: true,
                reconnectionDelay: this.reconnectDelay,
                reconnectionDelayMax: 5000,
                timeout: 20000
            });

            this.setupSocketHandlers();
        } catch (error) {
            console.error('WebSocket connection failed:', error);
            this.handleConnectionError(error);
        }
    }

    setupSocketHandlers() {
        this.socket.on('connect', () => {
            this.reconnectAttempts = 0;
            this.eventManager.emit('connected');
        });

        this.socket.on('disconnect', () => {
            this.eventManager.emit('disconnected');
            this.tryReconnect();
        });

        this.socket.on('error', (error) => {
            this.handleConnectionError(error);
        });

        this.socket.on('game_update', (data) => {
            this.eventManager.emit('gameUpdate', data);
        });
    }

    emit(event, data) {
        return new Promise((resolve, reject) => {
            if (!this.socket || !this.socket.connected) {
                reject(new Error('Socket not connected'));
                return;
            }

            const timeout = setTimeout(() => {
                reject(new Error('Socket operation timeout'));
            }, 5000);

            this.socket.emit(event, data, (response) => {
                clearTimeout(timeout);
                resolve(response);
            });
        });
    }

    tryReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            this.eventManager.emit('reconnectFailed');
            return;
        }

        this.reconnectAttempts++;
        setTimeout(() => {
            this.connect();
        }, this.reconnectDelay * this.reconnectAttempts);
    }

    handleConnectionError(error) {
        this.eventManager.emit('error', error);
        console.error('WebSocket error:', error);
    }

    subscribe(event, handler) {
        return this.eventManager.on(event, handler);
    }

    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
        }
    }
}
