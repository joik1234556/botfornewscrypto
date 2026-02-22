"""
Main Telegram bot for crypto news collection and posting.

Commands (admin-only unless otherwise noted):
  /start        – welcome message
  /help         – show available commands
  /status       – show current bot configuration
  /fetch        – manually trigger a news fetch & post cycle
  /setchannel   – set the target channel/group ID
  /settopic     – set the topic (message_thread_id) inside the group
  /setinterval  – set automatic check interval in seconds
"""

import logging
import html
import functools
from typing import Optional

from telegram import Update, Bot
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from telegram.error import TelegramError

import config
import storage
from scraper import Article, fetch_all_articles, enrich_article
from ai_processor import process_article, format_fallback

logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Runtime-configurable settings (can be changed via bot commands)
_settings: dict = {
    "channel_id": config.NEWS_CHANNEL_ID,
    "topic_id": config.NEWS_TOPIC_ID,
    "interval": config.CHECK_INTERVAL,
    "max_articles": config.MAX_ARTICLES_PER_CHECK,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_admin(user_id: int) -> bool:
    return not config.ADMIN_IDS or user_id in config.ADMIN_IDS


def _admin_only(func):
    """Decorator that rejects non-admin users."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user and not _is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ У вас нет прав для этой команды.")
            return
        return await func(update, context)
    return wrapper


async def _post_article(bot: Bot, article: Article) -> bool:
    """
    Enrich, process with AI, and post *article* to the configured channel.
    Returns True on success.
    """
    channel_id = _settings["channel_id"]
    topic_id = _settings["topic_id"]

    if not channel_id:
        logger.warning("No target channel configured – skipping post.")
        return False

    enrich_article(article)
    text = process_article(article)
    if not text:
        text = format_fallback(article)
    if not text:
        return False

    # Telegram message limit is 4096 chars
    text = text[:4096]

    try:
        kwargs: dict = {
            "chat_id": channel_id,
            "text": text,
            "parse_mode": None,
        }
        if topic_id:
            kwargs["message_thread_id"] = topic_id

        await bot.send_message(**kwargs)
        storage.mark_posted(article.url, article.title)
        logger.info("Posted: %s", article.title)
        return True
    except TelegramError as exc:
        logger.error("Telegram error posting '%s': %s", article.title, exc)
        return False


# ---------------------------------------------------------------------------
# Scheduled job
# ---------------------------------------------------------------------------


async def _scheduled_fetch(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodic job: fetch new articles and post them."""
    logger.info("Running scheduled news fetch …")
    articles = fetch_all_articles(max_per_source=20)
    posted = 0
    for article in articles:
        if posted >= _settings["max_articles"]:
            break
        if storage.is_posted(article.url):
            continue
        success = await _post_article(context.bot, article)
        if success:
            posted += 1
    logger.info("Scheduled fetch done – posted %d article(s).", posted)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Привет! Я бот для сбора крипто-новостей.\n"
        "Используйте /help для просмотра команд."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 <b>Доступные команды</b>\n\n"
        "/status — текущие настройки бота\n"
        "/fetch — вручную запустить сбор и публикацию новостей\n"
        "/setchannel &lt;ID&gt; — задать ID канала/группы (например -1001234567890)\n"
        "/settopic &lt;ID&gt; — задать ID топика в группе (0 = общий чат)\n"
        "/setinterval &lt;секунды&gt; — интервал автоматической проверки\n"
        "/setmax &lt;число&gt; — максимум статей за один цикл",
        parse_mode=ParseMode.HTML,
    )


@_admin_only
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    count = storage.get_posted_count()
    topic = _settings["topic_id"] or "нет (общий чат)"
    channel = _settings["channel_id"] or "не задан"
    await update.message.reply_text(
        f"⚙️ <b>Настройки бота</b>\n\n"
        f"Канал/группа: <code>{html.escape(str(channel))}</code>\n"
        f"Топик: <code>{html.escape(str(topic))}</code>\n"
        f"Интервал проверки: {_settings['interval']} сек.\n"
        f"Макс. статей за цикл: {_settings['max_articles']}\n"
        f"Опубликовано всего: {count}",
        parse_mode=ParseMode.HTML,
    )


@_admin_only
async def cmd_fetch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🔍 Начинаю сбор новостей …")
    articles = fetch_all_articles(max_per_source=20)
    posted = 0
    skipped = 0
    for article in articles:
        if posted >= _settings["max_articles"]:
            break
        if storage.is_posted(article.url):
            skipped += 1
            continue
        success = await _post_article(context.bot, article)
        if success:
            posted += 1
    await update.message.reply_text(
        f"✅ Готово. Опубликовано: {posted}, пропущено (уже было): {skipped}."
    )


@_admin_only
async def cmd_setchannel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Использование: /setchannel <ID>")
        return
    try:
        channel_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID должен быть целым числом.")
        return
    _settings["channel_id"] = channel_id
    await update.message.reply_text(f"✅ Канал установлен: <code>{channel_id}</code>", parse_mode=ParseMode.HTML)


@_admin_only
async def cmd_settopic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Использование: /settopic <ID>  (0 = общий чат)")
        return
    try:
        topic_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID должен быть целым числом.")
        return
    _settings["topic_id"] = topic_id
    label = str(topic_id) if topic_id else "общий чат"
    await update.message.reply_text(f"✅ Топик установлен: <code>{html.escape(label)}</code>", parse_mode=ParseMode.HTML)


@_admin_only
async def cmd_setinterval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Использование: /setinterval <секунды>")
        return
    try:
        interval = int(context.args[0])
        if interval < 60:
            raise ValueError("Too short")
    except ValueError:
        await update.message.reply_text("❌ Интервал должен быть целым числом ≥ 60.")
        return
    _settings["interval"] = interval
    # Reschedule the periodic job
    jobs = context.job_queue.get_jobs_by_name("news_fetch")
    for job in jobs:
        job.schedule_removal()
    context.job_queue.run_repeating(
        _scheduled_fetch, interval=interval, first=interval, name="news_fetch"
    )
    await update.message.reply_text(f"✅ Интервал обновлён: {interval} сек.")


@_admin_only
async def cmd_setmax(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Использование: /setmax <число>")
        return
    try:
        max_art = int(context.args[0])
        if max_art < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Значение должно быть целым числом ≥ 1.")
        return
    _settings["max_articles"] = max_art
    await update.message.reply_text(f"✅ Максимум статей за цикл: {max_art}.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    app = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .build()
    )

    # Register command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("fetch", cmd_fetch))
    app.add_handler(CommandHandler("setchannel", cmd_setchannel))
    app.add_handler(CommandHandler("settopic", cmd_settopic))
    app.add_handler(CommandHandler("setinterval", cmd_setinterval))
    app.add_handler(CommandHandler("setmax", cmd_setmax))

    # Schedule periodic fetch
    app.job_queue.run_repeating(
        _scheduled_fetch,
        interval=_settings["interval"],
        first=10,
        name="news_fetch",
    )

    logger.info("Bot started. Polling …")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
