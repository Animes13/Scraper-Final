# -*- coding: utf-8 -*-
# anilist_api.py
import time
import requests
import re
import unicodedata
from sites.goyabu.AniList.models import Anime, Title, Staff, Character, VoiceActor, Relation, Trailer

ANILIST_URL = "https://graphql.anilist.co"


# -------------------------
# POST GRAPHQL COM RETRY
# -------------------------
def _post_graphql(query, variables, retries=10, delay=2, max_delay=64):
    """Wrapper para requisiÃ§Ãµes GraphQL com retry e backoff exponencial"""
    attempt = 0
    while attempt < retries:
        try:
            response = requests.post(ANILIST_URL, json={"query": query, "variables": variables})
            if response.status_code == 429:
                raise requests.exceptions.HTTPError(response=response)
            response.raise_for_status()
            return response.json()["data"]
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code
            wait = min(delay * 2 ** attempt, max_delay)
            if code in [429, 500, 502, 503, 504]:
                print(f"[Retry {attempt+1}/{retries}] Erro {code}, aguardando {wait}s...")
                time.sleep(wait)
                attempt += 1
            else:
                print(f"Erro HTTP {code}: {e}")
                return None
        except requests.exceptions.RequestException as e:
            wait = min(delay * 2 ** attempt, max_delay)
            print(f"[Retry {attempt+1}/{retries}] Erro de rede: {e}, aguardando {wait}s...")
            time.sleep(wait)
            attempt += 1
    print(f"Falha apÃ³s {retries} tentativas para variÃ¡veis {variables}")
    return None
    
# ------------------------------------------------------------------
# FunÃ§Ã£o melhorada para busca de tÃ­tulos disponÃ­veis (fuzzy / parcial)
# ------------------------------------------------------------------

def buscar_titulos_disponiveis(query):
    """
    Retorna uma lista de tÃ­tulos disponÃ­veis que correspondem Ã  query.
    - Inclui busca exata
    - Inclui versÃ£o parcial (primeiros 20 caracteres)
    - Normaliza caracteres especiais
    """
    titulos = []

    # 1ï¸â£ TÃ­tulo original
    titulos.append(query)

    # 2ï¸â£ TÃ­tulo parcial (primeiros 20 caracteres)
    if len(query) > 20:
        titulos.append(query[:20])

    # 3ï¸â£ NormalizaÃ§Ã£o: remove acentos e aspas especiais
    def normalizar(texto):
        # Substitui aspas curvas e outros caracteres estranhos
        texto = texto.replace('â', '"').replace('â', '"').replace('â', "'").replace('â', "'")
        # Remove acentos
        texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        # Remove espaÃ§os duplicados
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto

    titulos_normalizados = [normalizar(t) for t in titulos]

    # Remove duplicatas mantendo ordem
    titulos_final = []
    for t in titulos_normalizados:
        if t not in titulos_final:
            titulos_final.append(t)

    return titulos_final    


# -------------------------
# CONSTRUIR OBJETO ANIME
# -------------------------
def construir_anime_obj(media):
    """Converte JSON do AniList em objeto Anime"""
    title = Title(media["title"]["romaji"], media["title"].get("english"), media["title"].get("native"))

    staff_list = [
        Staff(
            name=edge["node"]["name"]["full"],
            role=edge["role"],
            language=edge["node"].get("language", ""),
            image=edge["node"]["image"]["large"] if edge["node"].get("image") else None
        )
        for edge in media.get("staff", {}).get("edges", [])
    ]

    characters_list = []
    for edge in media.get("characters", {}).get("edges", []):
        voiceactors = [
            VoiceActor(
                name=va["name"]["full"],
                language=va.get("language", ""),
                image=va["image"]["large"] if va.get("image") else None
            )
            for va in edge.get("voiceActors", [])
        ]
        characters_list.append(Character(
            name=edge["node"]["name"]["full"],
            image=edge["node"]["image"]["large"] if edge["node"].get("image") else None,
            voiceActors=voiceactors
        ))

    relations_list = [
        Relation(
            id=edge["node"]["id"],
            title=Title(edge["node"]["title"]["romaji"], edge["node"]["title"].get("english"), edge["node"]["title"].get("native")),
            type=edge["node"]["type"]
        )
        for edge in media.get("relations", {}).get("edges", [])
    ]

    trailer = None
    if media.get("trailer"):
        trailer = Trailer(
            site=media["trailer"]["site"],
            id=media["trailer"]["id"]
        )

    studios = [s["name"] for s in media.get("studios", {}).get("nodes", [])]

    return Anime(
        id=media["id"],
        title=title,
        description=media.get("description"),
        episodes=media.get("episodes"),
        duration=media.get("duration"),
        genres=media.get("genres", []),
        season=media.get("season"),
        seasonYear=media.get("seasonYear"),
        type=media.get("type"),
        status=media.get("status"),
        averageScore=media.get("averageScore"),
        popularity=media.get("popularity"),
        favourites=media.get("favourites"),
        rankings=media.get("rankings", []),
        coverImage=media.get("coverImage", {}).get("large"),
        bannerImage=media.get("bannerImage"),
        trailer=trailer,
        studios=studios,
        staff=staff_list,
        characters=characters_list,
        relations=relations_list,
        externalLinks=media.get("externalLinks", [])
    )


# -------------------------
# BUSCA POR ID
# -------------------------
def buscar_detalhes_anime(id_anime: int):
    query = '''
    query ($id: Int) {
      Media(id: $id, type: ANIME) {
        id
        title { romaji english native }
        description
        episodes
        duration
        genres
        season
        seasonYear
        type
        status
        averageScore
        popularity
        favourites
        rankings { rank type }
        coverImage { large }
        bannerImage
        trailer { site id thumbnail }
        studios { nodes { name } }
        staff { edges { role node { name { full } language image { large } } } }
        characters { edges { node { name { full } image { large } } voiceActors { name { full } language image { large } } } }
        relations { edges { node { id title { romaji english native } type } } }
        externalLinks { site url }
      }
    }'''
    variables = {"id": id_anime}

    data = _post_graphql(query, variables)
    if not data or "Media" not in data:
        return None
    return construir_anime_obj(data["Media"])


# -------------------------
# BUSCA POR TÃTULO COM FALLBACK
# -------------------------
def buscar_detalhes_anime_por_titulo(titulo: str):
    """Busca anime pelo tÃ­tulo, faz segunda tentativa com primeiros 20 caracteres se falhar"""
    query = '''
    query ($search: String) {
      Media(search: $search, type: ANIME) {
        id
        title { romaji english native }
        description
        episodes
        duration
        genres
        season
        seasonYear
        type
        status
        averageScore
        popularity
        favourites
        rankings { rank type }
        coverImage { large }
        bannerImage
        trailer { site id thumbnail }
        studios { nodes { name } }
        staff { edges { role node { name { full } language image { large } } } }
        characters { edges { node { name { full } image { large } } voiceActors { name { full } language image { large } } } }
        relations { edges { node { id title { romaji english native } type } } }
        externalLinks { site url }
      }
    }'''

    # 1Âª tentativa: tÃ­tulo completo
    variables = {"search": titulo}
    data = _post_graphql(query, variables)

    # 2Âª tentativa: primeiros 20 caracteres se falhar
    if not data or "Media" not in data:
        curto = titulo[:20]
        print(f"â ï¸ 1Âª tentativa falhou para '{titulo}', tentando com '{curto}'...")
        variables = {"search": curto}
        data = _post_graphql(query, variables)
        if not data or "Media" not in data:
            print(f"â Nenhum resultado para '{titulo}'")
            return None

    return construir_anime_obj(data["Media"])