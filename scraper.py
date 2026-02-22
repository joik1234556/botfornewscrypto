"""
News scraper for crypto news sources.

Fetches article lists via RSS when available, then retrieves the full article
body via HTTP for sources that provide only excerpts in their feed.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import feedparser
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Common browser-like headers to reduce bot-detection rejections
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

# Seconds to wait for HTTP responses
_TIMEOUT = 15

# Shared HTTP client – reused across all requests to improve performance
_http_client = httpx.Client(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True)


@dataclass
class Article:
    title: str
    url: str
    source: str
    summary: str = ""
    body: str = ""
    tags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fetch_html(url: str) -> Optional[str]:
    """Retrieve raw HTML from *url*, return None on failure."""
    try:
        resp = _http_client.get(url)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None


def _clean_text(text: str) -> str:
    """Strip extra whitespace from *text*."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_article_body(url: str) -> str:
    """
    Download the page at *url* and extract the main article text using
    BeautifulSoup heuristics.  Returns an empty string on failure.
    """
    html = _fetch_html(url)
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")

    # Remove script / style / nav / footer noise
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    # Priority selectors for main content (ordered from most to least specific)
    candidates = [
        soup.find("article"),
        soup.find(class_=re.compile(r"article[-_]?(body|content|text)", re.I)),
        soup.find(class_=re.compile(r"(post|entry)[-_]?(body|content|text)", re.I)),
        soup.find(id=re.compile(r"article[-_]?(body|content|text)", re.I)),
        soup.find("main"),
    ]

    for candidate in candidates:
        if candidate:
            paragraphs = candidate.find_all("p")
            if paragraphs:
                text = " ".join(_clean_text(p.get_text()) for p in paragraphs if p.get_text(strip=True))
                if len(text) > 200:
                    return text

    # Fallback: collect all <p> tags from the whole page
    paragraphs = soup.find_all("p")
    text = " ".join(_clean_text(p.get_text()) for p in paragraphs if p.get_text(strip=True))
    return text


# ---------------------------------------------------------------------------
# Per-source scrapers
# ---------------------------------------------------------------------------


def _scrape_rss(rss_url: str, source_name: str, max_items: int = 20) -> list[Article]:
    """Generic RSS scraper – works for any standard RSS/Atom feed."""
    articles: list[Article] = []
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:max_items]:
            url = entry.get("link", "")
            title = _clean_text(entry.get("title", ""))
            summary = _clean_text(BeautifulSoup(entry.get("summary", ""), "lxml").get_text())
            tags = [t.get("term", "") for t in entry.get("tags", [])]
            if url and title:
                articles.append(
                    Article(
                        title=title,
                        url=url,
                        source=source_name,
                        summary=summary,
                        tags=tags,
                    )
                )
    except Exception as exc:
        logger.warning("RSS fetch failed for %s: %s", rss_url, exc)
    return articles


def _scrape_coindesk_ru(max_items: int = 20) -> list[Article]:
    """
    CoinDesk Russian edition.  Try the global RSS feed first; filter to crypto.
    """
    articles = _scrape_rss(
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "CoinDesk",
        max_items,
    )
    if articles:
        return articles

    # Fallback: scrape the listing page
    html = _fetch_html("https://www.coindesk.com/ru/latest-crypto-news")
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    result: list[Article] = []
    for a_tag in soup.select("a[href]")[:max_items * 3]:
        href = a_tag.get("href", "")
        if "/ru/" not in href:
            continue
        title = _clean_text(a_tag.get_text())
        if not title or len(title) < 10:
            continue
        url = href if href.startswith("http") else f"https://www.coindesk.com{href}"
        if any(art.url == url for art in result):
            continue
        result.append(Article(title=title, url=url, source="CoinDesk"))
        if len(result) >= max_items:
            break
    return result


def _scrape_tradingview_ru(max_items: int = 20) -> list[Article]:
    """
    TradingView doesn't provide a standard RSS feed for its news section.
    Scrape the listing page for article links.
    """
    html = _fetch_html("https://ru.tradingview.com/markets/cryptocurrencies/news/")
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    result: list[Article] = []
    seen: set[str] = set()

    for a_tag in soup.find_all("a", href=True):
        href: str = a_tag["href"]
        if "/news/" not in href:
            continue
        url = href if href.startswith("http") else f"https://ru.tradingview.com{href}"
        if url in seen:
            continue
        seen.add(url)
        title = _clean_text(a_tag.get_text())
        if not title or len(title) < 10:
            continue
        result.append(Article(title=title, url=url, source="TradingView"))
        if len(result) >= max_items:
            break
    return result


def _scrape_investing_ru(max_items: int = 20) -> list[Article]:
    """
    Investing.com Russian edition – use their crypto RSS feed.
    Falls back to HTML scraping if the feed is unavailable.
    """
    articles = _scrape_rss(
        "https://ru.investing.com/rss/news_285.rss",
        "Investing.com",
        max_items,
    )
    if articles:
        return articles

    html = _fetch_html("https://ru.investing.com/news/cryptocurrency-news")
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    result: list[Article] = []
    seen: set[str] = set()

    for a_tag in soup.find_all("a", href=True):
        href: str = a_tag["href"]
        if "/news/" not in href:
            continue
        url = href if href.startswith("http") else f"https://ru.investing.com{href}"
        if url in seen:
            continue
        seen.add(url)
        title = _clean_text(a_tag.get_text())
        if not title or len(title) < 15:
            continue
        result.append(Article(title=title, url=url, source="Investing.com"))
        if len(result) >= max_items:
            break
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_all_articles(max_per_source: int = 20) -> list[Article]:
    """
    Fetch articles from all three sources and return a combined list.
    Articles are interleaved (one from each source at a time) so the feed
    stays balanced.
    """
    pools = [
        _scrape_investing_ru(max_per_source),
        _scrape_tradingview_ru(max_per_source),
        _scrape_coindesk_ru(max_per_source),
    ]

    combined: list[Article] = []
    max_len = max((len(p) for p in pools), default=0)
    for i in range(max_len):
        for pool in pools:
            if i < len(pool):
                combined.append(pool[i])
    return combined


def enrich_article(article: Article) -> Article:
    """
    Download and attach the full article body to *article*.
    Returns the same object (mutated in place) for convenience.
    """
    if not article.body:
        article.body = _extract_article_body(article.url)
    return article
