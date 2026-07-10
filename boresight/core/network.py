"""
Asynchronous Network Engine for BoreSight.
Handles proxy rotation, user-agent injection, and resilient HTTP fetching.
"""

import random
import multiprocessing
from typing import List, Optional
import httpx


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
]


class ProxyRotator:
    """Thread-safe round-robin proxy rotator."""

    def __init__(self, proxies: List[str]):
        self._proxies = proxies
        self._index = 0
        self._lock = multiprocessing.Lock()

    def get_proxy(self) -> Optional[str]:
        """Returns the next proxy in a round-robin fashion."""
        if not self._proxies:
            return None
        with self._lock:
            proxy = self._proxies[self._index]
            self._index = (self._index + 1) % len(self._proxies)
            return proxy


class AsyncNetworkClient:
    """Wrapper around httpx with proxy rotation and user-agent injection."""

    def __init__(self, proxy_rotator: Optional[ProxyRotator] = None, timeout: int = 15):
        self.proxy_rotator = proxy_rotator
        self.timeout = timeout

    async def fetch(self, url: str) -> httpx.Response:
        """
        Fetches the target URL asynchronously.
        Handles dynamic User-Agent and proxy rotation.
        """
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        proxies: Optional[str] = None
        
        if self.proxy_rotator:
            proxy_url = self.proxy_rotator.get_proxy()
            if proxy_url:
                proxies = proxy_url

        try:
            async with httpx.AsyncClient(proxies=proxies, timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 429:
                    raise httpx.HTTPStatusError("Rate Limit Exceeded (429)", request=response.request, response=response)
                elif response.status_code == 403:
                    raise httpx.HTTPStatusError("Forbidden (403)", request=response.request, response=response)
                    
                response.raise_for_status()
                return response
        except httpx.RequestError as exc:
            raise RuntimeError(f"An error occurred while requesting {exc.request.url!r}: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.") from exc
