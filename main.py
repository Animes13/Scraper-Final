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

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "animes.json"

# --------------------------------------------------
# FUNÇÃO AUXILIAR PARA JSON
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
# NORMALIZAÇÃO DE TÍTULOS
# --------------------------------------------------
def normalizar_titulo(titulo):
    """Remove acentos, aspas curvas, parênteses e espaços duplicados"""
    import unicodedata
    t = titulo.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    t = re.sub(r'\(.*?\)', '', t)  # Remove conteúdo entre parênteses
    t = t.split(":")[0]  # Pega só a parte antes de ':' para subtítulos
    t = ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')
    t = re.sub(r'\s+', ' ', t).strip()
    return t

# --------------------------------------------------
# FUNÇÃO DE BUSCA FUZZY COM FALLBACK POR URL/ID
# --------------------------------------------------
def buscar_anime_por_url_ou_fuzzy(titulo, url=None):
    """
    Busca primeiro pelo título usando fuzzy.
    Se falhar, tenta extrair o ID do AniList da URL (se fornecida) e busca por ID.
    """
    titulo_norm = normalizar_titulo(titulo)
    possiveis = buscar_titulos_disponiveis(titulo_norm[:50])
    if possiveis:
        match = get_close_matches(titulo_norm, possiveis, n=1, cutoff=0.6)
        if match:
            ani_data = buscar_detalhes_anime_por_titulo(match[0])
            if ani_data:
                return ani_data

    # Fallback parcial (primeiros 20 caracteres)
    if len(titulo_norm) > 20:
        possiveis = buscar_titulos_disponiveis(titulo_norm[:20])
        if possiveis:
            match = get_close_matches(titulo_norm[:20], possiveis, n=1, cutoff=0.5)
            if match:
                ani_data = buscar_detalhes_anime_por_titulo(match[0])
                if ani_data:
                    return ani_data

    # Fallback por ID do AniList extraído da URL
    if url:
        m = re.search(r'/anime/(\d+)', url)
        if m:
            id_anime = int(m.group(1))
            print(f"🔄 Título '{titulo}' não encontrado, tentando pelo AniList ID {id_anime}")
            ani_data = buscar_detalhes_anime(id_anime)
            if ani_data:
                return ani_data

    print(f"❌ Nenhum resultado para '{titulo}'")
    return None

# --------------------------------------------------
# FUNÇÃO PRINCIPAL
# --------------------------------------------------
def main(max_pages=1, delay=1.5):
    anime_list_scraper = GoyabuAnimeListScraper()
    anime_page_scraper = GoyabuAnimePageScraper()
    episode_page_scraper = GoyabuEpisodePageScraper()

    resultado_final = []

    print("🚀 Iniciando scraper híbrido Goyabu + AniList + Tradução + Fuzzy Search")

    for pagina in range(1, max_pages + 1):
        print(f"\n📄 Página {pagina}")
        try:
            animes = anime_list_scraper.listar(pagina)
        except Exception as e:
            print("❌ Erro ao listar animes:", e)
            continue

        for anime in animes:
            print(f"\n🎬 Anime: {anime['titulo']}")

            ani_data = buscar_anime_por_url_ou_fuzzy(anime["titulo"], anime.get("anilist_url"))

            # Preenche objeto base do Goyabu
            anime_obj = {
                "nome": anime["titulo"],
                "tipo": anime.get("tipo"),
                "nota": anime.get("nota"),
                "url": anime["link"],
                "episodios": []
            }

            # Adiciona dados AniList se disponíveis
            if ani_data:
                try:
                    descricao_original = getattr(ani_data, "description", "")
                    descricao_pt = ""
                    if descricao_original:
                        try:
                            descricao_pt = GoogleTranslator(source='auto', target='pt').translate(descricao_original)
                        except Exception as e:
                            print(f"⚠️ Erro na tradução de '{anime['titulo']}': {e}")

                    anime_obj.update({
                        "títulos": {
                            "romaji": getattr(getattr(ani_data, "title", None), "romaji", ""),
                            "english": getattr(getattr(ani_data, "title", None), "english", ""),
                            "native": getattr(getattr(ani_data, "title", None), "native", "")
                        },
                        "descricoes": descricao_original,
                        "descricoes_pt": descricao_pt,
                        "generos": getattr(ani_data, "genres", []),
                        "episodes_total": getattr(ani_data, "episodes", None),
                        "duration": getattr(ani_data, "duration", None),
                        "status": getattr(ani_data, "status", None),
                        "averageScore": getattr(ani_data, "averageScore", None),
                        "popularity": getattr(ani_data, "popularity", None),
                        "favourites": getattr(ani_data, "favourites", None),
                        "studios": getattr(ani_data, "studios", []),
                        "staff": to_dict(getattr(ani_data, "staff", [])),
                        "characters": to_dict(getattr(ani_data, "characters", [])),
                        "relations": to_dict(getattr(ani_data, "relations", [])),
                        "trailer": to_dict(getattr(ani_data, "trailer", None)),
                        "externalLinks": getattr(ani_data, "externalLinks", []),
                        "thumbnail": getattr(ani_data, "coverImage", None),
                        "fanart": getattr(ani_data, "bannerImage", None)
                    })
                except Exception as e:
                    print(f"⚠️ Erro ao adicionar dados AniList para '{anime['titulo']}': {e}")

            # Coleta episódios do Goyabu
            try:
                episodios = anime_page_scraper.listar_episodios(anime["link"])
            except Exception as e:
                print("❌ Erro ao abrir anime:", e)
                continue

            for ep in episodios:
                print(f"   ▸ EP {ep['numero']}")
                ep_url = ep.get("link")
                if not ep_url:
                    print("   ⚠️ Episódio sem link, pulando")
                    continue
                try:
                    streams = episode_page_scraper.obter_streams(ep_url)
                except Exception as e:
                    print("   ❌ Erro ao resolver episódio:", e)
                    continue

                anime_obj["episodios"].append({
                    "episodio": ep["numero"],
                    "url": ep_url,
                    "streams": streams
                })
                time.sleep(delay)

            resultado_final.append(anime_obj)
            salvar_parcial(resultado_final)
            time.sleep(delay)

    salvar_final(resultado_final)
    print("\n✅ Scraping finalizado com sucesso!")

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
    main(max_pages=1, delay=1.2)