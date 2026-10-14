"""Chargement des données (dataset public xgabora, mis à jour régulièrement, ~50 Mo)."""
import os
import numpy as np
import pandas as pd
from .config import DATA_URL


def saison(dates: pd.Series) -> np.ndarray:
    """Saison = année de début (juillet → juin) : un match de mars 2026 appartient à la saison 2025 (2025/26)."""
    return np.where(dates.dt.month >= 7, dates.dt.year, dates.dt.year - 1)


COLONNES = ["Division", "MatchDate", "HomeTeam", "AwayTeam", "HomeElo", "AwayElo", "FTHome", "FTAway", "FTResult", "HTHome", "HTAway",
            "HomeTarget", "AwayTarget", "OddHome", "OddDraw", "OddAway", "MaxHome", "MaxDraw", "MaxAway", "Over25", "Under25",
            "HomeShots", "AwayShots", "HomeCorners", "AwayCorners", "HomeYellow", "AwayYellow", "HomeRed", "AwayRed", "HomeFouls", "AwayFouls"]


def charger_matchs(source: str | None = None, cache: str | None = "data/Matches.csv", toutes_colonnes: bool = False) -> pd.DataFrame:
    """Charge Matches.csv depuis `source` (chemin ou URL). Sans source : le cache local s'il existe, sinon l'URL publique.
    Par défaut, seules les colonnes utiles au modèle sont chargées (moins de mémoire, utile sur Streamlit Cloud)."""
    if source is None:
        source = cache if cache and os.path.exists(cache) else DATA_URL
    raw = pd.read_csv(source, parse_dates=["MatchDate"], low_memory=False, usecols=None if toutes_colonnes else COLONNES)
    raw["Season"] = saison(raw.MatchDate)
    if cache and source == DATA_URL:
        os.makedirs(os.path.dirname(cache) or ".", exist_ok=True)
        raw.drop(columns="Season").to_csv(cache, index=False)
    return raw
