"""Helpers for reading Junos RPC replies with lxml.

Junos replies carry a release specific default namespace. Depending on
whether a PyEZ table ran earlier in the session the namespace may or may not
have been stripped, so every lookup here matches on the local tag name only.
"""

from __future__ import annotations

import collections
import logging
import math
import re
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

from lxml import etree
from prometheus_client.core import GaugeMetricFamily

RPC_DECORATOR_ARGS = ("dev_timeout", "normalize", "ignore_warning", "filter_xml")
UNKNOWN_STATE = "unknown"
LOGGER = logging.getLogger("network_exporter")


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
            result = float(int(value, 16))
        else:
            result = float(value)
    except (ValueError, OverflowError):
        return None
    # "nan", "inf" and overflowing text parse as floats but are not measurements.
    return result if math.isfinite(result) else None


def seconds(element, path: str) -> Optional[float]:
    """Read ``junos:seconds`` from an element, falling back to numeric text."""
    found = find(element, path)
    if found is None:
        return None
    for key, value in found.attrib.items():
        if key == "seconds" or key.endswith("}seconds"):
            return number(value)
    return number(found.text)


def slug(value: str) -> str:
    """``Software input control plane drops`` becomes ``software_input_control_plane_drops``."""
    return re.sub(r"[^a-z0-9]+", "_", (value or "").lower()).strip("_")


def all_text(element) -> str:
    """Every text node below the element, for replies Junos only renders as text.

    Junos answers a CLI command without an XML schema with a single
    ``<output>`` element; reading all text covers that and odd wrappers alike.
    """
    return "\n".join(part for part in element.itertext())


def numeric_leaves(element) -> Iterator[Tuple[str, float]]:
    """``(tag, value)`` for every direct child without children and with a numeric text."""
    for child in element:
        if not isinstance(child.tag, str) or len(child):
            continue
        value = number(child.text)
        if value is not None:
            yield localname(child), value


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

    def record(self, field: str) -> None:
        """Note an unexpected value under the given field name."""
        self.watch.record(self.collector, field)

    def unexpected_state(self, path: str, current: Optional[str]) -> None:
        LOGGER.info("%s: unexpected %s %r", self.collector, path, current)
        self.watch.record(self.collector, f"{path}:unexpected-value")

    def unique(self, families: Iterable):
        return unique(families, self.watch, self.collector)

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

    def first_seconds(self, element, paths: Sequence[str], required: bool = False):
        for path in paths:
            value = seconds(element, path)
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
) -> bool:
    """Emit one sample per known state plus ``unknown``, 1 for the current one.

    The label values are fixed: a state string the collector does not know
    lights the ``unknown`` sample instead of becoming a new label value, so
    the cardinality stays bounded whatever the device sends. Returns whether
    the current state was one of the known ones.
    """
    labels = list(labels)
    matched = False
    for state in states:
        hit = current is not None and current.lower() == state.lower()
        matched = matched or hit
        metric.add_metric(labels + [state], 1.0 if hit else 0.0)
    unknown = current is not None and not matched
    metric.add_metric(labels + [UNKNOWN_STATE], 1.0 if unknown else 0.0)
    return not unknown


def unique(families: Iterable, watch: Optional["SchemaWatch"] = None, collector: str = ""):
    """Drop samples that repeat a name and label set within a family.

    Prometheus rejects a whole scrape over one duplicate series, which would
    take every metric of the device down with it. Duplicates are counted in
    the schema watch so that they remain visible.
    """
    for family in families:
        seen = set()
        kept = []
        for sample in family.samples:
            key = (sample.name, tuple(sorted(sample.labels.items())))
            if key in seen:
                if watch is not None:
                    watch.record(collector, f"duplicate:{sample.name}")
                LOGGER.info("%s: dropped duplicate series %s%s", collector, sample.name, sample.labels)
                continue
            seen.add(key)
            kept.append(sample)
        family.samples = kept
        yield family
