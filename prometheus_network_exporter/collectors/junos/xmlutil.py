"""Helpers for reading Junos RPC replies with lxml.

Junos replies carry a release specific default namespace. Depending on
whether a PyEZ table ran earlier in the session the namespace may or may not
have been stripped, so every lookup here matches on the local tag name only.
"""

from __future__ import annotations

import collections
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

from lxml import etree
from prometheus_client.core import GaugeMetricFamily

RPC_DECORATOR_ARGS = ("dev_timeout", "normalize", "ignore_warning", "filter_xml")


def _xpath(path: str) -> str:
    """Turn ``a/b`` into ``{*}a/{*}b`` while keeping ``.`` and ``//`` intact."""
    parts = []
    for part in path.split("/"):
        if part in ("", ".", ".."):
            parts.append(part)
        else:
            parts.append("{*}" + part)
    return "/".join(parts)


def localname(element) -> str:
    return etree.QName(element).localname


def find(element, path: str):
    return element.find(_xpath(path))


def findall(element, path: str) -> list:
    return element.findall(_xpath(path))


def iter_items(element, names: Iterable[str]) -> Iterator:
    """Yield every descendant whose local tag name is in ``names``."""
    wanted = set(names)
    for item in element.iter():
        if isinstance(item.tag, str) and localname(item) in wanted:
            yield item


def text(element, path: str) -> Optional[str]:
    found = find(element, path)
    if found is None or found.text is None:
        return None
    value = found.text.strip()
    return value or None


def number(value: Optional[str]) -> Optional[float]:
    """Parse decimal or ``0x`` hexadecimal text, None when not numeric."""
    if value is None:
        return None
    value = value.strip()
    try:
        if value.lower().startswith("0x"):
            return float(int(value, 16))
        return float(value)
    except ValueError:
        return None


def seconds(element, path: str) -> Optional[float]:
    """Read ``junos:seconds`` from an element, falling back to numeric text."""
    found = find(element, path)
    if found is None:
        return None
    for key, value in found.attrib.items():
        if key == "seconds" or key.endswith("}seconds"):
            return number(value)
    return number(found.text)


def strip_port(address: Optional[str]) -> str:
    """``10.0.0.1+179`` becomes ``10.0.0.1``."""
    if address is None:
        return ""
    return address.split("+", 1)[0]


def label(value) -> str:
    return "" if value is None else str(value)


def is_ipv6(prefix: str) -> bool:
    return ":" in prefix


def family_matches(prefix: str, table: str) -> bool:
    """True when a watched prefix belongs into the given route table."""
    return is_ipv6(prefix) == ("inet6" in table)


class SchemaWatch:
    """Counts expected XML fields that were absent, per collector and field.

    Reset at the start of every scrape; exported by the status collector as
    ``pyez_junos_xml_missing_fields``.
    """

    def __init__(self):
        self.missing: Dict[Tuple[str, str], int] = collections.Counter()

    def record(self, collector: str, field: str) -> None:
        self.missing[(collector, field)] += 1

    def reset(self) -> None:
        self.missing.clear()


class Reader:
    """Field access bound to one collector that reports absent fields."""

    def __init__(self, watch: SchemaWatch, collector: str):
        self.watch = watch
        self.collector = collector

    def _missing(self, path: str) -> None:
        self.watch.record(self.collector, path)

    def text(self, element, path: str, required: bool = True) -> Optional[str]:
        value = text(element, path)
        if value is None and required:
            self._missing(path)
        return value

    def first_text(self, element, paths: Sequence[str], required: bool = True):
        for path in paths:
            value = text(element, path)
            if value is not None:
                return value
        if required:
            self._missing("|".join(paths))
        return None

    def number(self, element, path: str, required: bool = True) -> Optional[float]:
        value = number(text(element, path))
        if value is None and required:
            self._missing(path)
        return value

    def seconds(self, element, path: str, required: bool = True) -> Optional[float]:
        value = seconds(element, path)
        if value is None and required:
            self._missing(path)
        return value


def add(metric, labels: List[str], value: Optional[float]) -> None:
    """Add a sample unless the value is unknown. Unknown is never exported as 0."""
    if value is not None:
        metric.add_metric(labels, value)


def state_set(
    metric: GaugeMetricFamily,
    labels: Sequence[str],
    current: Optional[str],
    states: Sequence[str],
) -> None:
    """Emit one sample per known state, 1 for the current one.

    An unknown current state is emitted as an additional sample so that it
    stays visible instead of disappearing.
    """
    labels = list(labels)
    matched = False
    for state in states:
        hit = current is not None and current.lower() == state.lower()
        matched = matched or hit
        metric.add_metric(labels + [state], 1.0 if hit else 0.0)
    if current is not None and not matched:
        metric.add_metric(labels + [current], 1.0)
