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
    Não cria dados, apenas padrões.
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

        stage = context.get("stage")

        # Title mapping não precisa de HTML
        if stage != "title_mapping" and not context.get("html"):
            raise RuntimeError("HTML vazio - IA não será chamada")

        # 1️⃣ chama IA
        result = self.gemini.analyze(context)

        # 2️⃣ valida estrutura mínima
        if not self._basic_validation(result):
            raise RuntimeError("Resposta da IA inválida")

        # 2.1️⃣ confiança mínima diferenciada
        if stage == "title_mapping":
            min_conf = 0.30
        else:
            min_conf = MIN_CONFIDENCE

        if result.get("confidence", 0) < min_conf:
            raise RuntimeError("Confiança da IA muito baixa")

        # 2.2️⃣ sanity check de tipo
        if not self._type_matches_stage(result.get("type"), stage):
            raise RuntimeError("Tipo retornado pela IA não corresponde ao stage")

        # 3️⃣ normaliza
        rule = self._normalize_rule(result, stage)
        if not rule:
            raise RuntimeError("Falha ao normalizar regra")

        # 4️⃣ valida regra (não valida title_mapping)
        if stage != "title_mapping":
            if not self.validator.validate(rule, stage):
                raise RuntimeError("Regra inválida segundo Validator")

        # 5️⃣ evita duplicação (não aplica para title_mapping)
        if stage != "title_mapping":
            if self._rule_exists(rule, stage):
                return {"status": "exists"}

        # 6️⃣ salva (não salva title_mapping)
        if stage != "title_mapping":
            self._save_rule(rule, stage)

        return {
            "status": "learned",
            "rule": rule
        }

    # --------------------------------------------------
    # VALIDAÇÃO BÁSICA DO JSON
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
    # VALIDAÇÃO DE TYPE VS STAGE
    # --------------------------------------------------
    def _type_matches_stage(self, response_type: str, stage: str) -> bool:
        if stage == "title_mapping":
            return response_type == "title_mapping"

        if stage in {"anime_list", "anime_page", "episode_page"}:
            return response_type in {"selector_fix", "episode_list"}

        return False

    # --------------------------------------------------
    # NORMALIZA REGRA
    # --------------------------------------------------
    def _normalize_rule(self, data: Dict[str, Any], stage: str) -> Dict[str, Any]:
        rules = data["rules"]

        # ---------- title_mapping ----------
        if stage == "title_mapping":
            mapped_title = rules.get("title") or rules.get("mapped_title")
            if not mapped_title:
                return None

            rule = {
                "match_title": mapped_title,
                "confidence": data.get("confidence", 0.5),
            }

            # URL pode vir enriquecida pelo GeminiClient
            if "url" in rules:
                rule["url"] = rules["url"]

            return rule

        # ---------- regra estrutural ----------
        rule = {
            "name": f"ai_{stage}",
            "score": max(data.get("confidence", MIN_SCORE), MIN_SCORE),
            "source": "puter-ai",
            "stage": stage,
            "match": {},
            "extract": {},
        }

        # ---------- anime_list ----------
        if stage == "anime_list":
            css = rules.get("css")
            if not css:
                return None

            rule["match"]["card"] = css
            rule["extract"] = {
                "title": {"type": "text", "selector": f"{css} h3"},
                "link": {"type": "attr", "selector": "a", "attr": "href"},
            }

        # ---------- anime_page ----------
        elif stage == "anime_page":
            regex = rules.get("regex")
            if not regex:
                return None

            rule["match"]["episodes"] = {
                "type": "regex",
                "pattern": regex,
            }

        # ---------- episode_page ----------
        elif stage == "episode_page":
            css = rules.get("css")
            if not css:
                return None

            rule["extract"] = {
                "player": {
                    "type": "attr",
                    "selector": css,
                    "attr": "data-blogger-url-encrypted",
                }
            }

        else:
            return None

        return rule

    # --------------------------------------------------
    # DUPLICAÇÃO
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