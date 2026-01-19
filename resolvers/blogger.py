# resolvers/blogger.py
import re
from bs4 import BeautifulSoup

from core.fetcher import Fetcher
from resolvers.base import BaseResolver
from resolvers.googlevideo import GoogleVideoResolver


class BloggerResolver(BaseResolver):
    domains = [
        "blogger.com",
        "blogspot.com"
    ]

    def __init__(self):
        self.fetcher = Fetcher()

    def resolve(self, url):
        html = self.fetcher.get(url)

        # 1️⃣ tenta extrair play_url do script
        sources = self._extract_sources_from_scripts(html)
        if sources:
            return sources

        # 2️⃣ fallback: iframe
        soup = BeautifulSoup(html, "html.parser")
        iframe = soup.find("iframe")
        if iframe and iframe.get("src"):
            return self._resolve_iframe(iframe["src"])

        return []

    # --------------------------------------------------
    def _resolve_iframe(self, src):
        if "blogger" not in src and "blogspot" not in src:
            return []

        html = self.fetcher.get(src)
        return self._extract_sources_from_scripts(html)

    # --------------------------------------------------
    def _extract_sources_from_scripts(self, html):
        streams = []

        # Novo padrão do Blogger: "play_url" em vez de "url"
        matches = re.findall(
            r'"play_url":"(https://[^"]+googlevideo\.com[^"]+)"',
            html
        )

        for m in matches:
            streams.append({
                "url": m.replace("\\u0026", "&"),
                "type": "video"
            })

        return streams