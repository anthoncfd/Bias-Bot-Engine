import json
import logging
import requests
from app.services.async_fetcher import AsyncRSSFetcher
from app.models import NewsItem
from app.config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

with open('app/config/source_reliability.json') as f:
    RELIABILITY = json.load(f)

class NewsEngine:
    def __init__(self):
        self.gemini_key = GEMINI_API_KEY
        self.use_llm = bool(self.gemini_key)

    async def fetch_async(self, asset: str) -> list[NewsItem]:
        keyword_map = {
            "xauusd": "gold", "xagusd": "silver", "eurusd": "euro",
            "gbpusd": "pound", "audusd": "australian dollar",
            "usdcad": "canadian dollar", "btcusd": "bitcoin",
            "ethusd": "ethereum", "us30": "dow jones", "jp225": "nikkei"
        }
        keyword = keyword_map.get(asset, asset)
        articles = await AsyncRSSFetcher.fetch_all(keyword)
        items = []
        
        for art in articles:
            text = f"Title: {art['title']}\nSummary: {art['summary']}"
            if self.use_llm:
                classification = self._classify_with_gemini(text, asset)
            else:
                classification = self._classify_with_rules(text, asset)
                
            source_rel = self._get_source_reliability(art['source'])
            items.append(NewsItem(
                headline=art['title'],
                source=art['source'],
                asset_mentioned=asset,
                direction=classification['direction'],
                confidence=float(classification['confidence'] * source_rel)
            ))
        return items

    def _get_source_reliability(self, source: str) -> float:
        s = source.lower()
        if 'reuters' in s: return RELIABILITY.get('rss_reuters', 0.85)
        if 'marketwatch' in s: return RELIABILITY.get('rss_marketwatch', 0.75)
        if 'cnbc' in s: return RELIABILITY.get('rss_cnbc', 0.70)
        return 0.60

    def _classify_with_gemini(self, text: str, asset: str) -> dict:
        try:
            # Optimized native structural JSON prompt via raw HTTP post to the Gemini free tier api
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_key}"
            prompt = (
                f"Analyze this news entry for {asset}. Respond ONLY with a valid minified JSON object "
                f"containing keys 'direction' (-1 for bearish, 1 for bullish, 0 for neutral) and "
                f"'confidence' (0.0 to 1.0).\nNews text: {text[:800]}"
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.1
                }
            }
            resp = requests.post(url, json=payload, timeout=5)
            if resp.status_code == 200:
                res_data = resp.json()
                text_out = res_data['candidates'][0]['content']['parts'][0]['text'].strip()
                result = json.loads(text_out)
                return {'direction': int(result.get('direction', 0)), 'confidence': float(result.get('confidence', 0.5))}
            else:
                raise RuntimeError("Gemini connection exception encountered.")
        except Exception as e:
            logger.warning(f"Gemini evaluation failure occurred ({e}). Reverting logic execution parameters back to rules engine.")
            return self._classify_with_rules(text, asset)

    def _classify_with_rules(self, text: str, asset: str) -> dict:
        text_low = text.lower()
        direction = 0
        confidence = 0.5
        
        # Deep financial taxonomy extraction matrix
        bearish_signals = ['concern over slowing', 'hawkish', 'hike rates', 'slowdown', 'drop', 'fall', 'decline', 'crash', 'slump', 'contraction']
        bullish_signals = ['cut rates', 'dovish', 'surge', 'rally', 'jump', 'gain', 'rise', 'bullish', 'expansion', 'stimulus']
        
        bull_hits = sum(1 for w in bullish_signals if w in text_low)
        bear_hits = sum(1 for w in bearish_signals if w in text_low)
        
        if bull_hits > bear_hits:
            direction = 1
            confidence = min(0.85, 0.5 + 0.1 * bull_hits)
        elif bear_hits > bull_hits:
            direction = -1
            confidence = min(0.85, 0.5 + 0.1 * bear_hits)
            
        return {'direction': direction, 'confidence': confidence}

    def score(self, news_items: list[NewsItem]) -> float:
        if not news_items:
            return 0.0
        total = sum(item.direction * item.confidence for item in news_items)
        count = sum(item.confidence for item in news_items)
        return float(max(-1.0, min(1.0, total / count if count > 0 else 0.0)))
