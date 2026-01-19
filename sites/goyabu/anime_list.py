# sites/goyabu/anime_list.py
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from core.fetcher import Fetcher
from core.detector import BreakDetector
from core.validator import Validator
from rules.loader import RuleLoader
from ai.learner import RuleLearner

BASE = "https://goyabu.io"


class GoyabuAnimeListScraper:

    def __init__(self):
        self.fetcher = Fetcher(base_url=BASE)
        self.rules = RuleLoader()
        self.learner = RuleLearner()

    # --------------------------------------------------
    # API PÃBLICA
    # --------------------------------------------------
    def listar(self, pagina=1):
        url = f"{BASE}/lista-de-animes/page/{pagina}?l=todos&pg={pagina}"
        html = self.fetcher.get(url)

        animes = self._extract_with_rules(html)

        # ð fallback inteligente com IA
        if BreakDetector.should_trigger_ai("anime_list", animes):
            print("â ï¸ Regras falharam, acionando IA para aprender...")
            self.learner.learn(html, "anime_list")
            animes = self._extract_with_rules(html)

        return animes

    # --------------------------------------------------
    # EXTRAÃÃO BASEADA EM REGRAS
    # --------------------------------------------------
    def _extract_with_rules(self, html):
        soup = BeautifulSoup(html, "html.parser")
        strategies = self.rules.get_strategies("anime_list.json")

        for strat in strategies:
            results = self._apply_strategy(soup, strat)

            if results:
                self.rules.update_score(
                    "anime_list.json",
                    strat.get("name"),
                    +0.05
                )
                return results
            else:
                self.rules.update_score(
                    "anime_list.json",
                    strat.get("name"),
                    -0.05
                )

        return []

    # --------------------------------------------------
    # APLICA UMA STRATEGY
    # --------------------------------------------------
    def _apply_strategy(self, soup, strat):
        selector = strat.get("selector")
        fields = strat.get("fields", {})

        if not selector or not fields:
            return []

        cards = soup.select(selector)
        animes = []
        vistos = set()

        for card in cards:
            item = {}

            for name, rule in fields.items():
                el = card.select_one(rule.get("selector"))
                if not el:
                    item = {}
                    break

                if rule.get("type") == "text":
                    item[name] = el.get_text(" ", strip=True)

                elif rule.get("type") == "css":
                    attr = rule.get("attr")
                    item[name] = el.get(attr)

            if not item:
                continue

            # ð normaliza link
            if "link" in item:
                item["link"] = urljoin(BASE, item["link"])

            # valida estrutura mÃ­nima
            if not Validator.anime_item(item):
                continue

            # evita duplicados
            if item["link"] in vistos:
                continue
            vistos.add(item["link"])

            item = self._normalize_item(item)
            animes.append(item)

        return animes

    # --------------------------------------------------
    # NORMALIZA TITULO / TIPO / NOTA
    # --------------------------------------------------
    def _normalize_item(self, item):
        texto = item.get("titulo", "")

        nota_m = re.search(r"(\d\.\d)", texto)
        nota = nota_m.group(1) if nota_m else "N/A"

        tipo = "Dublado" if "Dublado" in texto else "Legendado"

        titulo = texto.replace("Dublado", "").replace("Legendado", "")
        if nota != "N/A":
            titulo = titulo.replace(nota, "")

        titulo = re.sub(r"\s{2,}", " ", titulo).strip()

        item["titulo"] = titulo
        item["tipo"] = tipo
        item["nota"] = nota

        return item