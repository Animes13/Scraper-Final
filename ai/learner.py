# ai/learner.py
from copy import deepcopy
from typing import Dict, Any

from ai.gemini import GeminiClient
from core.validator import Validator
from rules.loader import RuleLoader


MIN_CONFIDENCE = 0.55
MIN_SCORE = 0.6


class RuleLearner:
    """
    Aprende novas regras estruturais quando o scraper quebra.
    No cria dados, apenas padres.
    """

    def __init__(self):
        self.gemini = GeminiClient()
        self.validator = Validator()
        self.loader = RuleLoader()

    # --------------------------------------------------
    # API PRINCIPAL
    # --------------------------------------------------
    def learn(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        context esperado:
        {
            anime,
            url,
            stage,
            error_type,
            html
        }
        """

        if not context.get("html"):
            raise RuntimeError("HTML vazio — IA no será chamada")

        # 1 chama Gemini
        result = self.gemini.analyze(context)

        # 2 valida estrutura mínima
        if not self._basic_validation(result):
            raise RuntimeError("Resposta da IA inválida")

        if result["confidence"] < MIN_CONFIDENCE:
            raise RuntimeError("Confiança da IA muito baixa")

        # 3 normaliza
        rule = self._normalize_rule(result, context["stage"])
        if not rule:
            raise RuntimeError("Falha ao normalizar regra")

        # 4 valida regra
        if not self.validator.validate(rule, context["stage"]):
            raise RuntimeError("Regra inválida segundo Validator")

        # 5 evita duplicaço
        if self._rule_exists(rule, context["stage"]):
            return {"status": "exists"}

        # 6 salva
        self._save_rule(rule, context["stage"])

        return {
            "status": "learned",
            "rule": rule
        }

    # --------------------------------------------------
    # VALIDAÇO BÁSICA DO JSON
    # --------------------------------------------------
    def _basic_validation(self, data: Dict[str, Any]) -> bool:
        return (
            isinstance(data, dict)
            and "type" in data
            and "confidence" in data
            and "rules" in data
            and isinstance(data["rules"], dict)
        )

    # --------------------------------------------------
    # NORMALIZA REGRA
    # --------------------------------------------------
    def _normalize_rule(self, data: Dict[str, Any], stage: str) -> Dict[str, Any]:
        rules = data["rules"]

        rule = {
            "name": f"ai_{stage}",
            "score": max(data["confidence"], MIN_SCORE),
            "source": "gemini",
            "stage": stage,
            "match": {},
            "extract": {}
        }

        # ---------- anime_list ----------
        if stage == "anime_list":
            if not rules.get("css"):
                return None

            rule["match"]["card"] = rules["css"]
            rule["extract"] = {
                "title": {"type": "text", "selector": rules["css"] + " h3"},
                "link": {"type": "attr", "selector": "a", "attr": "href"},
            }

        # ---------- anime_page ----------
        elif stage == "anime_page":
            if not rules.get("regex"):
                return None

            rule["match"]["episodes"] = {
                "type": "regex",
                "pattern": rules["regex"]
            }

        # ---------- episode_page ----------
        elif stage == "episode_page":
            if not rules.get("css"):
                return None

            rule["extract"] = {
                "player": {
                    "type": "attr",
                    "selector": rules["css"],
                    "attr": "data-blogger-url-encrypted"
                }
            }

        else:
            return None

        return rule

    # --------------------------------------------------
    # DUPLICAÇO
    # --------------------------------------------------
    def _rule_exists(self, rule: Dict[str, Any], stage: str) -> bool:
        rules = self.loader.get_rules(stage)
        for r in rules:
            if r.get("match") == rule.get("match"):
                return True
        return False

    # --------------------------------------------------
    # SALVAR
    # --------------------------------------------------
    def _save_rule(self, rule: Dict[str, Any], stage: str):
        self.loader.add_rule(stage, deepcopy(rule))
