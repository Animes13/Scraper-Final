# core/fetcher.py
import time
import random
import requests

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
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
        # Delay aleatório entre requisições para não ser bloqueado
        time.sleep(random.uniform(0.8, 1.8))

    # --------------------------------------------------
    def get(self, url, headers=None, timeout=None):
        """
        Faz GET de uma URL com retries, timeout e headers opcionais.
        """
        last_error = None
        timeout = timeout or self.timeout
        req_headers = headers or self.headers

        for attempt in range(1, self.retries + 1):
            try:
                self._delay()
                r = self.session.get(url, headers=req_headers, timeout=timeout)
                r.raise_for_status()
                return r.text
            except requests.exceptions.RequestException as e:
                last_error = e
                print(f"⚠️ Fetcher GET tentativa {attempt} falhou: {e}")
                if attempt == self.retries:
                    raise RuntimeError(f"❌ Fetcher erro ao acessar {url}: {last_error}")

    # --------------------------------------------------
    def get_json(self, url, headers=None, timeout=None):
        """
        Faz GET de uma URL que retorna JSON, com retries e timeout.
        """
        last_error = None
        timeout = timeout or self.timeout
        req_headers = headers or self.headers

        for attempt in range(1, self.retries + 1):
            try:
                self._delay()
                r = self.session.get(url, headers=req_headers, timeout=timeout)
                r.raise_for_status()
                return r.json()
            except requests.exceptions.RequestException as e:
                last_error = e
                print(f"⚠️ Fetcher JSON tentativa {attempt} falhou: {e}")
                if attempt == self.retries:
                    raise RuntimeError(f"❌ Fetcher JSON erro {url}: {last_error}")