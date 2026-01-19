# ai/learner.py
from copy import deepcopy

from ai.gemini import GeminiClient
from rules.loader import RuleLoader
from core.validator import Validator


class RuleLearner:
    """
    Responsável por:
    - chamar Gemini quando o scraper quebra
    - validar regras geradas
    - converter para formato interno
    - salvar no rules/
    """

    def __init__(self):
        self.gemini = GeminiClient()
        self.loader = RuleLoader()

    # --------------------------------------------------
    # API PRINCIPAL
    # --------------------------------------------------
    def learn(self, html, context):
        """
        context:
            anime_list
            anime_page
            episode_page
        """
        raw_rule = self.gemini.analyze_html(html, context)

        strategy = self._normalize_strategy(raw_rule, context)
        if not strategy:
            raise RuntimeError("IA retornou regra inválida")

        self._save_strategy(context, strategy)
        return strategy

    # --------------------------------------------------
    # NORMALIZA REGRA DA IA
    # --------------------------------------------------
    def _normalize_strategy(self, data, context):
        if not isinstance(data, dict):
            return None

        if context == "anime_list":
            return self._normalize_anime_list(data)

        if context == "anime_page":
            return self._normalize_anime_page(data)

        if context == "episode_page":
            return self._normalize_episode_page(data)

        return None

    # --------------------------------------------------
    # LISTA DE ANIMES
    # --------------------------------------------------
    def _normalize_anime_list(self, data):
        card = data.get("card") or data.get("cards") or data
        selector = card.get("selector")
        title_sel = card.get("title")
        link_sel = card.get("link")

        if not selector or not title_sel or not link_sel:
            return None

        return {
            "name": "ai_generated_anime_list",
            "selector": selector,
            "fields": {
                "titulo": {
                    "type": "text",
                    "selector": title_sel
                },
                "link": {
                    "type": "css",
                    "selector": link_sel,
                    "attr": "href"
                }
            },
            "score": 0.6
        }

    # --------------------------------------------------
    # PÁGINA DO ANIME
    # --------------------------------------------------
    def _normalize_anime_page(self, data):
        pattern = data.get("pattern")
        if not pattern or "allEpisodes" not in pattern:
            return None

        return {
            "name": "ai_generated_anime_page",
            "type": "regex",
            "pattern": pattern,
            "score": 0.6
        }

    # --------------------------------------------------
    # PÁGINA DO EPISÓDIO
    # --------------------------------------------------
    def _normalize_episode_page(self, data):
        selector = data.get("selector")
        attr = data.get("attr") or "data-blogger-url-encrypted"

        if not selector:
            return None

        return {
            "name": "ai_generated_episode_page",
            "selector": selector,
            "attr": attr,
            "score": 0.6
        }

    # --------------------------------------------------
    # SALVAR REGRA
    # --------------------------------------------------
    def _save_strategy(self, context, strategy):
        file_map = {
            "anime_list": "anime_list.json",
            "anime_page": "anime_page.json",
            "episode_page": "episode_page.json"
        }

        filename = file_map.get(context)
        if not filename:
            raise ValueError("Contexto inválido para salvar regra")

        # evita duplicação
        rules = self.loader.get_strategies(filename)
        for r in rules:
            if r.get("selector") == strategy.get("selector"):
                return

        self.loader.add_strategy(filename, strategy)