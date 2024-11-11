// Версия и название кэша
const CACHE_NAME = 'ofc-poker-v1.2';
const DYNAMIC_CACHE = 'ofc-poker-dynamic-v1';

// Ресурсы для предварительного кэширования
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
    '/static/sounds/card-place.mp3',
    '/static/sounds/card-flip.mp3',
    '/static/sounds/victory.mp3',
    '/static/sounds/error.mp3',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css',
    'https://cdn.socket.io/4.0.1/socket.io.min.js',
    'https://cdn.jsdelivr.net/npm/chart.js'
];

// Конфигурация кэширования для разных типов ресурсов
const cacheConfig = {
    images: {
        maxAge: 30 * 24 * 60 * 60 * 1000, // 30 дней
        maxItems: 100
    },
    api: {
        maxAge: 60 * 60 * 1000, // 1 час
        maxItems: 50
    },
    dynamic: {
        maxAge: 7 * 24 * 60 * 60 * 1000, // 7 дней
        maxItems: 200
    }
};

// Установка service worker
self.addEventListener('install', event => {
    event.waitUntil(
        Promise.all([
            caches.open(CACHE_NAME).then(cache => {
                return cache.addAll(ASSETS_TO_CACHE);
            }),
            self.skipWaiting()
        ]).catch(error => {
            console.error('Cache initialization failed:', error);
        })
    );
});

// Активация service worker
self.addEventListener('activate', event => {
    event.waitUntil(
        Promise.all([
            // Очистка старых версий кэша
            caches.keys().then(cacheNames => {
                return Promise.all(
                    cacheNames
                        .filter(cacheName => 
                            cacheName.startsWith('ofc-poker-') && 
                            cacheName !== CACHE_NAME &&
                            cacheName !== DYNAMIC_CACHE
                        )
                        .map(cacheName => caches.delete(cacheName))
                );
            }),
            // Очистка устаревших элементов в динамическом кэше
            cleanupDynamicCache(),
            // Получение контроля над всеми клиентами
            self.clients.claim()
        ])
    );
});

// Обработка запросов
self.addEventListener('fetch', event => {
    // Пропускаем запросы к API и WebSocket
    if (shouldSkipCache(event.request)) {
        return;
    }

    event.respondWith(
        handleFetch(event.request)
    );
});

async function handleFetch(request) {
    try {
        // Проверяем стратегию кэширования для данного запроса
        const strategy = getStrategyForRequest(request);
        
        switch (strategy) {
            case 'cache-first':
                return await handleCacheFirst(request);
            case 'network-first':
                return await handleNetworkFirst(request);
            case 'stale-while-revalidate':
                return await handleStaleWhileRevalidate(request);
            default:
                return await fetch(request);
        }
    } catch (error) {
        console.error('Fetch handling failed:', error);
        return await handleOffline(request);
    }
}

async function handleCacheFirst(request) {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
        return cachedResponse;
    }
    
    try {
        const networkResponse = await fetch(request);
        await updateCache(request, networkResponse.clone());
        return networkResponse;
    } catch (error) {
        return await handleOffline(request);
    }
}

async function handleNetworkFirst(request) {
    try {
        const networkResponse = await fetch(request);
        await updateCache(request, networkResponse.clone());
        return networkResponse;
    } catch (error) {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        return await handleOffline(request);
    }
}

async function handleStaleWhileRevalidate(request) {
    const cachedResponse = await caches.match(request);
    
    const networkResponsePromise = fetch(request).then(async response => {
        await updateCache(request, response.clone());
        return response;
    });

    return cachedResponse || networkResponsePromise;
}

async function updateCache(request, response) {
    if (!response || response.status !== 200 || response.type !== 'basic') {
        return;
    }

    const cache = await caches.open(
        shouldUseDynamicCache(request) ? DYNAMIC_CACHE : CACHE_NAME
    );
    await cache.put(request, response);
}

async function cleanupDynamicCache() {
    const cache = await caches.open(DYNAMIC_CACHE);
    const entries = await cache.keys();
    const now = Date.now();

    const deletionPromises = entries.map(async request => {
        const response = await cache.match(request);
        const cacheTime = response.headers.get('sw-cache-time');
        
        if (cacheTime && (now - parseInt(cacheTime)) > cacheConfig.dynamic.maxAge) {
            return cache.delete(request);
        }
    });

    await Promise.all(deletionPromises);

    // Ограничение количества элементов
    if (entries.length > cacheConfig.dynamic.maxItems) {
        const itemsToDelete = entries.slice(0, entries.length - cacheConfig.dynamic.maxItems);
        await Promise.all(itemsToDelete.map(request => cache.delete(request)));
    }
}

