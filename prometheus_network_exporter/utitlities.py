import collections
import functools
from datetime import datetime, timedelta
from typing import List

from .config.configuration import LabelConfiguration


def merge_dicts_by_key(first: dict, second: dict) -> dict:
    result = {}
    for key in first.keys():
        result[key] = {**first[key], **second.get(key, {})}
    return result


def create_list_from_dict(dictionary: dict, key: str, format_str="{}") -> list:
    return [
        {key: format_str.format(dict_key), **dict_values}
        for dict_key, dict_values in dictionary.items()
    ]


def remove_empty(dictionary: dict) -> dict:
    return {
        key: value
        for key, value in dictionary.items()
        if value is not None and value != str(None)
    }


def enrich_dict_from_upper_dict_by_labels(
    listing: dict, labels: List[LabelConfiguration], key: str
) -> list:
    for dictionary in listing:
        data = {label.json_key: label.get_label(dictionary) for label in labels}
        data = remove_empty(data)
        if dictionary.get(key) is not None:
            dictionary[key] = [{**item, **data} for item in dictionary.get(key, [])]
    return listing


def flatten(d, parent_key="", sep="_"):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def timed_cache(**timedelta_kwargs):
    def _wrapper(f):
        maxsize = timedelta_kwargs.pop("maxsize", 128)
        typed = timedelta_kwargs.pop("typed", False)
        update_delta = timedelta(**timedelta_kwargs)
        next_update = datetime.utcnow() - update_delta
        # Apply @lru_cache to f
        f = functools.lru_cache(maxsize=maxsize, typed=typed)(f)

        @functools.wraps(f)
        def _wrapped(*args, **kwargs):
            timed_cache_clear()
            return f(*args, **kwargs)

        def timed_cache_clear():
            """Clear cache when time expires"""
            nonlocal next_update
            now = datetime.utcnow()
            if now >= next_update:
                f.cache_clear()
                next_update = now + update_delta

        def cache_info():
            """Report cache statistics"""
            timed_cache_clear()
            return f.cache_info()

        _wrapped.cache_info = cache_info
        _wrapped.cache_clear = f.cache_clear
        return _wrapped

    return _wrapper
