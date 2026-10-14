"""Chaque page de l'application Streamlit s'affiche sans erreur à partir des données publiées (web/data)."""
import json
import os

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PAGES = ["selection", "accueil", "predictions", "equipes", "competitions", "cotes", "assistant", "performance", "methode", "page_match"]


def _script(tmp_path, fn):
    p = tmp_path / f"{fn}.py"
    p.write_text(f"import sys; sys.path.insert(0, {RACINE!r})\nimport streamlit as st\nst.set_page_config(layout='wide')\n"
                 + (f"from appui import selection\nselection.page()\n" if fn == "selection" else f"from appui import pages\npages.{fn}()\n"), encoding="utf-8")
    return str(p)


@pytest.mark.parametrize("fn", PAGES)
def test_page(fn, tmp_path, monkeypatch):
    monkeypatch.setenv("GOALGEBRA_MAJ_AUTO", "0")          # pas de recalcul du modèle pendant les tests
    at = AppTest.from_file(_script(tmp_path, fn), default_timeout=120)
    if fn == "page_match":
        ms = json.load(open(os.path.join(RACINE, "web", "data", "matches.json"), encoding="utf-8"))
        at.query_params["m"] = next(m["slug"] for m in ms if m.get("prediction"))
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_assistant_repond(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALGEBRA_MAJ_AUTO", "0")
    at = AppTest.from_file(_script(tmp_path, "assistant"), default_timeout=120).run()
    for q in ["C'est quoi les xG ?", "Le modèle est-il fiable ?", "Matchs de demain"]:
        at.chat_input[0].set_value(q).run()
        assert not at.exception
        assert at.session_state.chat[-1]["role"] == "assistant" and at.session_state.chat[-1]["content"]
