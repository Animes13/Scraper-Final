# -*- coding: utf-8 -*-
# scraper/main.py
import json
import time
import re
from pathlib import Path
from difflib import get_close_matches
from deep_translator import GoogleTranslator

from sites.goyabu.anime_list import GoyabuAnimeListScraper
from sites.goyabu.anime_page import GoyabuAnimePageScraper
from sites.goyabu.episode_page import GoyabuEpisodePageScraper
from sites.goyabu.AniList.anilist_api import (
    buscar_detalhes_anime_por_titulo,
    buscar_titulos_disponiveis,
    buscar_detalhes_anime
)

# ð¹ Logger self-healing
from core.error_logger import log_error

# --------------------------------------------------
# OUTPUT
# --------------------------------------------------
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "animes.json"

# --------------------------------------------------
# ERROS (LEGADO)
# --------------------------------------------------
ERROS_DIR = OUTPUT_DIR / "ERROS"
ERROS_DIR.mkdir(parents=True, exist_ok=True)
ERROS_FILE = ERROS_DIR / "Erros.txt"

# --------------------------------------------------
# LOG DE ERROS (LEGADO â NÃO REMOVIDO)
# --------------------------------------------------
def registrar_erro(tipo, anime=None, url=None, erro=None, extra=None):
    with open(ERROS_FILE, "a", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write(f"TIPO: {tipo}\n")
        if anime:
            f.write(f"ANIME: {anime}\n")
        if url:
            f.write(f"URL: {url}\n")
        if erro:
            f.write(f"ERRO: {erro}\n")
        if extra:
            f.write(f"INFO EXTRA: {extra}\n")
        f.write(f"TIMESTAMP: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

# --------------------------------------------------
# FUNÃÃO AUXILIAR PARA JSON
# --------------------------------------------------
def to_dict(obj):
    if obj is None:
        return None
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, list):
        return [to_dict(item) for item in obj]
    elif hasattr(obj, "__dict__"):
        return {k: to_dict(v) for k, v in obj.__dict__.items()}
    else:
        return str(obj)

# --------------------------------------------------
# NORMALIZAÃÃO DE TÃTULOS
# --------------------------------------------------
def normalizar_titulo(titulo):
    import unicodedata
    t = titulo.replace('â', '"').replace('â', '"').replace('â', "'").replace('â', "'")
    t = re.sub(r'\(.*?\)', '', t)
    t = t.split(":")[0]
    t = ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')
    t = re.sub(r'\s+', ' ', t).strip()
    return t

# --------------------------------------------------
# CONTROLE DE QUALIDADE
# --------------------------------------------------
def anime_esta_completo(anime: dict) -> bool:
    return bool(anime.get("episodios"))

def carregar_existentes():
    if OUTPUT_FILE.exists():
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

# --------------------------------------------------
# BUSCA ANIList (FUZZY + FALLBACK)
# --------------------------------------------------
def buscar_anime_por_url_ou_fuzzy(titulo, url=None):
    titulo_norm = normalizar_titulo(titulo)

    try:
        possiveis = buscar_titulos_disponiveis(titulo_norm[:50])
        if possiveis:
            match = get_close_matches(titulo_norm, possiveis, n=1, cutoff=0.6)
            if match:
                ani_data = buscar_detalhes_anime_por_titulo(match[0])
                if ani_data:
                    return ani_data
    except Exception as e:
        registrar_erro("ANILIST_FALHA", titulo, url, str(e))
        log_error(anime=titulo, url=url, stage="anilist",
                  error_type="ANILIST_FALHA", message=str(e))

    registrar_erro("ANIME_NAO_ENCONTRADO", titulo, url)
    log_error(anime=titulo, url=url, stage="anilist",
              error_type="ANIME_NAO_ENCONTRADO",
              message="Anime nÃ£o encontrado no AniList")
    return None

# --------------------------------------------------
# FUNÃÃO PRINCIPAL
# --------------------------------------------------
def main(max_pages=None, delay=1.5):
    anime_list_scraper = GoyabuAnimeListScraper()
    anime_page_scraper = GoyabuAnimePageScraper()
    episode_page_scraper = GoyabuEpisodePageScraper()

    existentes = carregar_existentes()
    existentes_por_url = {a["url"]: a for a in existentes if "url" in a}

    resultado_final = []
    fila_retry = []
    pagina = 1

    print("🚀 Iniciando scraper hibrido Goyabu + AniList")

    while True:
        if max_pages and pagina > max_pages:
            break

        animes = anime_list_scraper.listar(pagina)
        if not animes:
            break

        for anime in animes:
            anime_obj = {
                "nome": anime["titulo"],
                "url": anime["link"],
                "episodios": []
            }

            try:
                episodios = anime_page_scraper.listar_episodios(anime["link"])
                if not episodios:
                    raise Exception("Sem episÃ³dios")

                for ep in episodios:
                    streams = episode_page_scraper.obter_streams(ep["link"])
                    anime_obj["episodios"].append({
                        "episodio": ep["numero"],
                        "url": ep["link"],
                        "streams": streams
                    })

            except Exception as e:
                fila_retry.append(anime)
                registrar_erro("RETRY_AGENDADO", anime["titulo"], anime["link"], str(e))
                log_error(anime=anime["titulo"], url=anime["link"],
                          stage="retry_queue",
                          error_type="RETRY_AGENDADO",
                          message="Agendado para retry")

            antigo = existentes_por_url.get(anime["link"])
            if antigo and anime_esta_completo(antigo) and not anime_esta_completo(anime_obj):
                resultado_final.append(antigo)
            else:
                resultado_final.append(anime_obj)

        pagina += 1

    # --------------------------------------------------
    # ð RETRY INTELIGENTE (ERRO 5)
    # --------------------------------------------------
    if fila_retry:
        print(f"\nð Retry inteligente: {len(fila_retry)} animes")
        for anime in fila_retry:
            try:
                episodios = anime_page_scraper.listar_episodios(anime["link"])
                if not episodios:
                    continue

                anime_retry = {
                    "nome": anime["titulo"],
                    "url": anime["link"],
                    "episodios": []
                }

                for ep in episodios:
                    streams = episode_page_scraper.obter_streams(ep["link"])
                    anime_retry["episodios"].append({
                        "episodio": ep["numero"],
                        "url": ep["link"],
                        "streams": streams
                    })

                resultado_final = [
                    a for a in resultado_final if a["url"] != anime["link"]
                ]
                resultado_final.append(anime_retry)

                log_error(anime=anime["titulo"], url=anime["link"],
                          stage="retry",
                          error_type="RETRY_SUCESSO",
                          message="Retry bem-sucedido")

            except Exception as e:
                registrar_erro("RETRY_FALHOU", anime["titulo"], anime["link"], str(e))

    salvar_final(resultado_final)
    print("\nâ Scraping finalizado com retry inteligente")

# --------------------------------------------------
# SALVAMENTO
# --------------------------------------------------
def salvar_parcial(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def salvar_final(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# --------------------------------------------------
# ENTRYPOINT
# --------------------------------------------------
if __name__ == "__main__":
    main()