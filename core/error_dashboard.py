# -*- coding: utf-8 -*-
# core/error_dashboard.py

import json
import time
from pathlib import Path
from hashlib import md5
from typing import List, Dict, Any

# --------------------------------------------------
# CAMINHOS
# --------------------------------------------------
OUTPUT_DIR = Path("output")
DASHBOARD_DIR = OUTPUT_DIR / "ERROS"
DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

DASHBOARD_FILE = DASHBOARD_DIR / "dashboard.json"
ERROS_FILE = DASHBOARD_DIR / "Erros.txt"

# --------------------------------------------------
# UTILITÁRIOS
# --------------------------------------------------
def gerar_id(texto: str) -> str:
    """
    Cria um hash curto para identificar cada erro unicamente.
    Usa conteúdo estável para evitar duplicações.
    """
    return md5(texto.encode("utf-8")).hexdigest()[:10]


def carregar_dashboard() -> Dict[str, Any]:
    if not DASHBOARD_FILE.exists():
        return {"errors": [], "stats": {}}

    try:
        return json.loads(DASHBOARD_FILE.read_text(encoding="utf-8"))
    except Exception:
        # Falha de leitura não deve quebrar o scraper
        return {"errors": [], "stats": {}}


def salvar_dashboard(data: Dict[str, Any]):
    data["generated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    DASHBOARD_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

# --------------------------------------------------
# PARSE DE ERROS
# --------------------------------------------------
def parse_erros() -> List[Dict[str, Any]]:
    """
    Lê o Erros.txt e transforma em lista de dicionários normalizados.
    """
    erros: List[Dict[str, Any]] = []

    if not ERROS_FILE.exists():
        return erros

    with open(ERROS_FILE, "r", encoding="utf-8") as f:
        bloco: Dict[str, Any] = {}

        for linha in f:
            linha = linha.strip()

            if not linha:
                continue

            # Separador de bloco
            if linha.startswith("=" * 60):
                _finalizar_bloco(bloco, erros)
                bloco = {}
                continue

            # Campo
            if ":" in linha:
                k, v = linha.split(":", 1)
                bloco[k.strip()] = v.strip()

        # Último bloco
        _finalizar_bloco(bloco, erros)

    return erros


def _finalizar_bloco(bloco: Dict[str, Any], erros: List[Dict[str, Any]]):
    if not bloco:
        return

    # Normalização mínima esperada pelo pipeline
    tipo = bloco.get("TIPO") or bloco.get("type") or ""
    url = bloco.get("URL") or bloco.get("url") or ""
    anime = bloco.get("ANIME") or bloco.get("anime") or ""
    stage = bloco.get("STAGE") or bloco.get("stage")

    error_id = gerar_id(f"{tipo}|{url}|{anime}|{stage}")

    erro = {
        "error_id": error_id,
        "type": tipo,
        "url": url,
        "anime": anime,
        "stage": stage,
        "html": bloco.get("HTML"),
        "attempts": 0,
        "fixed": False,
        "pending_retry": False,
        "last_update": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    erros.append(erro)

# --------------------------------------------------
# ATUALIZA DASHBOARD
# --------------------------------------------------
def atualizar_dashboard():
    dashboard = carregar_dashboard()
    dashboard.setdefault("errors", [])

    novos_erros = parse_erros()
    existentes = {e["error_id"]: e for e in dashboard["errors"]}

    # Adiciona apenas erros realmente novos
    for erro in novos_erros:
        if erro["error_id"] not in existentes:
            dashboard["errors"].append(erro)

    # Estatísticas rápidas
    dashboard["stats"] = {
        "total_errors": len(dashboard["errors"]),
        "pending_retry": sum(1 for e in dashboard["errors"] if e.get("pending_retry")),
        "fixed": sum(1 for e in dashboard["errors"] if e.get("fixed")),
        "open": sum(1 for e in dashboard["errors"] if not e.get("fixed")),
    }

    salvar_dashboard(dashboard)
    print(f"📊 Dashboard atualizado — {len(dashboard['errors'])} erros no total")

# --------------------------------------------------
# ENTRYPOINT
# --------------------------------------------------
if __name__ == "__main__":
    atualizar_dashboard()