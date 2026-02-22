"""Configuration management for the crypto news bot."""

import os
from dotenv import load_dotenv

load_dotenv()


def _get_required(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"Required environment variable '{key}' is not set.")
    return value


def _get_int_list(key: str, default: str = "") -> list[int]:
    raw = os.getenv(key, default)
    if not raw.strip():
        return []
    result = []
    for x in raw.split(","):
        x = x.strip()
        if not x:
            continue
        try:
            result.append(int(x))
        except ValueError:
            raise EnvironmentError(
                f"Invalid value '{x}' in '{key}': expected a comma-separated list of integers."
            )
    return result


# Telegram
TELEGRAM_BOT_TOKEN: str = _get_required("TELEGRAM_BOT_TOKEN")
NEWS_CHANNEL_ID: int = int(os.getenv("NEWS_CHANNEL_ID", "0"))
NEWS_TOPIC_ID: int = int(os.getenv("NEWS_TOPIC_ID", "0"))
ADMIN_IDS: list[int] = _get_int_list("ADMIN_IDS")

# OpenAI
OPENAI_API_KEY: str = _get_required("OPENAI_API_KEY")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Scheduler
CHECK_INTERVAL: int = int(os.getenv("CHECK_INTERVAL", "3600"))
MAX_ARTICLES_PER_CHECK: int = int(os.getenv("MAX_ARTICLES_PER_CHECK", "3"))

# News sources: list of (name, rss_url, site_url)
NEWS_SOURCES: list[dict] = [
    {
        "name": "Investing.com",
        "rss_url": "https://ru.investing.com/rss/news_285.rss",
        "site_url": "https://ru.investing.com/news/cryptocurrency-news",
    },
    {
        "name": "TradingView",
        "rss_url": "https://ru.tradingview.com/markets/cryptocurrencies/news/",
        "site_url": "https://ru.tradingview.com/markets/cryptocurrencies/news/",
    },
    {
        "name": "CoinDesk",
        "rss_url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "site_url": "https://www.coindesk.com/ru/latest-crypto-news",
    },
]
