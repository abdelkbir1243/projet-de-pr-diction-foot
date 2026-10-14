"""Identité des équipes et compétitions : noms d'affichage, slugs d'URL, codes, couleurs, correspondance avec les API externes."""
import difflib
import hashlib
import re
import unicodedata

# Noms du dataset → noms d'affichage complets
NOMS = {
    "Man City": "Manchester City", "Man United": "Manchester United", "Nott'm Forest": "Nottingham Forest", "Newcastle": "Newcastle United",
    "Tottenham": "Tottenham Hotspur", "West Ham": "West Ham United", "Wolves": "Wolverhampton", "Brighton": "Brighton & Hove Albion",
    "Leeds": "Leeds United", "Ipswich": "Ipswich Town", "Leicester": "Leicester City", "Coventry": "Coventry City", "Hull": "Hull City",
    "Sunderland": "Sunderland AFC", "Burnley": "Burnley FC",
    "Ath Madrid": "Atlético Madrid", "Ath Bilbao": "Athletic Club", "Sociedad": "Real Sociedad", "Betis": "Real Betis", "Celta": "Celta Vigo",
    "Espanol": "Espanyol", "Vallecano": "Rayo Vallecano", "Alaves": "Deportivo Alavés", "La Coruna": "Deportivo La Coruña",
    "Santander": "Racing Santander", "Malaga": "Málaga", "Oviedo": "Real Oviedo",
    "Paris SG": "Paris Saint-Germain", "St Etienne": "Saint-Étienne", "Le Havre": "Le Havre AC", "Le Mans": "Le Mans FC",
    "Dortmund": "Borussia Dortmund", "M'gladbach": "Borussia Mönchengladbach", "Ein Frankfurt": "Eintracht Frankfurt",
    "Leverkusen": "Bayer Leverkusen", "FC Koln": "1. FC Köln", "Mainz": "Mainz 05", "Hoffenheim": "TSG Hoffenheim", "St Pauli": "FC St. Pauli",
    "Hamburg": "Hamburger SV", "Elversberg": "SV Elversberg", "Bayern Munich": "Bayern Munich",
    "Sp Lisbon": "Sporting CP", "Sp Braga": "Sporting Braga", "St. Gilloise": "Union Saint-Gilloise", "Buyuksehyr": "İstanbul Başakşehir",
    "SK Rapid": "Rapid Vienna", "Olympiakos": "Olympiacos", "Club Brugge": "Club Brugge", "PSV Eindhoven": "PSV Eindhoven",
    "Inter": "Inter", "Milan": "AC Milan", "Roma": "AS Roma", "Verona": "Hellas Verona", "Napoli": "SSC Napoli",
}
CODES = {"Paris SG": "PSG", "Man City": "MCI", "Man United": "MUN", "Inter": "INT", "Milan": "MIL", "Real Madrid": "RMA", "Barcelona": "BAR",
         "Bayern Munich": "BAY", "Dortmund": "BVB", "RB Leipzig": "RBL", "Ath Madrid": "ATM", "Ath Bilbao": "ATH", "Juventus": "JUV"}

# Compétitions : code interne, code football-data.org, zones du classement (rangs inclus)
COMPETITIONS = [
    {"code": "E0", "fd": "PL", "slug": "premier-league", "name": "Premier League", "country": "Angleterre", "cc": "ENG",
     "zones": {"cl": [1, 4], "el": [5, 6], "rel": [18, 20]}, "covered": True},
    {"code": "SP1", "fd": "PD", "slug": "laliga", "name": "LaLiga", "country": "Espagne", "cc": "ESP",
     "zones": {"cl": [1, 4], "el": [5, 6], "rel": [18, 20]}, "covered": True},
    {"code": "I1", "fd": "SA", "slug": "serie-a", "name": "Serie A", "country": "Italie", "cc": "ITA",
     "zones": {"cl": [1, 4], "el": [5, 6], "rel": [18, 20]}, "covered": True},
    {"code": "D1", "fd": "BL1", "slug": "bundesliga", "name": "Bundesliga", "country": "Allemagne", "cc": "GER",
     "zones": {"cl": [1, 4], "el": [5, 6], "rel": [16, 18]}, "covered": True},
    {"code": "F1", "fd": "FL1", "slug": "ligue-1", "name": "Ligue 1", "country": "France", "cc": "FRA",
     "zones": {"cl": [1, 3], "el": [4, 5], "rel": [16, 18]}, "covered": True},
    {"code": "CL", "fd": "CL", "slug": "champions-league", "name": "Ligue des champions", "country": "Europe", "cc": "EUR",
     "zones": {}, "covered": False, "model": "cup"},
    {"code": "EL", "fd": "EL", "slug": "europa-league", "name": "Ligue Europa", "country": "Europe", "cc": "EUR",
     "zones": {}, "covered": False, "model": "cup"},
    {"code": "ECL", "fd": "ECL", "slug": "conference-league", "name": "Conference League", "country": "Europe", "cc": "EUR",
     "zones": {}, "covered": False, "model": "cup"},
]
PAR_CODE = {c["code"]: c for c in COMPETITIONS}
PAR_FD = {c["fd"]: c for c in COMPETITIONS}


