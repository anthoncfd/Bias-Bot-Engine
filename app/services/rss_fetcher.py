import feedparser
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class RSSFetcher:
    FEEDS = {
        "reuters": "https://www.reutersagency.com/feed/?best-topics=business",
        "marketwatch": "https://feeds.content.dowjones.io/public/rss/mw_marketpulse",
        "cnbc": "https://search.cnbc.com/rs/search/combined/search.rss?partnerId=401&keywords=finance",
    }
    
    @classmethod
    def fetch_all(cls, keyword: str = "") -> List[Dict]:
        articles = []
        for name, url in cls.FEEDS.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:8]:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    if keyword and keyword.lower() not in title.lower() and keyword.lower() not in summary.lower():
                        continue
                    articles.append({
                        "title": title,
                        "summary": summary,
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                        "source": name
                    })
            except Exception as e:
                logger.warning(f"Unable to process text ingest for RSS provider matrix '{name}': {e}")
        return articles
