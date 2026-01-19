# -*- coding: utf-8 -*-
# auto_fix.py

import json
import time
from pathlib import Path
from typing import Dict, Any

from core.error_handler import handle_error, Action
from ai.error_analyzer import ErrorAnalyzerAI
from ai.learner import RuleLearner

# --------------------------------------------------
# PATHS
# --------------------------------------------------
OUTPUT_DIR = Path("output")
ANIMES_JSON = OUTPUT_DIR / "animes.json"
DASHBOARD = OUTPUT_DIR / "ERROS" / "dashboard.json"

MAX_RETRY_SIMPLE = 2
RETRY_DELAY = 8  # segundos


# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def load_dashboard() -> Dict[str, Any]:
    return json.loads(DASHBOARD.read_text(encoding="utf-8"))


def save_dashboard(data: Dict[str, Any]):
    DASHBOARD.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def load_animes() -> list:
    if not ANIMES_JSON.exists():
        return []
    return json.loads(ANIMES_JSON.read_text(encoding="utf-8"))


def save_animes(data: list):
    ANIMES_JSON.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def find_anime(animes: list, *, nome=None, url=None):
    for a in animes:
        if url and a.get("url") == url:
            return a
        if nome and a.get("nome") == nome:
            return a
    return None


# --------------------------------------------------
# ENGINE
# --------------------------------------------------
class AutoFixEngine:
    def __init__(self):
        self.analyzer = ErrorAnalyzerAI()
        self.learner = RuleLearner()

    # --------------------------------------------------
    # ENTRY
    # --------------------------------------------------
    def run(self):
        if not DASHBOARD.exists():
            print("â Nenhum erro registrado")
            return

        dashboard = load_dashboard()
        self.analyzer.load_errors()

        if not self.analyzer.errors:
            print("â Nenhum erro pendente elegÃ­vel")
            return

        print(f"ð§  AutoFix iniciado â {len(self.analyzer.errors)} erros analisÃ¡veis")

        for error in self.analyzer.errors:
            self._process_error(error, dashboard)

        save_dashboard(dashboard)
        print("â AutoFix finalizado")

    # --------------------------------------------------
    # PROCESSAMENTO DE ERRO
    # --------------------------------------------------
    def _process_error(self, error: Dict[str, Any], dashboard: Dict[str, Any]):
        action = handle_error(error)

        print(f"\nð§ {error['type']} â aÃ§Ã£o: {action.value}")

        if action == Action.IGNORE:
            return

        if action == Action.RETRY:
            self._retry_simple(error, dashboard)
            return

        if action == Action.CALL_IA:
            self._call_ia_and_retry(error, dashboard)

    # --------------------------------------------------
    # ATUALIZA attempts NO DASHBOARD
    # --------------------------------------------------
    def _inc_attempts(self, error: Dict[str, Any], dashboard: Dict[str, Any]):
        for e in dashboard["errors"]:
            if e["url"] == error["url"] and not e["fixed"]:
                e["attempts"] = e.get("attempts", 1) + 1
                error["attempts"] = e["attempts"]
                break

    # --------------------------------------------------
    # RETRY SIMPLES
    # --------------------------------------------------
    def _retry_simple(self, error: Dict[str, Any], dashboard: Dict[str, Any]):
        print(f"ð Retry simples â {error['url']}")
        self._inc_attempts(error, dashboard)
        time.sleep(RETRY_DELAY)

    # --------------------------------------------------
    # IA + RETRY
    # --------------------------------------------------
    def _call_ia_and_retry(self, error: Dict[str, Any], dashboard: Dict[str, Any]):
        try:
            print("ð§  Chamando IA para aprendizadoâ¦")

            context = self.analyzer.build_context(error)
            result = self.learner.learn(context)

            if result.get("status") not in ("learned", "exists"):
                return

            print("ð§  Regra aprendida â aguardando retry do scraper")
            self._inc_attempts(error, dashboard)

            # Marca para prÃ³ximo ciclo do scraper
            for e in dashboard["errors"]:
                if e["url"] == error["url"] and not e["fixed"]:
                    e["pending_retry"] = True
                    break

        except Exception as e:
            print(f"â IA falhou: {e}")
            self._inc_attempts(error, dashboard)


# --------------------------------------------------
# ENTRYPOINT
# --------------------------------------------------
if __name__ == "__main__":
    AutoFixEngine().run()