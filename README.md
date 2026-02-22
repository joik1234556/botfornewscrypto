# botfornewscrypto

Telegram-бот для автоматического сбора, AI-обработки и публикации криптовалютных новостей.

## Возможности

- Сбор новостей из трёх источников:
  - [Investing.com (RU)](https://ru.investing.com/news/cryptocurrency-news)
  - [TradingView (RU)](https://ru.tradingview.com/markets/cryptocurrencies/news/)
  - [CoinDesk (RU)](https://www.coindesk.com/ru/latest-crypto-news)
- AI-обработка через любой OpenAI-совместимый API:
  - Удаление гиперссылок и упоминаний источников
  - Редактирование и форматирование текста
  - Поддержка: OpenAI, Groq, Mistral, Together AI, DeepSeek, OpenRouter и другие
- Автоматическая публикация по расписанию в нужный топик группы
- Хранение истории опубликованных статей (SQLite)

## Требования

- Python 3.11+
- Telegram Bot Token ([@BotFather](https://t.me/BotFather))
- API-ключ любого OpenAI-совместимого AI-сервиса

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
| `AI_API_KEY` | API-ключ выбранного AI-провайдера (`OPENAI_API_KEY` также поддерживается) |
| `AI_BASE_URL` | Базовый URL API-провайдера (не задавать для OpenAI) |
| `AI_MODEL` | Название модели (по умолчанию `gpt-4o-mini`) |
| `NEWS_CHANNEL_ID` | ID группы/канала (отрицательное число для групп) |
| `NEWS_TOPIC_ID` | ID топика в группе (0 = общий чат) |
| `CHECK_INTERVAL` | Интервал проверки в секундах (по умолчанию 3600) |
| `MAX_ARTICLES_PER_CHECK` | Макс. статей за один цикл (по умолчанию 3) |
| `ADMIN_IDS` | ID пользователей-администраторов через запятую |

## Поддерживаемые AI-провайдеры

Бот использует OpenAI Python SDK с настраиваемым `base_url`, что обеспечивает
совместимость с любым провайдером, поддерживающим OpenAI Chat Completions API.

| Провайдер | `AI_BASE_URL` | Пример модели |
|---|---|---|
| **OpenAI** (по умолчанию) | *(не задавать)* | `gpt-4o-mini` |
| **Groq** (быстрый, есть бесплатный тариф) | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` |
| **Mistral** | `https://api.mistral.ai/v1` | `mistral-small-latest` |
| **Together AI** | `https://api.together.xyz/v1` | `meta-llama/Llama-3-8b-chat-hf` |
| **DeepSeek** | `https://api.deepseek.com` | `deepseek-chat` |
| **OpenRouter** (100+ моделей) | `https://openrouter.ai/api/v1` | `anthropic/claude-3.5-sonnet` |

Пример конфигурации для Groq:
```env
AI_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
AI_BASE_URL=https://api.groq.com/openai/v1
AI_MODEL=llama-3.3-70b-versatile
```

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
├── ai_processor.py   # Обработка текста через любой OpenAI-совместимый AI API
├── storage.py        # SQLite-хранилище опубликованных статей
├── config.py         # Конфигурация из переменных окружения
├── requirements.txt  # Зависимости Python
└── .env.example      # Пример файла с переменными окружения
```
