import aiohttp
import asyncio
import feedparser
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class AsyncRSSFetcher:
    FEEDS = {
        "reuters": "https://www.reutersagency.com/feed/?best-topics=business",
        "marketwatch": "https://feeds.content.dowjones.io/public/rss/mw_marketpulse",
        "cnbc": "https://search.cnbc.com/rs/search/combined/search.rss?partnerId=401&keywords=finance",
    }

    @classmethod
    async def fetch_all(cls, keyword: str = "") -> List[Dict]:
        articles = []
        async with aiohttp.ClientSession() as session:
            tasks = [cls._fetch_feed(session, name, url, keyword) for name, url in cls.FEEDS.items()]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, list):
                    articles.extend(res)
        return articles

    @classmethod
    async def _fetch_feed(cls, session, name, url, keyword) -> List[Dict]:
        try:
            async with session.get(url, timeout=8) as resp:
                if resp.status != 200:
                    return []
                text = await resp.text()
                feed = feedparser.parse(text)
                items = []
                for entry in feed.entries[:8]:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    if keyword and keyword.lower() not in title.lower() and keyword.lower() not in summary.lower():
                        continue
                    items.append({
                        "title": title,
                        "summary": summary,
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                        "source": name
                    })
                return items
        except Exception as e:
            logger.debug(f"Async ingestion timed out or threw an exception for source portfolio {name}: {e}")
            return []