def nom(equipe: str) -> str:
    return NOMS.get(equipe, equipe)


def slug(texte: str) -> str:
    t = unicodedata.normalize("NFKD", texte.replace("ß", "ss")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def code(equipe: str) -> str:
    if equipe in CODES:
        return CODES[equipe]
    mots = [m for m in re.split(r"[\s'.-]+", unicodedata.normalize("NFKD", nom(equipe)).encode("ascii", "ignore").decode()) if m and not m.isdigit()]
    mots = [m for m in mots if m.upper() not in ("FC", "AC", "AS", "SV", "SSC", "TSG", "AFC", "CF")] or mots
    if len(mots) == 1:
        return mots[0][:3].upper()
    c = "".join(m[0] for m in mots[:3])
    return (c + mots[-1][1:])[:3].upper()


def couleur(equipe: str) -> str:
    """Couleur déterministe (originale, sans rapport avec les couleurs officielles des clubs)."""
    h = int(hashlib.md5(equipe.encode()).hexdigest(), 16)
    teinte, sat, lum = h % 360, 45 + (h >> 9) % 20, 38 + (h >> 17) % 10
    import colorsys
    r, g, b = colorsys.hls_to_rgb(teinte / 360, lum / 100, sat / 100)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


# ---------------------------------------------------------------- correspondance avec les noms d'une API externe
_BRUIT = r"\b(fc|cf|afc|ac|as|ssc|sc|sv|tsg|rc|rcd|ud|cd|sd|ca|club|calcio|de|futbol|football|1\.|1|04|05|1846|1899|1907|1909|1913)\b"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().replace("&", " ")
    s = re.sub(_BRUIT, " ", s)
    return re.sub(r"[^a-z]+", " ", s).strip()


ALIAS_API = {  # noms football-data.org (normalisés) → noms du dataset, quand la similarité ne suffit pas
    "manchester city": "Man City", "manchester united": "Man United", "nottingham forest": "Nott'm Forest",
    "wolverhampton wanderers": "Wolves", "brighton hove albion": "Brighton", "tottenham hotspur": "Tottenham",
    "atletico madrid": "Ath Madrid", "club atletico madrid": "Ath Madrid", "athletic bilbao": "Ath Bilbao", "athletic": "Ath Bilbao",
    "real betis balompie": "Betis", "real betis": "Betis", "rc celta vigo": "Celta", "celta vigo": "Celta", "espanyol barcelona": "Espanol",
    "rayo vallecano madrid": "Vallecano", "rayo vallecano": "Vallecano", "deportivo alaves": "Alaves", "real sociedad": "Sociedad",
    "paris saint germain": "Paris SG", "borussia dortmund": "Dortmund", "borussia monchengladbach": "M'gladbach",
    "eintracht frankfurt": "Ein Frankfurt", "bayer leverkusen": "Leverkusen", "koln": "FC Koln", "mainz": "Mainz", "st pauli": "St Pauli",
    "hamburger": "Hamburg", "hoffenheim": "Hoffenheim", "bayern munchen": "Bayern Munich", "internazionale milano": "Inter", "inter": "Inter",
    "milan": "Milan", "roma": "Roma", "napoli": "Napoli", "hellas verona": "Verona", "racing santander": "Santander",
    "deportivo la coruna": "La Coruna", "real oviedo": "Oviedo", "stade rennais": "Rennes", "olympique lyonnais": "Lyon",
    "stade brestois": "Brest", "paris": "Paris FC", "stade brestois 29": "Brest", "olympique marseille": "Marseille", "hellas verona": "Verona",
}


def associer(nom_api: str, candidats: list[str]) -> str | None:
    """Associe un nom d'équipe d'une API externe à un nom du dataset (alias, puis similarité de chaînes)."""
    n = _norm(nom_api)
    if n in ALIAS_API:                                  # alias connu : la réponse est certaine (ou l'équipe est hors liste)
        return ALIAS_API[n] if ALIAS_API[n] in candidats else None
    table = {_norm(c): c for c in candidats} | {_norm(nom(c)): c for c in candidats}
    if n in table:
        return table[n]
    # nom du dataset contenu (mot entier) dans le nom de l'API : « Olympique de Marseille » → « Marseille »
    inclus = [(len(k), v) for k, v in table.items() if k and re.search(rf"\b{re.escape(k)}\b", n)]
    if inclus:
        return max(inclus)[1]
    m = difflib.get_close_matches(n, list(table), n=1, cutoff=0.8)
    return table[m[0]] if m else None
