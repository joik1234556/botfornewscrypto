"""
AI-powered article processor.

Supports any OpenAI-compatible API (OpenAI, Groq, Mistral, Together AI,
DeepSeek, OpenRouter, Fireworks, Perplexity, …).  Configure via the
AI_API_KEY and AI_BASE_URL environment variables.

Takes a raw Article and returns a cleaned, Telegram-ready text:
  - Removes hyperlinks and source/author mentions
  - Fixes grammar and formatting
  - Keeps the text concise (≤ 4096 characters for a single Telegram message)
"""

import logging
import re
from typing import Optional

from openai import OpenAI

import config
from scraper import Article

logger = logging.getLogger(__name__)

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        kwargs: dict = {"api_key": config.AI_API_KEY}
        if config.AI_BASE_URL:
            kwargs["base_url"] = config.AI_BASE_URL
        _client = OpenAI(**kwargs)
    return _client


_SYSTEM_PROMPT = """\
Ты редактор криптовалютных новостей для Telegram-канала.

Твои задачи:
1. Переписать статью понятным и читабельным языком на русском.
2. Удалить все гиперссылки (URL-адреса) из текста.
3. Удалить все упоминания источников, авторов и названий СМИ \
   (например «по данным CoinDesk», «сообщает Investing.com», «автор: …» и т.п.).
4. Сохранить все ключевые факты, цифры и даты.
5. Не добавлять собственных суждений или прогнозов.
6. Итоговый текст должен быть не длиннее 3800 символов (включая заголовок).
7. Форматирование: одна пустая строка между абзацами; без маркдауна (никаких *, _, # и т.д.).
8. Первая строка — заголовок статьи заглавными буквами.

Верни только готовый текст без каких-либо пояснений.\
"""


def _build_user_message(article: Article) -> str:
    """Combine article fields into a single prompt message."""
    parts = [f"Заголовок: {article.title}"]
    body = article.body or article.summary
    if body:
        parts.append(f"\nТекст:\n{body}")
    return "\n".join(parts)


def _strip_urls(text: str) -> str:
    """Remove raw URLs as a pre-processing safety step."""
    return re.sub(r"https?://\S+", "", text)


def process_article(article: Article) -> str:
    """
    Send *article* to the OpenAI API for cleaning and formatting.

    Returns the processed text ready for Telegram, or an empty string if
    processing fails.
    """
    user_message = _build_user_message(article)
    if not user_message.strip():
        logger.warning("Article has no content to process: %s", article.url)
        return ""

    try:
        response = _get_client().chat.completions.create(
            model=config.AI_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=1500,
            temperature=0.3,
        )
        result = response.choices[0].message.content or ""
        # Safety pass: strip any URLs the model may have left in
        result = _strip_urls(result)
        return result.strip()
    except Exception as exc:
        logger.error("AI processing failed for '%s': %s", article.title, exc)
        return ""


def format_fallback(article: Article) -> str:
    """
    Build a simple formatted message without AI when processing fails.
    Strips URLs and trims to Telegram's message limit.
    """
    body = _strip_urls(article.body or article.summary or "Текст статьи недоступен.")
    body = re.sub(r"\s+", " ", body).strip()
    text = f"{article.title.upper()}\n\n{body}"
    return text[:4096]
