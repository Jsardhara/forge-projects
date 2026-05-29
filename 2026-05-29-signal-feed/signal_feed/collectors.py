"""Signal collectors — pull data from free RSS feeds and APIs.

Sources:
- Crypto news: CoinDesk, Cointelegraph RSS
- General news: Reuters, Bloomberg RSS
- Reddit: CryptoMarkets, wallstreetbets hot posts (public JSON)
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

import httpx
import feedparser
import structlog

from .analyzer import score_sentiment, classify_category
from .database import Signal

logger = structlog.get_logger(__name__)

RSS_FEEDS = {
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "cointelegraph": "https://cointelegraph.com/rss",
    "decrypt": "https://decrypt.co/feed",
    " bitcoinist": "https://bitcoinist.com/feed/",
}

REDDIT_FEEDS = [
    "CryptoCurrency",
    "CryptoMarkets",
    "wallstreetbets",
    "stocks",

    "SecurityAnalysis",
]


async def fetch_rss(
    client: httpx.AsyncClient,
    source_name: str,
    url: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Fetch and parse an RSS feed."""
    try:
        resp = await client.get(url, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)

        items = []
        for entry in feed.entries[:limit]:
            title = entry.get("title", "")
            summary = entry.get("summary", entry.get("description", ""))
            link = entry.get("link", "")
            score, label = score_sentiment(f"{title} {summary}")
            category = classify_category(f"{title} {summary}")

            items.append({
                "source": source_name,
                "category": category,
                "title": title[:500],
                "url": link[:1000],
                "summary": summary[:2000] if summary else None,
                "signal_score": score,
                "sentiment_label": label,
                "raw_score": score,
                "metadata_json": json.dumps({"feed_type": "rss", "parser": "feedparser"}),
                "created_at": datetime.now(timezone.utc),
            })

        logger.info("rss_fetched", source=source_name, count=len(items))
        return items

    except Exception as e:
        logger.error("rss_fetch_failed", source=source_name, error=str(e))
        return []


async def fetch_reddit(
    client: httpx.AsyncClient,
    subreddit: str,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Fetch hot posts from a subreddit via public JSON API."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    headers = {"User-Agent": "SignalFeedBot/0.1 (by Jarmes)"}

    try:
        resp = await client.get(url, timeout=15, headers=headers, follow_redirects=True)
        if resp.status_code != 200:
            logger.warning("reddit_non_200", subreddit=subreddit, status=resp.status_code)
            return []
        data = resp.json()

        items = []
        for post in data.get("data", {}).get("children", []):
            p = post.get("data", {})
            title = p.get("title", "")
            selftext = p.get("selftext", "")
            score_val = p.get("score", 0)
            num_comments = p.get("num_comments", 0)
            combined = f"{title} {selftext}"
            sentiment_score, label = score_sentiment(combined)
            category = classify_category(combined)

            # Boost signal score based on engagement
            engagement_boost = min(0.2, (score_val / 10000) * 0.1 + (num_comments / 500) * 0.1)
            adjusted_score = max(-1.0, min(1.0, sentiment_score + engagement_boost * (1 if sentiment_score >= 0 else -1)))

            items.append({
                "source": f"reddit/r/{subreddit}",
                "category": category,
                "title": title[:500],
                "url": f"https://reddit.com{p.get('permalink', '')}"[:1000],
                "summary": selftext[:1000] if selftext else None,
                "signal_score": round(adjusted_score, 3),
                "sentiment_label": label,
                "raw_score": sentiment_score,
                "metadata_json": json.dumps({
                    "feed_type": "reddit",
                    "subreddit": subreddit,
                    "upvotes": score_val,
                    "comments": num_comments,
                }),
                "created_at": datetime.now(timezone.utc),
            })

        logger.info("reddit_fetched", subreddit=subreddit, count=len(items))
        return items

    except Exception as e:
        logger.error("reddit_fetch_failed", subreddit=subreddit, error=str(e))
        return []


async def collect_all() -> list[dict[str, Any]]:
    """Run all collectors and return combined signal list."""
    all_signals: list[dict[str, Any]] = []

    async with httpx.AsyncClient() as client:
        rss_tasks = [
            fetch_rss(client, name, url)
            for name, url in RSS_FEEDS.items()
        ]
        reddit_tasks = [
            fetch_reddit(client, sub)
            for sub in REDDIT_FEEDS
        ]

        results = await asyncio.gather(*(rss_tasks + reddit_tasks), return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_signals.extend(result)
            elif isinstance(result, Exception):
                logger.error("collector_error", error=str(result))

    logger.info("collection_complete", total_signals=len(all_signals))
    return all_signals
