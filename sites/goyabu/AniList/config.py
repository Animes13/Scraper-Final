# config.py

TOTAL_PAGES = 50          # Quantas páginas você quer percorrer
PER_PAGE = 25             # Quantos animes por página
OUTPUT_JSON = "animes.json"
CHECKPOINT_INTERVAL = 10  # Salva a cada N animes

# Filtros opcionais
FILTER_SEASON = None      # "WINTER", "SPRING", "SUMMER", "FALL"
FILTER_YEAR = None        # 2026
FILTER_TYPE = None        # "ANIME", "MOVIE", etc.
FILTER_GENRE = None       # "Action", "Comedy", etc.