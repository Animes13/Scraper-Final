# core/fetcher.py
import time
import random
import requests

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Android; Termux)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
}

class Fetcher:
    def __init__(self, base_url=None, headers=None, timeout=20, retries=3):
        self.base_url = base_url
        self.headers = headers or DEFAULT_HEADERS
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _delay(self):
        time.sleep(random.uniform(0.8, 1.8))

    def get(self, url):
        last_error = None

        for attempt in range(1, self.retries + 1):
            try:
                self._delay()
                r = self.session.get(url, timeout=self.timeout)
                r.raise_for_status()
                return r.text
            except Exception as e:
                last_error = e

        raise RuntimeError(f"Fetcher erro ao acessar {url}: {last_error}")

    def get_json(self, url):
        last_error = None

        for attempt in range(1, self.retries + 1):
            try:
                self._delay()
                r = self.session.get(url, timeout=self.timeout)
                r.raise_for_status()
                return r.json()
            except Exception as e:
                last_error = e

        raise RuntimeError(f"Fetcher JSON erro {url}: {last_error}")