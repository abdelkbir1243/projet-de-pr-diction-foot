"""Comptes utilisateurs, mots de passe et clés d'API.

Sécurité :
  - mots de passe hachés avec bcrypt (coût 12), jamais stockés ni journalisés en clair ;
  - politique minimale : 10 caractères, au moins une lettre et un chiffre ;
  - anti force brute : 5 échecs en 15 minutes bloquent l'adresse pendant 15 minutes ;
  - message d'erreur identique que l'adresse existe ou non (pas d'énumération des comptes) ;
  - clés d'API aléatoires (secrets.token_urlsafe), seule leur empreinte SHA-256 est conservée ; la clé n'est montrée qu'une fois.
"""
import hashlib
import os
import re
import secrets
from datetime import timedelta

import bcrypt
from sqlalchemy import func, select

from .db import (Audit, CleApi, Favori, SessionWeb, TentativeConnexion, UsageApi, Utilisateur, auditer, maintenant, session)

DUREE_SESSION = timedelta(days=14)

ECHECS_MAX, FENETRE = 5, timedelta(minutes=15)
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,189}\.[a-z]{2,}$", re.I)


class ErreurCompte(ValueError):
    pass


# ---------------------------------------------------------------- mots de passe
def hacher(mdp: str) -> str:
    return bcrypt.hashpw(mdp.encode()[:72], bcrypt.gensalt(12)).decode()


def verifier(mdp: str, empreinte: str) -> bool:
    try:
        return bcrypt.checkpw(mdp.encode()[:72], empreinte.encode())
    except ValueError:
        return False


_FACTICE = hacher("mot-de-passe-factice-0")     # temps de réponse identique pour une adresse inconnue


def controler_mdp(mdp: str):
    if len(mdp) < 10 or not re.search(r"[A-Za-z]", mdp) or not re.search(r"\d", mdp):
        raise ErreurCompte("Le mot de passe doit contenir au moins 10 caractères, dont une lettre et un chiffre.")
    if len(mdp.encode()) > 72:
        raise ErreurCompte("Le mot de passe est trop long (72 octets au maximum).")


def normaliser(email: str) -> str:
    return (email or "").strip().lower()


# ---------------------------------------------------------------- comptes
def creer_utilisateur(email: str, mdp: str, nom: str = "", role: str = "user", s=None) -> Utilisateur:
    email = normaliser(email)
    if not EMAIL.match(email):
        raise ErreurCompte("Adresse e-mail invalide.")
    controler_mdp(mdp)
    propre = s is None
    s = s or session()
    try:
        if s.scalar(select(Utilisateur).where(Utilisateur.email == email)):
            raise ErreurCompte("Un compte existe déjà avec cette adresse.")
        u = Utilisateur(email=email, nom=nom.strip()[:80], mot_de_passe=hacher(mdp), role=role)
        s.add(u); auditer(s, "compte_cree", f"{email} ({role})", acteur=email)
        s.commit()
        return u
    finally:
        if propre:
            s.close()


def bloque(email: str, s) -> bool:
    depuis = maintenant() - FENETRE
    n = s.scalar(select(func.count()).select_from(TentativeConnexion)
                 .where(TentativeConnexion.email == email, TentativeConnexion.le >= depuis, TentativeConnexion.reussie.is_(False)))
    return (n or 0) >= ECHECS_MAX


def authentifier(email: str, mdp: str) -> Utilisateur:
    """Renvoie l'utilisateur, ou lève ErreurCompte avec un message qui ne révèle pas si l'adresse existe."""
    email = normaliser(email)
    with session() as s:
        if bloque(email, s):
            raise ErreurCompte("Trop de tentatives. Réessaie dans 15 minutes.")
        u = s.scalar(select(Utilisateur).where(Utilisateur.email == email))
        if u:
            ok = verifier(mdp, u.mot_de_passe) and u.actif
        else:
            verifier(mdp, _FACTICE)                 # même durée de calcul : on ne révèle pas si l'adresse existe
            ok = False
        s.add(TentativeConnexion(email=email, reussie=bool(ok)))
        if ok:
            u.derniere_connexion = maintenant()
        s.commit()
        if not ok:
            raise ErreurCompte("Adresse ou mot de passe incorrect.")
        s.refresh(u)
        return u