function shouldSkipCache(request) {
    return (
        request.url.includes('/api/') ||
        request.url.includes('socket.io') ||
        request.method !== 'GET'
    );
}

function shouldUseDynamicCache(request) {
    return !ASSETS_TO_CACHE.includes(new URL(request.url).pathname);
}

function getStrategyForRequest(request) {
    const url = new URL(request.url);
    
    if (url.pathname.startsWith('/static/images/')) {
        return 'cache-first';
    }
    
    if (url.pathname.startsWith('/static/')) {
        return 'stale-while-revalidate';
    }
    
    return 'network-first';
}

async function handleOffline(request) {
    // Для навигации показываем офлайн-страницу
    if (request.mode === 'navigate') {
        const cache = await caches.open(CACHE_NAME);
        return cache.match('/offline');
    }
    
    // Для изображений показываем заглушку
    if (request.destination === 'image') {
        return new Response(
            `<svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                <rect width="100" height="100" fill="#eee"/>
                <text x="50" y="50" text-anchor="middle" dy=".3em" fill="#999">Offline</text>
            </svg>`,
            {
                headers: {
                    'Content-Type': 'image/svg+xml',
                    'Cache-Control': 'no-store'
                }
            }
        );
    }

    // Для остальных ресурсов возвращаем ошибку
    return new Response('Offline content not available', {
        status: 503,
        statusText: 'Service Unavailable',
        headers: {
            'Content-Type': 'text/plain',
            'Cache-Control': 'no-store'
        }
    });
}

// Обработка push-уведомлений
self.addEventListener('push', event => {
    const options = {
        body: event.data?.text() || 'New update available',
        icon: '/static/images/icon-192.png',
        badge: '/static/images/icon-192.png',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: crypto.randomUUID()
        },
        actions: [
            {
                action: 'open',
                title: 'Open application'
            },
            {
                action: 'close',
                title: 'Close'
            }
        ]
    };

    event.waitUntil(
        self.registration.showNotification('OFC Poker', options)
    );
});

// Обработка действий с уведомлениями
self.addEventListener('notificationclick', event => {
    event.notification.close();

    if (event.action === 'open') {
        event.waitUntil(
            clients.matchAll({
                type: 'window'
            }).then(clientList => {
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
self.addEventListener('periodicsync', event => {
    if (event.tag === 'update-stats') {
        event.waitUntil(updateStatistics());
    } else if (event.tag === 'cleanup-cache') {
        event.waitUntil(cleanupDynamicCache());
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
            const statsCache = await caches.open('stats-cache');
            await statsCache.put('/api/statistics', new Response(JSON.stringify(data)));
            
            // Отправляем уведомление об обновлении статистики
            await self.registration.showNotification('Statistics Updated', {
                body: 'Your game statistics have been synchronized',
                icon: '/static/images/icon-192.png',
                badge: '/static/images/icon-192.png'
            });
        }
    } catch (error) {
        console.error('Failed to sync statistics:', error);
    }
}

// Обработка фоновых синхронизаций
self.addEventListener('sync', event => {
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

// Обработка ошибок
self.addEventListener('error', event => {
    console.error('Service Worker error:', event.error);
});

self.addEventListener('unhandledrejection', event => {
    console.error('Unhandled promise rejection:', event.reason);
});

// Утилиты для работы с кэшем
async function getCacheSize(cacheName) {
    const cache = await caches.open(cacheName);
    const keys = await cache.keys();
    return keys.length;
}

async function clearOldCache(maxAge) {
    const cacheNames = await caches.keys();
    const now = Date.now();

    return Promise.all(
        cacheNames.map(async cacheName => {
            const cache = await caches.open(cacheName);
            const keys = await cache.keys();
            
            return Promise.all(
                keys.map(async request => {
                    const response = await cache.match(request);
                    const cacheTime = response.headers.get('sw-cache-time');
                    
                    if (cacheTime && (now - parseInt(cacheTime)) > maxAge) {
                        return cache.delete(request);
                    }
                })
            );
        })
    );
}

// Функция для добавления временной метки к кэшированным ответам
function addTimestamp(response) {
    const headers = new Headers(response.headers);
    headers.append('sw-cache-time', Date.now().toString());
    
    return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: headers
    });
}

// Периодическая очистка кэша
setInterval(async () => {
    try {
        await clearOldCache(cacheConfig.dynamic.maxAge);
    } catch (error) {
        console.error('Cache cleanup failed:', error);
    }
}, 24 * 60 * 60 * 1000); // Раз в сутки
