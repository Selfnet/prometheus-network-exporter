"""
Pythonifier for environment Views/Tabls
"""

from typing import Any

from ..loader import loadyaml

# Created from bgp.yml below; declared for the type checker.
BGPNeighborTable: Any

globals().update(loadyaml(__name__))
