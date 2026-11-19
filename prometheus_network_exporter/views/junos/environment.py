"""
Pythonifier for environment Views/Tabls
"""

from typing import Any

from ..loader import loadyaml

# Created from environment.yml below; declared for the type checker.
RoutingEngineTable: Any
SoftwareTable: Any
EnvironmentTable: Any

globals().update(loadyaml(__name__))
