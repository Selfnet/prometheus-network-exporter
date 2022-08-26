from jnpr.junos.factory.factory_loader import FactoryLoader
from importlib.resources import read_text
import yaml


def loadyaml(module_name: str):
    module, name = module_name.rsplit('.', maxsplit=1)
    return FactoryLoader().load(yaml.load(read_text(module, f"{name}.yml"), Loader=yaml.SafeLoader))
