import collections
from typing import List

from .config.configuration import LabelConfiguration
import copy


def merge_dicts_by_key(first: dict, second: dict) -> dict:
    result = {}
    for key in first.keys():
        result[key] = {
            **first[key],
            **second.get(key, {})
        }
    return result


def create_list_from_dict(dictionary: dict, key: str) -> list:
    return [
        {
            key: dict_key,
            **dict_values
        } for dict_key, dict_values in dictionary.items()
    ]


def remove_empty(dictionary: dict) -> dict:
    return {
        key: value for key, value in dictionary.items() if value is not None
    }


def enrich_dict_from_upper_dict_by_labels(listing: dict, labels: List[LabelConfiguration], key: str) -> list:
    for dictionary in listing:
        data = {
            label.json_key: label.get_label(dictionary)
            for label in labels
        }
        data = remove_empty(data)
        if dictionary.get(key) is not None:
            dictionary[key] = [
                {**item, **data} for item in dictionary.get(key, [])
            ]
    return listing


def flatten(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def get_resource(name):
    """Return a file handle on a named resource next to this module."""
    # get_resource_reader() may not exist or may return None, which this
    # code doesn't handle.
    reader = __loader__.get_resource_reader(__name__)
    return reader.open_resource(name)
