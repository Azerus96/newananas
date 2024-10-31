# Reinforcement Learning for Open Face Chinese Poker

Проект по обучению RL-агентов игре в Open Face Chinese Poker.

## Особенности

- Реализация различных RL алгоритмов (DQN, A3C, PPO)
- Веб-интерфейс для игры против обученных агентов
- Визуализация процесса обучения
- Docker поддержка
- Масштабируемая архитектура

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/rlofc.git
cd rlofc
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

3. Установите зависимости:
```bash
pip install -e ".[dev]"
```

## Использование

### Запуск веб-интерфейса

```bash
python -m rlofc.web.app
```

### Обучение агента

```bash
python -m rlofc.training.train --agent dqn --episodes 1000
```

### Запуск с Docker

```bash
docker-compose up
```

## Структура проекта

```
rlofc/
├── agents/          # Реализации агентов
├── core/            # Ядро игры
├── evaluation/      # Оценка комбинаций
├── models/          # Нейронные сети
├── training/        # Обучение
├── utils/           # Утилиты
└── web/            # Веб-интерфейс
```

## Тестирование

```bash
pytest tests/
```

## Документация

Подробная документация доступна в директории `docs/`.

## Лицензия

MIT License

## Авторы

- Azerus96 (@Azerus96)

## Благодарности

- Deuces library
- OpenAI Gym
- TensorFlow team
```
