import httpx
from app.logger import logger

class BaseAsyncClient:
    """An abstract foundational client handling structured, safe asynchronous HTTP operations."""
    
    def __init__(self, base_url: str, default_params: dict = None):
        self.base_url = base_url
        self.default_params = default_params or {}

    async def _get(self, endpoint: str, params: dict = None) -> dict | None:
        combined_params = {**self.default_params, **(params or {})}
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        async with httpx.AsyncClient(timeout=12.0) as client:
            try:
                response = await client.get(url, params=combined_params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                logger.error(f"HTTP upstream failure response received from {url}: {exc.response.status_code}")
                return None
            except httpx.RequestError as exc:
                logger.error(f"Network transport level connection anomaly occurred while hitting {url}: {exc}")
                return None