def changer_mdp(uid: int, ancien: str, nouveau: str):
    controler_mdp(nouveau)
    with session() as s:
        u = s.get(Utilisateur, uid)
        if not u or not verifier(ancien, u.mot_de_passe):
            raise ErreurCompte("Mot de passe actuel incorrect.")
        u.mot_de_passe = hacher(nouveau); auditer(s, "mdp_change", u.email, acteur=u.email)
        s.commit()
    fermer_toutes_sessions(uid)


def initialiser_admin():
    """Crée le premier administrateur depuis ADMIN_EMAIL / ADMIN_PASSWORD (variables d'environnement), s'il n'existe pas."""
    email, mdp = os.environ.get("ADMIN_EMAIL"), os.environ.get("ADMIN_PASSWORD")
    if not email or not mdp:
        return None
    with session() as s:
        u = s.scalar(select(Utilisateur).where(Utilisateur.email == normaliser(email)))
        if u:
            if u.role != "admin":
                u.role = "admin"; s.commit()
            return u
    return creer_utilisateur(email, mdp, "Administrateur", role="admin")


# ---------------------------------------------------------------- sessions de l'application (cookie)
def ouvrir_session(uid: int) -> str:
    jeton = secrets.token_urlsafe(32)
    with session() as s:
        s.add(SessionWeb(empreinte=empreinte(jeton), utilisateur_id=uid, expire_le=maintenant() + DUREE_SESSION)); s.commit()
    return jeton


def utilisateur_de_session(jeton: str | None) -> Utilisateur | None:
    if not jeton or len(jeton) > 100:
        return None
    with session() as s:
        sw = s.scalar(select(SessionWeb).where(SessionWeb.empreinte == empreinte(jeton)))
        if not sw or sw.revoquee or _aware(sw.expire_le) < maintenant():
            return None
        u = s.get(Utilisateur, sw.utilisateur_id)
        return u if u and u.actif else None


def fermer_session(jeton: str | None):
    if not jeton:
        return
    with session() as s:
        sw = s.scalar(select(SessionWeb).where(SessionWeb.empreinte == empreinte(jeton)))
        if sw:
            sw.revoquee = True; s.commit()


def fermer_toutes_sessions(uid: int):
    with session() as s:
        for sw in s.scalars(select(SessionWeb).where(SessionWeb.utilisateur_id == uid, SessionWeb.revoquee.is_(False))):
            sw.revoquee = True
        s.commit()


def _aware(d):
    from datetime import timezone
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)                # SQLite renvoie des dates sans fuseau


def utilisateur_par_email(email: str, creer: bool = False, nom: str = "") -> Utilisateur | None:
    """Connexion déléguée (OIDC, ex. Google via st.login) : le compte est créé au premier passage, sans mot de passe utilisable."""
    email = normaliser(email)
    with session() as s:
        u = s.scalar(select(Utilisateur).where(Utilisateur.email == email))
        if u or not creer:
            return u if (u and u.actif) else None
        u = Utilisateur(email=email, nom=nom[:80], mot_de_passe=hacher(secrets.token_urlsafe(24)), role="user")
        s.add(u); auditer(s, "compte_cree", f"{email} (oidc)", acteur=email); s.commit(); s.refresh(u)
        return u


# ---------------------------------------------------------------- favoris
def favoris(uid: int) -> list[str]:
    with session() as s:
        return list(s.scalars(select(Favori.equipe).where(Favori.utilisateur_id == uid)))


def basculer_favori(uid: int, equipe: str) -> bool:
    """Ajoute ou retire une équipe suivie ; renvoie True si elle est désormais suivie."""
    with session() as s:
        f = s.scalar(select(Favori).where(Favori.utilisateur_id == uid, Favori.equipe == equipe))
        if f:
            s.delete(f); s.commit(); return False
        s.add(Favori(utilisateur_id=uid, equipe=equipe[:80])); s.commit(); return True


