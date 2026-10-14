"""Garantie centrale du projet : les variables d'un match n'utilisent AUCUNE information de ce match ni des suivants."""
import numpy as np
from footpred.features import construire
from footpred import config as C


def test_modifier_un_resultat_ne_change_pas_ses_propres_variables(raw_petit):
    d0 = construire(raw_petit)
    cible = d0.X.index[len(d0.X) // 2]
    ligne = d0.X.loc[cible]
    raw2 = raw_petit.copy()
    k = raw2[(raw2.MatchDate == ligne.MatchDate) & (raw2.HomeTeam == ligne.HomeTeam) & (raw2.AwayTeam == ligne.AwayTeam)].index
    assert len(k) == 1
    raw2.loc[k, ["FTHome", "FTAway", "HomeTarget", "AwayTarget"]] = [9, 0, 20, 0]          # résultat falsifié
    raw2.loc[k, "FTResult"] = "H"
    d1 = construire(raw2)
    # 1) les variables du match lui-même sont identiques
    np.testing.assert_allclose(d0.X.loc[cible, C.FE_B].astype(float), d1.X.loc[cible, C.FE_B].astype(float))
    # 2) celles des matchs antérieurs aussi
    avant = d0.X.index[d0.X.MatchDate < ligne.MatchDate]
    np.testing.assert_allclose(d0.X.loc[avant, C.FE_B].astype(float), d1.X.loc[avant, C.FE_B].astype(float))
    # 3) mais le match suivant de l'équipe à domicile, lui, voit le changement (le test n'est pas vide)
    ap = d0.X[(d0.X.MatchDate > ligne.MatchDate) & ((d0.X.HomeTeam == ligne.HomeTeam) | (d0.X.AwayTeam == ligne.HomeTeam))].index[0]
    assert not np.allclose(d0.X.loc[ap, ["g_lh", "g_la", "pi_diff"]].astype(float), d1.X.loc[ap, ["g_lh", "g_la", "pi_diff"]].astype(float))
