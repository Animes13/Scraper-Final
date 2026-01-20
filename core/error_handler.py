from enum import Enum
from typing import Dict, Any

MAX_RETRIES = 2

class Action(Enum):
    RETRY = "retry"
    CALL_IA = "call_ia"
    IGNORE = "ignore"

# Mapa determinístico de decisão
ERROR_POLICY = {
    "HTTP_404": Action.RETRY,
    "HTTP_503": Action.RETRY,
    "HTTP_504": Action.RETRY,
    "TIMEOUT": Action.RETRY,

    "EPISODIOS_NAO_ENCONTRADOS": Action.CALL_IA,
    "SELECTOR_FAILED": Action.CALL_IA,
    "STRUCTURE_CHANGED": Action.CALL_IA,
    "ANIME_NAO_ENCONTRADO": Action.CALL_IA,  # agora garantido

    "ANILIST_FALHA": Action.RETRY,

    "IA_FALHA": Action.IGNORE,
    "UNKNOWN": Action.IGNORE,
}

def handle_error(error: Dict[str, Any]) -> Action:
    """
    Decide o que fazer com um erro já logado.
    Retorna uma Action.
    """

    # Normaliza para maiúsculas para evitar problemas de capitalização
    error_type = error.get("type", "UNKNOWN").upper()
    attempts = error.get("attempts", 0)  # tenta iniciar de 0

    action = ERROR_POLICY.get(error_type, Action.IGNORE)

    # Proteção contra loop infinito só para RETRY
    if action == Action.RETRY and attempts > MAX_RETRIES:
        return Action.IGNORE

    # IA sempre roda para ANIME_NAO_ENCONTRADO na primeira tentativa
    if action == Action.CALL_IA and attempts > 1 and error_type != "ANIME_NAO_ENCONTRADO":
        return Action.IGNORE

    return action