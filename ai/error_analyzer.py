# ai/error_analyzer.py
import json
from pathlib import Path
from typing import List, Dict, Any


DASHBOARD = Path("output/ERROS/dashboard.json")

IA_ELIGIBLE = {
    "EPISODIOS_NAO_ENCONTRADOS",
    "SELECTOR_FAILED",
    "STRUCTURE_CHANGED",
    "ANIME_NAO_ENCONTRADO",
}


class ErrorAnalyzerAI:
    def __init__(self):
        self.errors: List[Dict[str, Any]] = []

    # --------------------------------------------------
    # LOAD
    # --------------------------------------------------
    def load_errors(self):
        if not DASHBOARD.exists():
            return

        data = json.loads(DASHBOARD.read_text(encoding="utf-8"))
        self.errors = [
            e for e in data.get("errors", [])
            if not e.get("fixed") and e.get("type") in IA_ELIGIBLE
        ]

    # --------------------------------------------------
    # GROUP
    # --------------------------------------------------
    def group_by_type(self) -> Dict[str, List[Dict]]:
        grouped = {}
        for e in self.errors:
            grouped.setdefault(e["type"], []).append(e)
        return grouped

    # --------------------------------------------------
    # CONTEXT BUILDER
    # --------------------------------------------------
    def build_context(self, error: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepara contexto limpo e mÃ­nimo para IA.
        """
        return {
            "anime": error.get("anime"),
            "url": error.get("url"),
            "stage": error.get("stage"),
            "html": error.get("html"),
            "attempts": error.get("attempts", 1),
            "error_type": error.get("type"),
        }

    # --------------------------------------------------
    # PAYLOAD PARA IA
    # --------------------------------------------------
    def get_ai_payloads(self) -> List[Dict[str, Any]]:
        payloads = []
        for e in self.errors:
            if not e.get("html"):
                continue  # IA nunca roda sem HTML real
            payloads.append(self.build_context(e))
        return payloads