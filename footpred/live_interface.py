"""Phase 6 (préparée, non activée) : interface du futur modèle live, P(résultat final | état connu à la minute t).

Ce qui manque : un flux d'événements en direct horodatés (tirs avec xG, cartons, remplacements, corners, entrées dans la
surface) et un historique d'événements suffisant pour l'entraînement. Les sources gratuites utilisées par Goalgebra ne
fournissent que les scores (football-data.org, avec quelques minutes de retard) : aucun modèle live n'est donc publié, et
aucune donnée n'est simulée. Fournisseurs possibles (payants, à évaluer) : Opta/Stats Perform, StatsBomb, Sportmonks, API-Football.

Règles déjà garanties par le code :
  - une prédiction live est enregistrée à part (prediction_type = "live", match_minute) et ne remplace jamais la prédiction ou la
    sélection d'avant-match figées au journal (footpred.web.figer_selection, tests/test_selection.py) ;
  - le modèle live sera évalué séparément, minute de référence par minute de référence (15, 30, 45, 60, 75).
"""
from dataclasses import dataclass, field
from typing import Protocol

MINUTES_REFERENCE = (15, 30, 45, 60, 75)


@dataclass(frozen=True)
class Instantane:
    """État d'un match à la minute t, construit uniquement avec les événements déjà survenus."""
    match_id: str
    minute: int
    score_dom: int
    score_ext: int
    rouges_dom: int = 0
    rouges_ext: int = 0
    xg_dom: float | None = None             # xG fournisseur cumulé (jamais le xG proxy)
    xg_ext: float | None = None
    xg_dom_10min: float | None = None
    xg_ext_10min: float | None = None
    tirs_cadres_dom: int | None = None
    tirs_cadres_ext: int | None = None
    corners_dom: int | None = None
    corners_ext: int | None = None
    remplacements_dom: int | None = None
    remplacements_ext: int | None = None
    proba_avant_match: tuple[float, float, float] | None = None
    horodatage_source: str = ""             # instant où la source a publié l'état (preuve de disponibilité)


@dataclass
class PredictionLive:
    match_id: str
    minute: int
    p_resultat: tuple[float, float, float]
    p_prochain_but: tuple[float, float, float] | None = None      # domicile, extérieur, aucun
    buts_restants_attendus: float | None = None
    prediction_type: str = field(default="live", init=False)
    model_version: str = "live-non-active"


class FournisseurEvenements(Protocol):
    """À implémenter pour un fournisseur réel ; aucune implémentation fictive n'est fournie."""

    def instantane(self, match_id: str, minute: int) -> Instantane: ...

    def historique(self, saisons: list[int]) -> list[Instantane]: ...


class ModeleLive:
    """Modèle de buts restants (Poisson à intensité dépendant du temps restant, du score et des cartons rouges), puis
    convolution avec le score courant. Non entraîné tant qu'aucun historique d'événements n'est disponible."""

    def __init__(self, fournisseur: FournisseurEvenements | None = None):
        self.fournisseur = fournisseur

    def predire(self, etat: Instantane) -> PredictionLive:
        raise NotImplementedError("Modèle live non activé : un flux d'événements en direct et un historique d'entraînement sont "
                                  "nécessaires (voir footpred/live_interface.py).")
