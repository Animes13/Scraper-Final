# main.py
import time
from anilist_api import buscar_ids_animes, buscar_detalhes_anime
from utils import transformar_em_objeto, carregar_json_existente, salvar_json
from config import TOTAL_PAGES, PER_PAGE, OUTPUT_JSON, CHECKPOINT_INTERVAL, FILTER_SEASON, FILTER_YEAR, FILTER_TYPE, FILTER_GENRE

# Carregar progresso existente
data = carregar_json_existente(OUTPUT_JSON)
todos_animes = [a for a in data.get("animes", [])]
processed_ids = set(data.get("processed_ids", []))

for page in range(1, TOTAL_PAGES + 1):
    while True:
        try:
            print(f"Buscando IDs da pÃ¡gina {page}...")
            ids = buscar_ids_animes(page, PER_PAGE)
            if not ids:
                print(f"Nenhum anime encontrado na pÃ¡gina {page}, tentando novamente em 5s...")
                time.sleep(5)
                continue  # Tenta novamente a mesma pÃ¡gina

            for id_anime in ids:
                if id_anime in processed_ids:
                    continue
                retry_count = 0
                while retry_count < 5:
                    anime_obj = buscar_detalhes_anime(id_anime)
                    if anime_obj:
                        # Filtro opcional
                        if FILTER_SEASON and anime_obj.season != FILTER_SEASON:
                            break
                        if FILTER_YEAR and anime_obj.seasonYear != FILTER_YEAR:
                            break
                        if FILTER_TYPE and anime_obj.type != FILTER_TYPE:
                            break
                        if FILTER_GENRE and FILTER_GENRE not in anime_obj.genres:
                            break

                        todos_animes.append(anime_obj)
                        processed_ids.add(id_anime)

                        # Checkpoint
                        if len(todos_animes) % CHECKPOINT_INTERVAL == 0:
                            print(f"Salvando checkpoint ({len(todos_animes)} animes)...")
                            salvar_json(todos_animes, list(processed_ids), OUTPUT_JSON)
                        break
                    else:
                        retry_count += 1
                        print(f"Tentativa {retry_count}/5 falhou para anime {id_anime}, aguardando 5s...")
                        time.sleep(5)
                time.sleep(1.5)  # evita sobrecarga na API

            break  # PÃ¡gina processada com sucesso, vai para a prÃ³xima
        except Exception as e:
            print(f"Erro na pÃ¡gina {page}: {e}, tentando novamente em 5s...")
            time.sleep(5)

# Salvar JSON final
print(f"Salvando JSON final com {len(todos_animes)} animes...")
salvar_json(todos_animes, list(processed_ids), OUTPUT_JSON)
print("ConcluÃ­do!")