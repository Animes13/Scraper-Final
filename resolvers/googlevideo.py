# resolvers/googlevideo.py
from resolvers.base import BaseResolver


class GoogleVideoResolver(BaseResolver):
    domains = ["googlevideo.com"]

    def resolve(self, url):
        return [{
            "url": url,
            "headers": {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.blogger.com/"
            },
            "quality": self._guess_quality(url),
            "type": "mp4"
        }]

    def _guess_quality(self, url):
        if "=m37" in url or "1080" in url:
            return "1080p"
        if "=m22" in url or "720" in url:
            return "720p"
        if "=m18" in url:
            return "360p"
        return "auto"