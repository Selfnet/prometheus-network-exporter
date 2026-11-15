"""Read module and lane diagnostics from the same optics RPC reply."""

from importlib.resources import read_text
import math
import re

import yaml

from .xmlutil import find, findall, iter_items, localname, text

FIELDS = yaml.safe_load(read_text("prometheus_network_exporter.views.junos", "optic.yml"))[
    "PhyPortDiagView"
]["fields_diag"]


def numeric(value):
    if value is None:
        return None
    try:
        result = float(re.sub(r"\s+", "", value))
    except (ValueError, TypeError):
        return None
    return None if math.isnan(result) else result


def field_value(element, path):
    node_path, _, attribute = path.partition("/@")
    node = find(element, node_path)
    if node is None:
        return None
    if attribute:
        return next((v for k, v in node.attrib.items() if k.split("}")[-1] == attribute), None)
    return node.text


def convert_field(key, value):
    if key.startswith("flag_") or key == "tx_laser_fault_alarm":
        state = (value or "").strip().lower()
        if state not in ("on", "off"):
            return None
        # Keep the legacy metric's documented polarity: 1=OK, 0=fault.
        return state == "off" if key == "tx_laser_fault_alarm" else state
    return numeric(value)


def read_fields(element):
    result = {}
    for key, definition in FIELDS.items():
        path = next(iter(definition)) if isinstance(definition, dict) else definition
        for alternative in path.split(" | "):
            value = convert_field(key, field_value(element, alternative))
            if value is not None:
                result[key] = value
                break
    result.update(read_flags(element))
    return result


def read_flags(element):
    result = {}
    for child in element:
        if not isinstance(child.tag, str):
            continue
        tag = localname(child)
        value = (child.text or "").strip().lower()
        if tag.endswith(("-alarm", "-warn")) and value in ("on", "off"):
            result["flag_" + tag.replace("-", "_")] = value
    return result


def parse_optics(reply):
    result = {}
    for interface in iter_items(reply, ("physical-interface",)):
        name = text(interface, "name")
        diag = find(interface, "optics-diagnostics")
        if not name or diag is None:
            continue
        available = find(diag, "optic-diagnostics-not-available") is None
        values = read_fields(diag) if available else {}
        lanes = {}
        if available:
            for lane in findall(diag, "optics-diagnostics-lane-values"):
                index = text(lane, "lane-index")
                if index is None or index in lanes:
                    raise ValueError("Missing or duplicate optics lane index on " + name)
                lanes[index] = read_fields(lane)
        if not available or values or lanes:
            values["diagnostics_available"] = int(available)
        values["lanes"] = lanes
        # A single reported lane is unambiguous. Never average multiple lanes.
        # Breakout IDs must agree with the reported lane index.
        if len(lanes) == 1 and (":" not in name or name.rsplit(":", 1)[1] in lanes):
            for key, value in next(iter(lanes.values())).items():
                if key.startswith(("rx_optic_power", "tx_optic_power", "laser_bias")):
                    values[key] = value
                else:
                    values.setdefault(key, value)
        result[name] = values
    return result
