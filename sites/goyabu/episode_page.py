import re
from bs4 import BeautifulSoup

from core.fetcher import Fetcher

BASE = "https://goyabu.io"


class GoyabuEpisodePageScraper:
    """
    - Abre a página do episódio
    - Extrai os links codificados do Goyabu (Blogger)
    - Retorna para o JSON sem resolver o GoogleVideo
    """

    def __init__(self):
        self.fetcher = Fetcher(base_url=BASE)

    # --------------------------------------------------
    def obter_streams(self, episode_url):
        html = self.fetcher.get(episode_url)

        players = self._extract_players_from_buttons(html)

        streams = []

        for player in players:
            # retornamos apenas o link codificado do Blogger
            streams.append({
                "url": player["url"],  # link codificado
                "type": "blogger"
            })

        return streams

    # --------------------------------------------------
    def _extract_players_from_buttons(self, html):
        soup = BeautifulSoup(html, "html.parser")

        players = []
        vistos = set()

        # seleciona todos os botões com link codificado do Blogger
        buttons = soup.select("button.player-tab[data-blogger-url-encrypted]")

        for btn in buttons:
            encrypted = btn.get("data-blogger-url-encrypted")
            if not encrypted:
                continue

            if encrypted in vistos:
                continue

            vistos.add(encrypted)

            # adiciona direto o link codificado
            players.append({
                "url": encrypted,
                "type": "blogger",
                "source": "goyabu"
            })

        return players

    # --------------------------------------------------
    # UTILITÁRIO
    # --------------------------------------------------
    @staticmethod
    def extract_episode_number(text):
        if not text:
            return None
        m = re.search(r"(\d+)", text)
        return int(m.group(1)) if m else None