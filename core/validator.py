# core/validator.py
import re

class Validator:

    @staticmethod
    def title(text):
        if not text:
            return False
        if not isinstance(text, str):
            return False
        if len(text) < 2 or len(text) > 120:
            return False
        return True

    # -------------------------
    # ANIME
    # -------------------------
    @staticmethod
    def anime_item(item):
        if not isinstance(item, dict):
            return False

        if not Validator.title(item.get("titulo")):
            return False

        if not item.get("link", "").startswith("http"):
            return False

        return True

    # -------------------------
    # EPISÓDIO
    # -------------------------
    @staticmethod
    def episode_item(item):
        """
        Valida item de episódio
        Usado em anime_page.py
        """
        if not isinstance(item, dict):
            return False

        if not Validator.title(item.get("titulo")):
            return False

        link = item.get("link", "")
        if not link or not link.startswith("http"):
            return False

        return True

    @staticmethod
    def episode_number(value):
        try:
            n = int(value)
            return n > 0
        except:
            return False

    # -------------------------
    # PLAYERS / STREAMS
    # -------------------------
    @staticmethod
    def player_url(url):
        """
        Usado em episode_page.py
        """
        if not url:
            return False

        if not isinstance(url, str):
            return False

        if not url.startswith("http"):
            return False

        return True

    @staticmethod
    def googlevideo(url):
        if not url:
            return False
        return "googlevideo.com" in url

    @staticmethod
    def blogger(url):
        if not url:
            return False
        return "blogger.com" in url