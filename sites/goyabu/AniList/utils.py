# utils.py
import json
from sites.goyabu.AniList.models import Anime

def objeto_para_dict(obj):
    """Converte recursivamente objetos customizados em dicts"""
    if isinstance(obj, list):
        return [objeto_para_dict(item) for item in obj]
    elif hasattr(obj, "__dict__"):
        result = {}
        for key, value in obj.__dict__.items():
            result[key] = objeto_para_dict(value)
        return result
    else:
        return obj

def salvar_json(animes: list, processed_ids: list, arquivo: str):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump({
            "animes": objeto_para_dict(animes),
            "processed_ids": processed_ids
        }, f, ensure_ascii=False, indent=2)

def carregar_json_existente(arquivo: str):
    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"animes": [], "processed_ids": []}

def transformar_em_objeto(anime_obj: Anime):
    return anime_obj  # agora só retorna o objeto, conversão é feita ao salvar