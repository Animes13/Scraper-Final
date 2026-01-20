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

from core.error_logger import log_error

# --------------------------------------------------
# OUTPUT
# --------------------------------------------------
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "animes.json"

# --------------------------------------------------
# ERROS
# --------------------------------------------------
ERROS_DIR = OUTPUT_DIR / "ERROS"
ERROS_DIR.mkdir(parents=True, exist_ok=True)
ERROS_FILE = ERROS_DIR / "Erros.txt"
DASHBOARD_FILE = ERROS_DIR / "dashboard.json"   # 🔧 AJUSTE IA

# --------------------------------------------------
# REGISTRO DE ERROS
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
# 🔧 AJUSTE IA — DASHBOARD HELPERS
# --------------------------------------------------
def carregar_dashboard():
    if not DASHBOARD_FILE.exists():
        return {}
    return json.loads(DASHBOARD_FILE.read_text(encoding="utf-8"))

def marcar_erro_corrigido(url):
    dashboard = carregar_dashboard()
    for e in dashboard.get("errors", []):
        if e.get("url") == url and not e.get("fixed"):
            e["fixed"] = True
            e["pending_retry"] = False
    DASHBOARD_FILE.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False), encoding="utf-8")

def obter_mapped_title(url):
    dashboard = carregar_dashboard()
    for e in dashboard.get("errors", []):
        if e.get("url") == url and e.get("mapped_title"):
            return e.get("mapped_title")
    return None

# --------------------------------------------------
# NORMALIZAÇÃO DE TÍTULOS
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
# FUNÇÃO HELPER PARA SERIALIZAÇÃO
# --------------------------------------------------
def serialize_obj(obj):
    if isinstance(obj, list):
        return [serialize_obj(o) for o in obj]
    elif isinstance(obj, dict):
        return {k: serialize_obj(v) for k, v in obj.items()}
    elif hasattr(obj, "__dict__"):
        return {k: serialize_obj(v) for k, v in vars(obj).items()}
    else:
        return obj

# --------------------------------------------------
# BUSCA ANILIST (COM IA TITLE MAPPING)
# --------------------------------------------------
def buscar_anime_por_url_ou_fuzzy(titulo, url=None):
    # 🔧 AJUSTE IA — usa título mapeado se existir
    mapped = obter_mapped_title(url)
    if mapped:
        titulo = mapped

    titulo_norm = normalizar_titulo(titulo)
    try:
        possiveis = buscar_titulos_disponiveis(titulo_norm[:50])
        if possiveis:
            match = get_close_matches(titulo_norm, possiveis, n=1, cutoff=0.6)
            if match:
                ani_data = buscar_detalhes_anime_por_titulo(match[0])
                if ani_data:
                    ani_data.thumbnail = ani_data.coverImage if hasattr(ani_data, "coverImage") else ""
                    ani_data.fanart = ani_data.bannerImage or ani_data.coverImage or ""
                    return ani_data
    except Exception as e:
        registrar_erro("ANILIST_FALHA", titulo, url, str(e))
        log_error(anime=titulo, url=url, stage="anilist", error_type="ANILIST_FALHA", message=str(e))

    registrar_erro("ANIME_NAO_ENCONTRADO", titulo, url)
    log_error(anime=titulo, url=url, stage="anilist", error_type="ANIME_NAO_ENCONTRADO", message="Anime não encontrado no AniList")
    return None

# --------------------------------------------------
# FUNÇÃO PRINCIPAL
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

    print("🚀 Iniciando scraper híbrido Goyabu + AniList\n")

    while True:
        if max_pages and pagina > max_pages:
            break

        print(f"📄 Coletando Página {pagina}")
        animes = anime_list_scraper.listar(pagina)
        if not animes:
            break

        for anime in animes:
            print(f"\n🎬 {anime['titulo']}")

            ani_data = buscar_anime_por_url_ou_fuzzy(anime["titulo"], anime["link"])
            ani_dict = ani_data.__dict__ if ani_data else {}

            anime_obj = {
                "nome": anime["titulo"],
                "tipo": "Legendado",
                "nota": ani_dict.get("averageScore", ""),
                "url": anime["link"],
                "episodios": [],
                "títulos": ani_dict.get("titles", {}),
                "descricoes": ani_dict.get("description", ""),
                "descricoes_pt": GoogleTranslator(source='en', target='pt').translate(ani_dict.get("description", "")) if ani_data else "",
                "generos": ani_dict.get("genres", []),
                "episodes_total": ani_dict.get("episodes", 0),
                "duration": ani_dict.get("duration", 0),
                "status": ani_dict.get("status", ""),
                "averageScore": ani_dict.get("averageScore", 0),
                "popularity": ani_dict.get("popularity", 0),
                "favourites": ani_dict.get("favourites", 0),
                "studios": ani_dict.get("studios", []),
                "staff": serialize_obj(ani_dict.get("staff", [])),
                "characters": serialize_obj(ani_dict.get("characters", [])),
                "relations": serialize_obj(ani_dict.get("relations", [])),
                "trailer": serialize_obj(ani_dict.get("trailer", {})),
                "externalLinks": serialize_obj(ani_dict.get("externalLinks", [])),
                "thumbnail": ani_dict.get("thumbnail", ""),
                "fanart": ani_dict.get("fanart", "")
            }

            try:
                episodios = anime_page_scraper.listar_episodios(anime["link"])
                for ep in episodios:
                    streams = episode_page_scraper.obter_streams(ep["link"])
                    anime_obj["episodios"].append({
                        "episodio": ep["numero"],
                        "url": ep["link"],
                        "streams": streams
                    })

                # 🔧 AJUSTE IA — marca erro resolvido
                marcar_erro_corrigido(anime["link"])

            except Exception as e:
                fila_retry.append(anime)
                registrar_erro("RETRY_AGENDADO", anime["titulo"], anime["link"], str(e))
                log_error(anime=anime["titulo"], url=anime["link"], stage="retry_queue", error_type="RETRY_AGENDADO", message="Agendado para retry")

            antigo = existentes_por_url.get(anime["link"])
            resultado_final.append(antigo if antigo and anime_esta_completo(antigo) else anime_obj)

        salvar_parcial(resultado_final)
        pagina += 1
        time.sleep(delay)

    salvar_final(resultado_final)
    print("\n🌟 Scraping finalizado")

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
    main(max_pages=1)