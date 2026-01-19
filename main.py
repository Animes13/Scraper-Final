# -*- coding: utf-8 -*-
# scraper/main.py
import json
import time
from pathlib import Path
from difflib import get_close_matches
from deep_translator import GoogleTranslator

from sites.goyabu.anime_list import GoyabuAnimeListScraper
from sites.goyabu.anime_page import GoyabuAnimePageScraper
from sites.goyabu.episode_page import GoyabuEpisodePageScraper
from sites.goyabu.AniList.anilist_api import buscar_detalhes_anime_por_titulo, buscar_titulos_disponiveis

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
        result = {}
        for key, value in obj.__dict__.items():
            result[key] = to_dict(value)
        return result
    else:
        return str(obj)

# --------------------------------------------------
# FUNÇÃO DE BUSCA FUZZY NO AniList
# --------------------------------------------------
def buscar_anime_fuzzy(titulo):
    """
    Tenta encontrar um anime no AniList usando busca fuzzy.
    """
    # Lista de títulos disponíveis (romaji/english/native)
    possiveis = buscar_titulos_disponiveis(titulo[:50])  # Busca inicial de possíveis matches
    if not possiveis:
        return None

    # Seleciona o mais parecido
    match = get_close_matches(titulo, possiveis, n=1, cutoff=0.6)  # 60% de similaridade mínima
    if match:
        return buscar_detalhes_anime_por_titulo(match[0])
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

            # Busca AniList usando fuzzy search
            ani_data = buscar_anime_fuzzy(anime["titulo"])
            if not ani_data:
                # Segunda tentativa com primeiros 20 caracteres
                titulo_parcial = anime["titulo"][:20]
                print(f"🔄 AniList não encontrou '{anime['titulo']}', tentando parcial fuzzy: '{titulo_parcial}'")
                ani_data = buscar_anime_fuzzy(titulo_parcial)

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