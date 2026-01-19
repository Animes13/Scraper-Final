# -*- coding: utf-8 -*-
# core/error_logger.py
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# --------------------------------------------------
# PATHS
# --------------------------------------------------
BASE_DIR = Path("output/ERROS")
BASE_DIR.mkdir(parents=True, exist_ok=True)

HUMAN_LOG = BASE_DIR / "Erros.txt"
DASHBOARD = BASE_DIR / "dashboard.json"

# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def _now() -> str:
    """Retorna timestamp UTC ISO"""
    return datetime.utcnow().isoformat()


def _load_dashboard() -> Dict[str, Any]:
    """Carrega dashboard JSON com fallback seguro"""
    if DASHBOARD.exists():
        try:
            data = json.loads(DASHBOARD.read_text(encoding="utf-8"))
            if "errors" not in data or "stats" not in data:
                # Corrige dashboard inválido
                data = {
                    "errors": [],
                    "stats": {
                        "total": 0,
                        "fixed": 0,
                        "pending": 0,
                        "by_type": {}
                    }
                }
            return data
        except Exception:
            pass

    # Cria dashboard inicial se não existir ou estiver corrompido
    return {
        "errors": [],
        "stats": {
            "total": 0,
            "fixed": 0,
            "pending": 0,
            "by_type": {}
        }
    }


def _save_dashboard(data: Dict[str, Any]):
    """Salva dashboard JSON"""
    DASHBOARD.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

# --------------------------------------------------
# API PRINCIPAL
# --------------------------------------------------
def log_error(
    *,
    anime: str,
    url: str,
    stage: str,
    error_type: str,
    message: str
) -> Dict[str, Any]:
    """
    Log humano + dashboard de erros (JSON self-healing)
    Retorna dict do erro
    """

    error = {
        "timestamp": _now(),
        "anime": anime,
        "url": url,
        "stage": stage,
        "type": error_type,
        "message": message,
        "fixed": False,
        "attempts": 1
    }

    # Log humano
    with HUMAN_LOG.open("a", encoding="utf-8") as f:
        f.write(
            f"[{error['timestamp']}] "
            f"{error_type} | {anime} | {stage}\n"
            f"{message}\n\n"
        )

    # Log JSON (dashboard)
    dashboard = _load_dashboard()
    dashboard.setdefault("errors", [])
    dashboard.setdefault("stats", {
        "total": 0,
        "fixed": 0,
        "pending": 0,
        "by_type": {}
    })

    dashboard["errors"].append(error)

    # Estatísticas
    stats = dashboard["stats"]
    stats["total"] += 1
    stats["pending"] += 1
    stats["by_type"].setdefault(error_type, 0)
    stats["by_type"][error_type] += 1

    _save_dashboard(dashboard)

    return error