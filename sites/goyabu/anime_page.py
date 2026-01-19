# -*- coding: utf-8 -*-
# sites/goyabu/anime_page.py

import re
import json
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from core.fetcher import Fetcher
from core.detector import BreakDetector
from core.validator import Validator
from rules.loader import RuleLoader
from ai.learner import RuleLearner

BASE = "https://goyabu.io"


class GoyabuAnimePageScraper:

    def __init__(self):
        self.fetcher = Fetcher(base_url=BASE)
        self.rules = RuleLoader()
        self.learner = RuleLearner()

    # --------------------------------------------------
    # API PÚBLICA
    # --------------------------------------------------
    def listar_episodios(self, anime_url):
        html = self.fetcher.get(anime_url)

        # 1) MÉTODO CORRETO PARA GOYABU (JS)
        episodios = self._extract_from_js(html)
        if episodios:
            return episodios

        # 2) FALLBACK: RULES (para aprendizado / compatibilidade)
        episodios = self._extract_with_rules(html)

        # 3) SE TUDO FALHAR, IA APRENDE
        if BreakDetector.should_trigger_ai("episode_page", episodios):
            print("⚠️ Episódios não encontrados, acionando IA...")

            # Ajuste: enviar um dict 'context' em vez de dois argumentos
            context = {
                "html": html,
                "stage": "episode_page",
                "url": anime_url
            }
            self.learner.learn(context)

            # Tenta novamente extrair com as regras após aprendizado
            episodios = self._extract_with_rules(html)

        return episodios

    # --------------------------------------------------
    # EXTRAÇÃO DIRETA DO JS (FONTE REAL)
    # --------------------------------------------------
    def _extract_from_js(self, html):
        m = re.search(
            r"const allEpisodes\s*=\s*(\[[\s\S]*?\]);",
            html
        )
        if not m:
            return []

        try:
            data = json.loads(m.group(1).replace("\\/", "/"))
        except Exception:
            return []

        episodios = []
        vistos = set()

        for ep in data:
            ep_id = ep.get("id")
            if not ep_id:
                continue

            try:
                numero = int(ep.get("episodio", 0))
            except Exception:
                numero = None

            link = f"{BASE}/{ep_id}"
            if link in vistos:
                continue
            vistos.add(link)

            item = {
                "titulo": f"Episódio {numero}" if numero else None,
                "numero": numero,
                "audio": ep.get("audio"),
                "link": link,
                "id": ep_id
            }

            if Validator.episode_item(item):
                episodios.append(item)

        episodios.sort(key=lambda x: x.get("numero") or 0)
        return episodios

    # --------------------------------------------------
    # EXTRAÇÃO POR REGRAS (FALLBACK / IA)
    # --------------------------------------------------
    def _extract_with_rules(self, html):
        soup = BeautifulSoup(html, "html.parser")
        strategies = self.rules.get_strategies("episode_page.json")

        for strat in strategies:
            eps = self._apply_strategy(soup, strat)

            if eps:
                self.rules.update_score(
                    "episode_page.json",
                    strat.get("name"),
                    +0.05
                )
                return eps
            else:
                self.rules.update_score(
                    "episode_page.json",
                    strat.get("name"),
                    -0.05
                )

        return []

    # --------------------------------------------------
    # APLICA UMA STRATEGY
    # --------------------------------------------------
    def _apply_strategy(self, soup, strat):
        selector = strat.get("selector")
        fields = strat.get("fields")

        if not selector or not fields:
            return []

        items = soup.select(selector)
        episodios = []
        vistos = set()

        for item in items:
            ep = {}

            for name, rule in fields.items():
                el = item.select_one(rule.get("selector"))
                if not el:
                    ep = {}
                    break

                if rule.get("type") == "text":
                    ep[name] = el.get_text(" ", strip=True)

                elif rule.get("type") == "css":
                    ep[name] = el.get(rule.get("attr"))

            if not ep:
                continue

            if "link" in ep:
                ep["link"] = urljoin(BASE, ep["link"])

            if not Validator.episode_item(ep):
                continue

            ep["numero"] = self._extract_number(ep.get("titulo"))

            if ep["link"] in vistos:
                continue
            vistos.add(ep["link"])

            episodios.append(ep)

        return episodios

    # --------------------------------------------------
    # EXTRAI NÚMERO DO EPISÓDIO
    # --------------------------------------------------
    def _extract_number(self, text):
        if not text:
            return None

        m = re.search(r"(\d+)", text)
        return int(m.group(1)) if m else None