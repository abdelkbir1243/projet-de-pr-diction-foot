"""Base de données de la plateforme (PostgreSQL en production, SQLite en local et dans les tests).

DATABASE_URL, par exemple :
    postgresql+psycopg://goalgebra:motdepasse@db:5432/goalgebra      (docker compose)
    sqlite:///data/goalgebra.db                                       (par défaut, développement)

Tables : comptes, équipes suivies, clés d'API et leur consommation, tentatives de connexion (anti force brute),
exécutions du pipeline (supervision), journal des prédictions (copie consultable de journal.json), événements d'audit.
"""
import os
from datetime import datetime, timezone
from functools import lru_cache

from sqlalchemy import (Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, event,
                        select)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


def maintenant() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Utilisateur(Base):
    __tablename__ = "utilisateurs"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    nom: Mapped[str] = mapped_column(String(80), default="")
    mot_de_passe: Mapped[str] = mapped_column(String(100))            # empreinte bcrypt, jamais le mot de passe
    role: Mapped[str] = mapped_column(String(10), default="user")     # user | admin
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)
    derniere_connexion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    favoris: Mapped[list["Favori"]] = relationship(back_populates="utilisateur", cascade="all, delete-orphan")
    cles: Mapped[list["CleApi"]] = relationship(back_populates="utilisateur", cascade="all, delete-orphan")


class Favori(Base):
    __tablename__ = "favoris"
    __table_args__ = (UniqueConstraint("utilisateur_id", "equipe"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    utilisateur_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True)
    equipe: Mapped[str] = mapped_column(String(80))
    utilisateur: Mapped[Utilisateur] = relationship(back_populates="favoris")


class CleApi(Base):
    __tablename__ = "cles_api"
    id: Mapped[int] = mapped_column(primary_key=True)
    utilisateur_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True)
    nom: Mapped[str] = mapped_column(String(60), default="")
    prefixe: Mapped[str] = mapped_column(String(16), index=True)      # affiché pour reconnaître la clé (« gg_ab12cd… »)
    empreinte: Mapped[str] = mapped_column(String(64), unique=True)   # SHA-256 de la clé complète
    quota_jour: Mapped[int] = mapped_column(Integer, default=1000)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)
    derniere_utilisation: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoquee: Mapped[bool] = mapped_column(Boolean, default=False)
    utilisateur: Mapped[Utilisateur] = relationship(back_populates="cles")


class UsageApi(Base):
    __tablename__ = "usage_api"
    __table_args__ = (UniqueConstraint("cle_id", "jour"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    cle_id: Mapped[int] = mapped_column(ForeignKey("cles_api.id", ondelete="CASCADE"), index=True)
    jour: Mapped[str] = mapped_column(String(10))                     # AAAA-MM-JJ (UTC)
    requetes: Mapped[int] = mapped_column(Integer, default=0)


class TentativeConnexion(Base):
    __tablename__ = "tentatives_connexion"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), index=True)
    le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant, index=True)
    reussie: Mapped[bool] = mapped_column(Boolean, default=False)


class ExecutionPipeline(Base):
    __tablename__ = "executions_pipeline"
    id: Mapped[int] = mapped_column(primary_key=True)
    debut: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant, index=True)
    fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    statut: Mapped[str] = mapped_column(String(12), default="en_cours")   # en_cours | succes | echec
    mode: Mapped[str | None] = mapped_column(String(12), nullable=True)
    matchs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dernier_resultat: Mapped[str | None] = mapped_column(String(10), nullable=True)
    en_retard: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    message: Mapped[str] = mapped_column(Text, default="")


class Prediction(Base):
    """Copie consultable du journal : une ligne par match, figée avant le coup d'envoi (jamais modifiée ensuite, sauf le résultat)."""
    __tablename__ = "predictions"
    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    faite_le: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    coup_envoi: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    domicile: Mapped[str] = mapped_column(String(80))
    exterieur: Mapped[str] = mapped_column(String(80))
    p_dom: Mapped[float] = mapped_column(Float)
    p_nul: Mapped[float] = mapped_column(Float)
    p_ext: Mapped[float] = mapped_column(Float)
    modele: Mapped[str] = mapped_column(String(20), default="")
    resultat: Mapped[str | None] = mapped_column(String(1), nullable=True)
    score: Mapped[str | None] = mapped_column(String(10), nullable=True)


class SessionWeb(Base):
    """Session de l'application (cookie « gg_session ») : seule l'empreinte SHA-256 du jeton est stockée ; révocable."""
    __tablename__ = "sessions_web"
    id: Mapped[int] = mapped_column(primary_key=True)
    empreinte: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    utilisateur_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)
    expire_le: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoquee: Mapped[bool] = mapped_column(Boolean, default=False)


class Audit(Base):
    __tablename__ = "audit"
    id: Mapped[int] = mapped_column(primary_key=True)
    le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant, index=True)
    acteur: Mapped[str] = mapped_column(String(254), default="systeme")
    action: Mapped[str] = mapped_column(String(60))
    detail: Mapped[str] = mapped_column(Text, default="")


def url_base() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    racine = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    os.makedirs(racine, exist_ok=True)
    return f"sqlite:///{os.path.join(racine, 'goalgebra.db')}"


@lru_cache(maxsize=4)
def moteur(url: str | None = None):
    url = url or url_base()
    eng = create_engine(url, pool_pre_ping=True, future=True,
                        connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
    if url.startswith("sqlite"):
        @event.listens_for(eng, "connect")
        def _fk(conn, _):                                    # cascades ON DELETE sous SQLite
            conn.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(eng)
    return eng


def session(url: str | None = None):
    return sessionmaker(bind=moteur(url), expire_on_commit=False)()


def auditer(s, action: str, detail: str = "", acteur: str = "systeme"):
    s.add(Audit(action=action, detail=detail[:2000], acteur=acteur))


__all__ = ["Base", "SessionWeb", "Utilisateur", "Favori", "CleApi", "UsageApi", "TentativeConnexion", "ExecutionPipeline", "Prediction", "Audit",
           "moteur", "session", "auditer", "maintenant", "select"]
