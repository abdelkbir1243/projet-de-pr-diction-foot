import re
import os

from footpred.version import MODELE, __version__


def test_versions_coherentes():
    racine = os.path.join(os.path.dirname(__file__), "..")
    py = open(os.path.join(racine, "pyproject.toml"), encoding="utf-8").read()
    assert re.search(r'^version = "([^"]+)"', py, re.M).group(1) == __version__
    maj, mineur = __version__.split(".")[:2]
    assert MODELE == f"v{maj}.{mineur}"
    from footpred import web
    assert web.VERSION == MODELE
