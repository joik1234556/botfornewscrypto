# botfornewscrypto

Telegram-бот для автоматического сбора, AI-обработки и публикации криптовалютных новостей.

## Возможности

- Сбор новостей из трёх источников:
  - [Investing.com (RU)](https://ru.investing.com/news/cryptocurrency-news)
  - [TradingView (RU)](https://ru.tradingview.com/markets/cryptocurrencies/news/)
  - [CoinDesk (RU)](https://www.coindesk.com/ru/latest-crypto-news)
- AI-обработка через OpenAI API:
  - Удаление гиперссылок и упоминаний источников
  - Редактирование и форматирование текста
- Автоматическая публикация по расписанию в нужный топик группы
- Хранение истории опубликованных статей (SQLite)

## Требования

- Python 3.11+
- Telegram Bot Token ([@BotFather](https://t.me/BotFather))
- OpenAI API Key

## Установка

```bash
git clone <repo_url>
cd botfornewscrypto
pip install -r requirements.txt
cp .env.example .env
# Заполните .env своими значениями
```

## Настройка (.env)

| Переменная | Описание |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `OPENAI_API_KEY` | Ключ OpenAI API |
| `NEWS_CHANNEL_ID` | ID группы/канала (отрицательное число для групп) |
| `NEWS_TOPIC_ID` | ID топика в группе (0 = общий чат) |
| `CHECK_INTERVAL` | Интервал проверки в секундах (по умолчанию 3600) |
| `MAX_ARTICLES_PER_CHECK` | Макс. статей за один цикл (по умолчанию 3) |
| `OPENAI_MODEL` | Модель OpenAI (по умолчанию `gpt-4o-mini`) |
| `ADMIN_IDS` | ID пользователей-администраторов через запятую |

## Запуск

```bash
python bot.py
```

## Команды бота

| Команда | Описание |
|---|---|
| `/start` | Приветственное сообщение |
| `/help` | Список команд |
| `/status` | Текущие настройки и статистика |
| `/fetch` | Вручную запустить сбор новостей |
| `/setchannel <ID>` | Задать ID канала/группы |
| `/settopic <ID>` | Задать ID топика (0 = общий чат) |
| `/setinterval <сек>` | Изменить интервал проверки |
| `/setmax <N>` | Макс. статей за один цикл |

## Как добавить бота в группу с топиками

1. Добавьте бота в группу и выдайте ему права администратора (право публиковать сообщения).
2. Включите «Темы» (Topics) в настройках группы.
3. Узнайте ID группы (например через [@userinfobot](https://t.me/userinfobot)).
4. Откройте нужный топик, перешлите любое сообщение из него боту — в ответ вы получите `message_thread_id`.
5. Задайте настройки: `/setchannel -1001234567890` и `/settopic 5`.

## Структура проекта

```
botfornewscrypto/
├── bot.py            # Точка входа, обработчики команд, планировщик
├── scraper.py        # Сбор статей (RSS + HTTP)
├── ai_processor.py   # Обработка текста через OpenAI
├── storage.py        # SQLite-хранилище опубликованных статей
├── config.py         # Конфигурация из переменных окружения
├── requirements.txt  # Зависимости Python
└── .env.example      # Пример файла с переменными окружения
```
