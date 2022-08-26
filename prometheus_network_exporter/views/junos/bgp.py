"""
Pythonifier for environment Views/Tabls
"""
from ..loader import loadyaml

globals().update(loadyaml(__name__))

