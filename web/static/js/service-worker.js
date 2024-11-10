// web/static/js/service-worker.js

const CACHE_NAME = 'ofc-poker-v1';
const ASSETS_TO_CACHE = [
    '/',
    '/offline',
    '/static/css/style.css',
    '/static/css/game.css',
    '/static/css/menu.css',
    '/static/css/statistics.css',
    '/static/css/training.css',
    '/static/css/fantasy.css',
    '/static/js/game.js',
    '/static/js/ui.js',
    '/static/js/statistics.js',
    '/static/js/training.js',
    '/static/js/fantasy.js',
    '/static/images/icon-192.png',
    '/static/images/icon-512.png',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css',
    'https://cdn.socket.io/4.0.1/socket.io.min.js',
    'https://cdn.jsdelivr.net/npm/chart.js'
];

// Установка service worker
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                return cache.addAll(ASSETS_TO_CACHE);
            })
            .then(() => {
                return self.skipWaiting();
            })
    );
});

// Активация service worker
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => {
            return self.clients.claim();
        })
    );
});

// Стратегия кэширования: Network First, затем Cache
self.addEventListener('fetch', (event) => {
    // Пропускаем запросы к API и WebSocket
    if (event.request.url.includes('/api/') || 
        event.request.url.includes('socket.io')) {
        return;
    }

    event.respondWith(
        fetch(event.request)
            .then((response) => {
                // Кэшируем успешный ответ
                if (response.status === 200) {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME)
                        .then((cache) => {
                            cache.put(event.request, responseClone);
                        });
                }
                return response;
            })
            .catch(() => {
                // При отсутствии сети используем кэш
                return caches.match(event.request)
                    .then((response) => {
                        if (response) {
                            return response;
                        }
                        // Если ресурс не найден в кэше, показываем офлайн-страницу
                        if (event.request.mode === 'navigate') {
                            return caches.match('/offline');
                        }
                        return new Response('', {
                            status: 404,
                            statusText: 'Not Found'
                        });
                    });
            })
    );
});

// Обработка push-уведомлений
self.addEventListener('push', (event) => {
    const options = {
        body: event.data.text(),
        icon: '/static/images/icon-192.png',
        badge: '/static/images/icon-192.png',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            {
                action: 'open',
                title: 'Открыть приложение'
            },
            {
                action: 'close',
                title: 'Закрыть'
            }
        ]
    };

    event.waitUntil(
        self.registration.showNotification('OFC Poker', options)
    );
});

// Обработка действий с уведомлениями
self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    if (event.action === 'open') {
        event.waitUntil(
            clients.matchAll({
                type: 'window'
            }).then((clientList) => {
                for (const client of clientList) {
                    if (client.url === '/' && 'focus' in client) {
                        return client.focus();
                    }
                }
                if (clients.openWindow) {
                    return clients.openWindow('/');
                }
            })
        );
    }
});

// Периодическая синхронизация
self.addEventListener('periodicsync', (event) => {
    if (event.tag === 'update-stats') {
        event.waitUntil(updateStatistics());
    }
});

async function updateStatistics() {
    try {
        const response = await fetch('/api/statistics/sync', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            // Обновляем локальное хранилище статистики
            const statsCache = await caches.open('stats-cache');
            await statsCache.put('/api/statistics', new Response(JSON.stringify(data)));
        }
    } catch (error) {
        console.error('Failed to sync statistics:', error);
    }
}

// Обработка фоновых синхронизаций
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-moves') {
        event.waitUntil(syncMoves());
    }
});

async function syncMoves() {
    try {
        const movesCache = await caches.open('moves-cache');
        const moves = await movesCache.match('/pending-moves');
        
        if (moves) {
            const pendingMoves = await moves.json();
            
            for (const move of pendingMoves) {
                await fetch('/api/sync-move', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(move)
                });
            }
            
            // Очищаем кэш после успешной синхронизации
            await movesCache.delete('/pending-moves');
        }
    } catch (error) {
        console.error('Failed to sync moves:', error);
    }
}
