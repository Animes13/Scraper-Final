# -*- coding: utf-8 -*-
# core/error_dashboard.py

import json
import time
from pathlib import Path
from hashlib import md5
from typing import List, Dict, Any

# Caminhos
OUTPUT_DIR = Path("output")
DASHBOARD_DIR = OUTPUT_DIR / "ERROS"
DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
DASHBOARD_FILE = DASHBOARD_DIR / "dashboard.json"
ERROS_FILE = DASHBOARD_DIR / "Erros.txt"

# --------------------------------------------------
# UTILITÁRIOS
# --------------------------------------------------
def gerar_id(texto: str) -> str:
    """Cria um hash curto para identificar cada erro unicamente"""
    return md5(texto.encode("utf-8")).hexdigest()[:8]

def carregar_dashboard() -> Dict[str, Any]:
    if DASHBOARD_FILE.exists():
        try:
            return json.loads(DASHBOARD_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def salvar_dashboard(data: Dict[str, Any]):
    data["generated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    DASHBOARD_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

# --------------------------------------------------
# PARSE DE ERROS
# --------------------------------------------------
def parse_erros() -> List[Dict[str, Any]]:
    """Lê o Erros.txt e transforma em lista de dicionários"""
    erros = []
    if not ERROS_FILE.exists():
        return erros

    with open(ERROS_FILE, "r", encoding="utf-8") as f:
        bloco = {}
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            if linha.startswith("="*60):
                if bloco:
                    # Gera ID único
                    bloco["error_id"] = gerar_id(bloco.get("TIPO", "") + bloco.get("URL", "") + bloco.get("ANIME", ""))
                    bloco["attempts"] = 0
                    bloco["fixed"] = False
                    bloco["pending_retry"] = False
                    bloco["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    erros.append(bloco)
                    bloco = {}
            else:
                if ":" in linha:
                    k, v = linha.split(":", 1)
                    bloco[k.strip()] = v.strip()
        # último bloco
        if bloco:
            bloco["error_id"] = gerar_id(bloco.get("TIPO", "") + bloco.get("URL", "") + bloco.get("ANIME", ""))
            bloco["attempts"] = 0
            bloco["fixed"] = False
            bloco["pending_retry"] = False
            bloco["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
            erros.append(bloco)
    return erros

# --------------------------------------------------
# ATUALIZA DASHBOARD
# --------------------------------------------------
def atualizar_dashboard():
    dashboard = carregar_dashboard()
    dashboard.setdefault("errors", [])

    novos_erros = parse_erros()
    existentes_ids = {e["error_id"] for e in dashboard["errors"]}

    # Adiciona só os novos erros
    for e in novos_erros:
        if e["error_id"] not in existentes_ids:
            dashboard["errors"].append(e)

    # Estatísticas rápidas
    dashboard["stats"] = {
        "total_errors": len(dashboard["errors"]),
        "pending_retry": sum(1 for e in dashboard["errors"] if e.get("pending_retry")),
        "fixed": sum(1 for e in dashboard["errors"] if e.get("fixed"))
    }

    salvar_dashboard(dashboard)
    print(f"📊 Dashboard atualizado — {len(dashboard['errors'])} erros no total")

# --------------------------------------------------
# ENTRYPOINT
# --------------------------------------------------
if __name__ == "__main__":
    atualizar_dashboard()