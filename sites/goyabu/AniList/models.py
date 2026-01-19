from typing import List, Optional

class Title:
    """
    Armazena tÃ­tulos do anime em mÃºltiplos idiomas.
    """
    def __init__(self, romaji: Optional[str] = None, english: Optional[str] = None, native: Optional[str] = None):
        self.titles = {
            "romaji": romaji,
            "english": english,
            "native": native
        }

    def to_dict(self):
        return self.titles

class Description:
    """
    Armazena descriÃ§Ãµes em mÃºltiplos idiomas. Por enquanto AniList retorna sÃ³ original (geralmente inglÃªs ou japonÃªs).
    """
    def __init__(self, original: Optional[str] = None, english: Optional[str] = None, portuguese: Optional[str] = None):
        self.descriptions = {
            "original": original,
            "english": english,
            "portuguese": portuguese
        }

    def to_dict(self):
        return self.descriptions

class Trailer:
    def __init__(self, site: str, id: str):
        self.site = site
        self.id = id

    def to_dict(self):
        return {"site": self.site, "id": self.id}

class Staff:
    def __init__(self, name: str, role: str, language: str, image: Optional[str] = None):
        self.name = name
        self.role = role
        self.language = language
        self.image = image

    def to_dict(self):
        return {
            "name": self.name,
            "role": self.role,
            "language": self.language,
            "image": self.image
        }

class VoiceActor:
    def __init__(self, name: str, language: str, image: Optional[str] = None):
        self.name = name
        self.language = language
        self.image = image

    def to_dict(self):
        return {
            "name": self.name,
            "language": self.language,
            "image": self.image
        }

class Character:
    def __init__(self, name: str, image: Optional[str], voiceActors: List[VoiceActor]):
        self.name = name
        self.image = image
        self.voiceActors = voiceActors

    def to_dict(self):
        return {
            "name": self.name,
            "image": self.image,
            "voiceActors": [va.to_dict() for va in self.voiceActors]
        }

class Relation:
    def __init__(self, id: int, title: Title, type: str):
        self.id = id
        self.title = title
        self.type = type

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title.to_dict(),
            "type": self.type
        }

class Anime:
    def __init__(self, id: int, title: Title, description: Description, episodes: Optional[int],
                 duration: Optional[int], genres: List[str], season: Optional[str], seasonYear: Optional[int],
                 type: str, status: Optional[str], averageScore: Optional[int], popularity: Optional[int],
                 favourites: Optional[int], rankings: Optional[List[dict]], coverImage: Optional[str],
                 bannerImage: Optional[str], trailer: Optional[Trailer], studios: List[str],
                 staff: List[Staff], characters: List[Character], relations: List[Relation],
                 externalLinks: List[dict]):
        self.id = id
        self.title = title
        self.description = description
        self.episodes = episodes
        self.duration = duration
        self.genres = genres
        self.season = season
        self.seasonYear = seasonYear
        self.type = type
        self.status = status
        self.averageScore = averageScore
        self.popularity = popularity
        self.favourites = favourites
        self.rankings = rankings
        self.coverImage = coverImage
        self.bannerImage = bannerImage
        self.trailer = trailer
        self.studios = studios
        self.staff = staff
        self.characters = characters
        self.relations = relations
        self.externalLinks = externalLinks

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title.to_dict(),
            "description": self.description.to_dict(),
            "episodes": self.episodes,
            "duration": self.duration,
            "genres": self.genres,
            "season": self.season,
            "seasonYear": self.seasonYear,
            "type": self.type,
            "status": self.status,
            "averageScore": self.averageScore,
            "popularity": self.popularity,
            "favourites": self.favourites,
            "rankings": self.rankings,
            "coverImage": self.coverImage,
            "bannerImage": self.bannerImage,
            "trailer": self.trailer.to_dict() if self.trailer else None,
            "studios": self.studios,
            "staff": [s.to_dict() for s in self.staff],
            "characters": [c.to_dict() for c in self.characters],
            "relations": [r.to_dict() for r in self.relations],
            "externalLinks": self.externalLinks
        }