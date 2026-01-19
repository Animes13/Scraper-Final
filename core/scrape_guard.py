# core/scrape_guard.py
from typing import Callable, Any
from core.error_logger import log_error
from core.error_handler import handle_error, Action


def guarded_scrape(
    *,
    anime: str,
    url: str,
    stage: str,
    scrape_fn: Callable[[], Any],
    html: str = None
):
    """
    Executa scraping com proteção total.
    """
    try:
        return scrape_fn()

    except Exception as e:
        error = log_error(
            anime=anime,
            url=url,
            stage=stage,
            error_type=_classify_error(e),
            message=str(e)
        )

        # HTML real só é salvo se for erro estrutural
        if html and error["type"] in (
            "EPISODIOS_NAO_ENCONTRADOS",
            "SELECTOR_FAILED",
            "STRUCTURE_CHANGED"
        ):
            error["html"] = html

        action = handle_error(error)

        if action == Action.RETRY:
            return None  # retry será feito fora

        if action == Action.CALL_IA:
            return None  # IA roda via auto_fix

        return None


def _classify_error(e: Exception) -> str:
    msg = str(e).lower()

    if "404" in msg:
        return "HTTP_404"
    if "503" in msg or "504" in msg:
        return "HTTP_503"
    if "timeout" in msg:
        return "TIMEOUT"
    if "episod" in msg:
        return "EPISODIOS_NAO_ENCONTRADOS"

    return "UNKNOWN"