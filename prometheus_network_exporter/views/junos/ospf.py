"""
Pythonifier for environment Views/Tabls
"""

from typing import Any

from ..loader import loadyaml

# Created from ospf.yml below; declared for the type checker.
OspfNeighborTable: Any
Ospf3NeighborTable: Any

globals().update(loadyaml(__name__))
