# -*- coding: utf-8 -*-
# scraper/main.py
import json
import time
from pathlib import Path

from deep_translator import GoogleTranslator

# Teste rápido de tradução
texto_traduzido = GoogleTranslator(source='auto', target='pt').translate("Hello World")
print(texto_traduzido)  # <-- apenas para conferir tradução

from sites.goyabu.anime_list import GoyabuAnimeListScraper
from sites.goyabu.anime_page import GoyabuAnimePageScraper
from sites.goyabu.episode_page import GoyabuEpisodePageScraper
from sites.goyabu.AniList.anilist_api import buscar_detalhes_anime_por_titulo

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "animes.json"

# --------------------------------------------------
# FUNÇÃO AUXILIAR PARA JSON
# --------------------------------------------------
def to_dict(obj):
    """
    Converte recursivamente um objeto AniList (ou qualquer objeto) em dicionário JSON-friendly.
    """
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
# FUNÇÃO PRINCIPAL
# --------------------------------------------------
def main(max_pages=1, delay=1.5):
    anime_list_scraper = GoyabuAnimeListScraper()
    anime_page_scraper = GoyabuAnimePageScraper()
    episode_page_scraper = GoyabuEpisodePageScraper()

    resultado_final = []

    print("🚀 Iniciando scraper híbrido Goyabu + AniList + Tradução")

    for pagina in range(1, max_pages + 1):
        print(f"\n📄 Página {pagina}")

        try:
            animes = anime_list_scraper.listar(pagina)
        except Exception as e:
            print("❌ Erro ao listar animes:", e)
            continue

        for anime in animes:
            print(f"\n🎬 Anime: {anime['titulo']}")

            # Busca AniList com título completo
            ani_data = buscar_detalhes_anime_por_titulo(anime["titulo"])
            if not ani_data:
                # Segunda tentativa com primeiros 20 caracteres
                titulo_parcial = anime["titulo"][:20]
                print(f"🔄 AniList não encontrou '{anime['titulo']}', tentando parcial: '{titulo_parcial}'")
                ani_data = buscar_detalhes_anime_por_titulo(titulo_parcial)

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
                            # Tradução para português usando deep-translator
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
    main(
        max_pages=1,  # 📌 aumente com cuidado
        delay=1.2      # ⏱️ evita bloqueio
    )