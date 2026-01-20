# -*- coding: utf-8 -*-

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
MAX_RETRY_IA = 3
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
            print("✔ Nenhum erro registrado")
            return

        dashboard = load_dashboard()
        self.analyzer.load_errors()

        if not self.analyzer.errors:
            print("✔ Nenhum erro pendente elegível")
            return

        print(f"⚡ AutoFix iniciado — {len(self.analyzer.errors)} erros analisáveis")

        for error in self.analyzer.errors:
            self._process_error(error, dashboard)

        save_dashboard(dashboard)
        print("✔ AutoFix finalizado")

    # --------------------------------------------------
    # PROCESSAMENTO DE ERRO
    # --------------------------------------------------
    def _process_error(self, error: Dict[str, Any], dashboard: Dict[str, Any]):
        action = handle_error(error)

        print(f"\n🔎 {error['type']} → ação: {action.value}")

        if action == Action.IGNORE:
            return

        # Bloqueio de loop
        if error.get("attempts", 0) >= MAX_RETRY_IA:
            print("⛔ Tentativas máximas atingidas — ignorando erro")
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
        for e in dashboard.get("errors", []):
            if e.get("error_id") == error.get("error_id") and not e.get("fixed"):
                e["attempts"] = e.get("attempts", 0) + 1
                e["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
                error["attempts"] = e["attempts"]
                break

    # --------------------------------------------------
    # RETRY SIMPLES
    # --------------------------------------------------
    def _retry_simple(self, error: Dict[str, Any], dashboard: Dict[str, Any]):
        if error.get("attempts", 0) >= MAX_RETRY_SIMPLE:
            print("⏭ Retry simples excedido — promovendo para IA")
            return

        print(f"⏱ Retry simples → {error.get('url')}")
        self._inc_attempts(error, dashboard)
        time.sleep(RETRY_DELAY)

    # --------------------------------------------------
    # IA + RETRY
    # --------------------------------------------------
    def _call_ia_and_retry(self, error: Dict[str, Any], dashboard: Dict[str, Any]):
        try:
            context = self.analyzer.build_context(error)

            # --------------------------------------------------
            # TITLE MAPPING (ANILIST)
            # --------------------------------------------------
            if error["type"] == "ANIME_NAO_ENCONTRADO":
                print(f"🔍 IA → title_mapping para '{error.get('anime')}'")

                result = self.learner.learn({
                    **context,
                    "stage": "title_mapping",
                    "html": ""
                })

                mapped_title = result.get("rule", {}).get("match_title")
                if not mapped_title:
                    raise RuntimeError("IA não retornou título válido")

                print(f"💡 Título mapeado: {mapped_title}")

                for e in dashboard["errors"]:
                    if e.get("error_id") == error.get("error_id"):
                        e["mapped_title"] = mapped_title
                        e["pending_retry"] = True
                        break

                self._inc_attempts(error, dashboard)
                return

            # --------------------------------------------------
            # APRENDIZADO ESTRUTURAL
            # --------------------------------------------------
            print("🤖 IA → aprendizado estrutural")
            result = self.learner.learn(context)

            if result.get("status") not in ("learned", "exists"):
                raise RuntimeError("IA não conseguiu aprender regra")

            print("✅ Regra aprendida — aguardando retry")

            for e in dashboard["errors"]:
                if e.get("error_id") == error.get("error_id"):
                    e["pending_retry"] = True
                    break

            self._inc_attempts(error, dashboard)

        except Exception as exc:
            print(f"❌ IA falhou: {exc}")
            self._inc_attempts(error, dashboard)

# --------------------------------------------------
# ENTRYPOINT
# --------------------------------------------------
if __name__ == "__main__":
    AutoFixEngine().run()