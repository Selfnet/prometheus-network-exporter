"""
Pythonifier for environment Views/Tabls
"""

from typing import Any

from ..loader import loadyaml

# Created from igmp.yml below; declared for the type checker.
IGMPGroupTable: Any

globals().update(loadyaml(__name__))
