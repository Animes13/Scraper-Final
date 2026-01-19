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
        # Inicializa o fetcher com base URL
        self.fetcher = Fetcher(base_url=BASE)

    # --------------------------------------------------
    def obter_streams(self, episode_url, retries=3, timeout=10):
        """
        Obtém links de um episódio com retries, timeout e User-Agent.
        Retorna lista de streams mesmo se houver falha parcial.
        """
        html = None
        for attempt in range(1, retries + 1):
            try:
                html = self.fetcher.get(
                    episode_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                                      "Chrome/120.0.0.0 Safari/537.36"
                    },
                    timeout=timeout
                )
                if html:
                    break
            except Exception as e:
                print(f"⚠️ Tentativa {attempt} falhou: {e}")
                if attempt == retries:
                    print("❌ Não foi possível obter o episódio após várias tentativas")
                    return []

        # Extrai os players do HTML
        players = self._extract_players_from_buttons(html)
        streams = []

        for player in players:
            # Retornamos apenas o link codificado do Blogger
            streams.append({
                "url": player["url"],  # link codificado
                "type": "blogger"
            })

        return streams

    # --------------------------------------------------
    def _extract_players_from_buttons(self, html):
        """
        Extrai todos os links codificados de botões de player do HTML
        """
        soup = BeautifulSoup(html, "html.parser")

        players = []
        vistos = set()

        # Seleciona todos os botões com link codificado do Blogger
        buttons = soup.select("button.player-tab[data-blogger-url-encrypted]")

        for btn in buttons:
            encrypted = btn.get("data-blogger-url-encrypted")
            if not encrypted or encrypted in vistos:
                continue

            vistos.add(encrypted)

            # Adiciona direto o link codificado
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
        """
        Extrai número do episódio de uma string
        """
        if not text:
            return None
        m = re.search(r"(\d+)", text)
        return int(m.group(1)) if m else None