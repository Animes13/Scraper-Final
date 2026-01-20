import json
from pathlib import Path
from typing import List, Dict, Any

DASHBOARD = Path("output/ERROS/dashboard.json")

# Tipos de erro que REALMENTE valem IA
IA_ELIGIBLE = {
    "EPISODIOS_NAO_ENCONTRADOS",
    "SELECTOR_FAILED",
    "STRUCTURE_CHANGED",
    "ANIME_NAO_ENCONTRADO",
}

# Limites de segurança
MAX_ATTEMPTS_PER_ERROR = 3
MAX_HTML_SIZE = 20000  # evita mandar HTML gigante


class ErrorAnalyzerAI:
    def __init__(self):
        self.errors: List[Dict[str, Any]] = []

    # --------------------------------------------------
    # LOAD
    # --------------------------------------------------
    def load_errors(self):
        """
        Carrega erros não corrigidos e elegíveis para IA.
        """
        if not DASHBOARD.exists():
            self.errors = []
            return

        data = json.loads(DASHBOARD.read_text(encoding="utf-8"))

        self.errors = [
            e for e in data.get("errors", [])
            if self._is_ai_candidate(e)
        ]

    # --------------------------------------------------
    # FILTRO DE ELEGIBILIDADE
    # --------------------------------------------------
    def _is_ai_candidate(self, error: Dict[str, Any]) -> bool:
        if error.get("fixed"):
            return False

        if error.get("type") not in IA_ELIGIBLE:
            return False

        if error.get("attempts", 1) > MAX_ATTEMPTS_PER_ERROR:
            return False

        if not error.get("html") and error.get("stage") != "title_mapping":
            return False

        return True

    # --------------------------------------------------
    # GROUP
    # --------------------------------------------------
    def group_by_type(self) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for e in self.errors:
            grouped.setdefault(e["type"], []).append(e)
        return grouped

    # --------------------------------------------------
    # CONTEXT BUILDER
    # --------------------------------------------------
    def build_context(self, error: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepara contexto mínimo, limpo e seguro para IA.
        """
        html = error.get("html")

        if html and len(html) > MAX_HTML_SIZE:
            html = html[:MAX_HTML_SIZE]

        return {
            "anime": error.get("anime"),
            "url": error.get("url"),
            "stage": error.get("stage"),
            "error_type": error.get("type"),
            "attempts": error.get("attempts", 1),
            "html": html,
        }

    # --------------------------------------------------
    # PAYLOADS PARA IA
    # --------------------------------------------------
    def get_ai_payloads(self) -> List[Dict[str, Any]]:
        """
        Retorna apenas contextos prontos para IA.
        """
        payloads: List[Dict[str, Any]] = []

        for e in self.errors:
            ctx = self.build_context(e)

            # IA nunca roda sem HTML real (exceto title_mapping)
            if ctx["stage"] != "title_mapping" and not ctx.get("html"):
                continue

            payloads.append(ctx)

        return payloads