# ---------------------------------------------------------------- clés d'API
def empreinte(cle: str) -> str:
    return hashlib.sha256(cle.encode()).hexdigest()


def creer_cle(uid: int, nom: str = "", quota_jour: int | None = None) -> str:
    """Renvoie la clé en clair (à montrer une seule fois)."""
    cle = "gg_" + secrets.token_urlsafe(32)
    with session() as s:
        if s.scalar(select(func.count()).select_from(CleApi).where(CleApi.utilisateur_id == uid, CleApi.revoquee.is_(False))) >= 5:
            raise ErreurCompte("5 clés actives au maximum : révoque une clé avant d'en créer une autre.")
        s.add(CleApi(utilisateur_id=uid, nom=nom.strip()[:60], prefixe=cle[:10], empreinte=empreinte(cle),
                     quota_jour=quota_jour or int(os.environ.get("API_QUOTA_JOUR", "1000"))))
        u = s.get(Utilisateur, uid); auditer(s, "cle_creee", f"{cle[:10]}…", acteur=u.email if u else "?")
        s.commit()
    return cle


def cles(uid: int) -> list[CleApi]:
    with session() as s:
        return list(s.scalars(select(CleApi).where(CleApi.utilisateur_id == uid).order_by(CleApi.cree_le.desc())))


def revoquer_cle(uid: int, cle_id: int, admin: bool = False):
    with session() as s:
        k = s.get(CleApi, cle_id)
        if k and (admin or k.utilisateur_id == uid):
            k.revoquee = True; auditer(s, "cle_revoquee", k.prefixe); s.commit()


def consommer(cle: str) -> tuple[CleApi | None, str]:
    """Vérifie une clé et décompte une requête. Renvoie (clé, "") ou (None, raison)."""
    if not cle or not cle.startswith("gg_"):
        return None, "clé manquante ou invalide"
    jour = maintenant().date().isoformat()
    with session() as s:
        k = s.scalar(select(CleApi).where(CleApi.empreinte == empreinte(cle)))
        if not k or k.revoquee:
            return None, "clé manquante ou invalide"
        u = s.get(Utilisateur, k.utilisateur_id)
        if not u or not u.actif:
            return None, "compte désactivé"
        usage = s.scalar(select(UsageApi).where(UsageApi.cle_id == k.id, UsageApi.jour == jour))
        if not usage:
            usage = UsageApi(cle_id=k.id, jour=jour, requetes=0); s.add(usage)
        if usage.requetes >= k.quota_jour:
            return None, f"quota quotidien atteint ({k.quota_jour} requêtes)"
        usage.requetes += 1
        k.derniere_utilisation = maintenant()
        s.commit(); s.refresh(k)
        return k, ""


# ---------------------------------------------------------------- administration
def utilisateurs() -> list[Utilisateur]:
    with session() as s:
        return list(s.scalars(select(Utilisateur).order_by(Utilisateur.cree_le.desc())))


def modifier_utilisateur(uid: int, acteur: str, actif: bool | None = None, role: str | None = None):
    with session() as s:
        u = s.get(Utilisateur, uid)
        if not u:
            return
        if actif is not None:
            u.actif = actif
        if role in ("user", "admin"):
            u.role = role
        auditer(s, "utilisateur_modifie", f"{u.email} actif={u.actif} role={u.role}", acteur=acteur); s.commit()


def usage_api(jours: int = 14):
    depuis = (maintenant() - timedelta(days=jours)).date().isoformat()
    with session() as s:
        return s.execute(select(UsageApi.jour, CleApi.prefixe, Utilisateur.email, UsageApi.requetes)
                         .join(CleApi, CleApi.id == UsageApi.cle_id).join(Utilisateur, Utilisateur.id == CleApi.utilisateur_id)
                         .where(UsageApi.jour >= depuis).order_by(UsageApi.jour.desc())).all()


def journal_audit(n: int = 200) -> list[Audit]:
    with session() as s:
        return list(s.scalars(select(Audit).order_by(Audit.le.desc()).limit(n)))
