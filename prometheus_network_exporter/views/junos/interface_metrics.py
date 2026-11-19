"""
Pythonifier for environment Views/Tabls
"""

from typing import Any

from ..loader import loadyaml

# Created from interface_metrics.yml below; declared for the type checker.
MetricsTable: Any

globals().update(loadyaml(__name__))
