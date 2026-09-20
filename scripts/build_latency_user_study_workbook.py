#!/usr/bin/env python3


from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET


OUTPUT_DIR = Path("outputs/user_study")
SELECTION_SEED = 20260715
SIMULATION_SEED = 20260720

METHODS = ["HA-native", "HEFT", "NaiveTopo", "LLM-only", "FloWeaver"]
METHOD_CODES = dict(zip(METHODS, "ABCDE"))
SCORE_COLUMNS = {
    "HA-native": "H",
    "HEFT": "I",
    "NaiveTopo": "J",
    "LLM-only": "K",
    "FloWeaver": "L",
}

SIMULATED_MEANS = {
    "R01": {"HA-native": 2.500, "HEFT": 2.625, "NaiveTopo": 3.625, "LLM-only": 4.000, "FloWeaver": 4.000},
    "R02": {"HA-native": 2.125, "HEFT": 2.250, "NaiveTopo": 3.250, "LLM-only": 4.000, "FloWeaver": 4.000},
    "R03": {"HA-native": 1.500, "HEFT": 1.750, "NaiveTopo": 2.500, "LLM-only": 3.500, "FloWeaver": 3.750},
    "R04": {"HA-native": 1.250, "HEFT": 1.625, "NaiveTopo": 2.375, "LLM-only": 3.375, "FloWeaver": 3.625},
    "R09": {"HA-native": 1.875, "HEFT": 2.125, "NaiveTopo": 2.750, "LLM-only": 3.500, "FloWeaver": 3.750},
    "R05": {"HA-native": 0.375, "HEFT": 0.875, "NaiveTopo": 1.750, "LLM-only": 2.500, "FloWeaver": 3.250},
    "R06": {"HA-native": 0.500, "HEFT": 1.000, "NaiveTopo": 1.875, "LLM-only": 2.625, "FloWeaver": 3.375},
    "R07": {"HA-native": 0.000, "HEFT": 0.250, "NaiveTopo": 1.000, "LLM-only": 1.500, "FloWeaver": 2.250},
    "R08": {"HA-native": 0.125, "HEFT": 0.500, "NaiveTopo": 1.375, "LLM-only": 2.250, "FloWeaver": 3.000},
    "R10": {"HA-native": 0.250, "HEFT": 0.625, "NaiveTopo": 1.250, "LLM-only": 2.125, "FloWeaver": 2.875},
}

ROUTINES = [
    {
        "routine_id": "R01",
        "schedule_id": "SH-G1",
        "dataset": "smart-home",
        "group": "Group1 (0, 3] s",
        "sample_id": 16,
        "name": "Turn on Home Connect Hood light on a special day",
        "protocol_mix": "cloud",
        "ble": 0,
        "local": 0,
        "cloud": 2,
        "devices": 2,
        "latencies": {
            "HA-native": 2.390,
            "HEFT": 2.341,
            "NaiveTopo": 1.729,
            "LLM-only": 1.746,
            "FloWeaver": 1.707,
        },
        "selection": "Cloud case; all five conditions pass; non-trivial latency contrast.",
    },
    {
        "routine_id": "R02",
        "schedule_id": "SH-G2",
        "dataset": "smart-home",
        "group": "Group2 (3, 6] s",
        "sample_id": 214,
        "name": "Turn on Hue and Nanoleaf lights at sunset",
        "protocol_mix": "local+local",
        "ble": 0,
        "local": 12,
        "cloud": 0,
        "devices": 12,
        "latencies": {
            "HA-native": 3.130,
            "HEFT": 3.012,
            "NaiveTopo": 2.141,
            "LLM-only": 1.127,
            "FloWeaver": 0.724,
        },
        "selection": "Local case; all five conditions pass; medium complexity.",
    },
    {
        "routine_id": "R03",
        "schedule_id": "SH-G3",
        "dataset": "smart-home",
        "group": "Group3 (6, 9] s",
        "sample_id": 248,
        "name": "Switch your ecobee to your chosen comfort profile as you arrive home",
        "protocol_mix": "cloud",
        "ble": 0,
        "local": 0,
        "cloud": 7,
        "devices": 7,
        "latencies": {
            "HA-native": 7.490,
            "HEFT": 7.100,
            "NaiveTopo": 4.732,
            "LLM-only": 3.318,
            "FloWeaver": 3.017,
        },
        "selection": "Only common-pass smart-home Group3 case.",
    },
    {
        "routine_id": "R04",
        "schedule_id": "SH-G4",
        "dataset": "smart-home",
        "group": "Group4 (9, infinity) s",
        "sample_id": 208,
        "name": "Color-loop Hue lights when Netatmo noise gets loud",
        "protocol_mix": "cloud+local",
        "ble": 0,
        "local": 6,
        "cloud": 7,
        "devices": 13,
        "latencies": {
            "HA-native": 9.870,
            "HEFT": 7.877,
            "NaiveTopo": 6.071,
            "LLM-only": 3.771,
            "FloWeaver": 3.389,
        },
        "selection": "Only common-pass smart-home Group4 case; mixed modality.",
    },
    {
        "routine_id": "R09",
        "schedule_id": "SH-G2b",
        "dataset": "smart-home",
        "group": "Group2 (3, 6] s",
        "sample_id": 295,
        "name": "Press Button widget to activate Home Connect Super Cooling",
        "protocol_mix": "cloud",
        "ble": 0,
        "local": 0,
        "cloud": 5,
        "devices": 5,
        "latencies": {
            "HA-native": 4.690,
            "HEFT": 4.482,
            "NaiveTopo": 2.995,
            "LLM-only": 2.452,
            "FloWeaver": 2.183,
        },
        "selection": "Additional common-pass smart-home Cloud case; medium complexity.",
    },
    {
        "routine_id": "R05",
        "schedule_id": "LC-G1a",
        "dataset": "long-chain",
        "group": "Group1 (0, 9] s",
        "sample_id": 122,
        "name": "Turn on Hue and Kasa lights when you arrive home [3x long-chain]",
        "protocol_mix": "local+local",
        "ble": 0,
        "local": 18,
        "cloud": 0,
        "devices": 18,
        "latencies": {
            "HA-native": 6.300,
            "HEFT": 6.086,
            "NaiveTopo": 4.575,
            "LLM-only": 4.514,
            "FloWeaver": 1.458,
        },
        "selection": "Common-pass long-chain Group1 case; arrival routine.",
    },
    {
        "routine_id": "R06",
        "schedule_id": "LC-G1b",
        "dataset": "long-chain",
        "group": "Group1 (0, 9] s",
        "sample_id": 189,
        "name": "Turn on Hue and Nanoleaf lights at sunset [3x long-chain]",
        "protocol_mix": "local+local",
        "ble": 0,
        "local": 18,
        "cloud": 0,
        "devices": 18,
        "latencies": {
            "HA-native": 5.430,
            "HEFT": 5.246,
            "NaiveTopo": 3.774,
            "LLM-only": 3.890,
            "FloWeaver": 1.257,
        },
        "selection": "Common-pass long-chain Group1 case; scheduled trigger.",
    },
    {
        "routine_id": "R07",
        "schedule_id": "LC-G2a",
        "dataset": "long-chain",
        "group": "Group2 (9, 18] s",
        "sample_id": 233,
        "name": "Automatically turn your lights on at sunset [3x long-chain]",
        "protocol_mix": "local",
        "ble": 0,
        "local": 24,
        "cloud": 0,
        "devices": 24,
        "latencies": {
            "HA-native": 13.860,
            "HEFT": 13.310,
            "NaiveTopo": 11.009,
            "LLM-only": 9.453,
            "FloWeaver": 3.617,
        },
        "selection": "Common-pass long-chain Group2 case; highest eligible latency.",
    },
    {
        "routine_id": "R08",
        "schedule_id": "LC-G2b",
        "dataset": "long-chain",
        "group": "Group2 (9, 18] s",
        "sample_id": 255,
        "name": "Turn on Kasa plug on at sunset [3x long-chain]",
        "protocol_mix": "local",
        "ble": 0,
        "local": 21,
        "cloud": 0,
        "devices": 21,
        "latencies": {
            "HA-native": 9.240,
            "HEFT": 8.873,
            "NaiveTopo": 7.633,
            "LLM-only": 6.302,
            "FloWeaver": 2.412,
        },
        "selection": "Common-pass long-chain Group2 case; lower group boundary.",
    },
    {
        "routine_id": "R10",
        "schedule_id": "LC-G2c",
        "dataset": "long-chain",
        "group": "Group2 (9, 18] s",
        "sample_id": 234,
        "name": "Toggle Kasa lights with Button widget [3x long-chain]",
        "protocol_mix": "local",
        "ble": 0,
        "local": 24,
        "cloud": 0,
        "devices": 24,
        "latencies": {
            "HA-native": 11.400,
            "HEFT": 10.852,
            "NaiveTopo": 9.659,
            "LLM-only": 7.396,
            "FloWeaver": 2.975,
        },
        "selection": "Additional common-pass long-chain Group2 case; 24 local devices.",
    },
]

WILLIAMS = {
    "W01": ["HA-native", "HEFT", "FloWeaver", "NaiveTopo", "LLM-only"],
    "W02": ["HEFT", "NaiveTopo", "HA-native", "LLM-only", "FloWeaver"],
    "W03": ["NaiveTopo", "LLM-only", "HEFT", "FloWeaver", "HA-native"],
    "W04": ["LLM-only", "FloWeaver", "NaiveTopo", "HA-native", "HEFT"],
    "W05": ["FloWeaver", "HA-native", "LLM-only", "HEFT", "NaiveTopo"],
    "W06": ["LLM-only", "NaiveTopo", "FloWeaver", "HEFT", "HA-native"],
    "W07": ["FloWeaver", "LLM-only", "HA-native", "NaiveTopo", "HEFT"],
    "W08": ["HA-native", "FloWeaver", "HEFT", "LLM-only", "NaiveTopo"],
    "W09": ["HEFT", "HA-native", "NaiveTopo", "FloWeaver", "LLM-only"],
    "W10": ["NaiveTopo", "HEFT", "LLM-only", "HA-native", "FloWeaver"],
}


SEQUENCE_ASSIGNMENT = {
    "SH-G1": ["W02", "W06", "W01", "W09", "W04", "W05", "W05", "W01", "W07", "W07", "W03", "W04", "W10", "W08", "W02", "W03"],
    "SH-G2": ["W10", "W03", "W03", "W04", "W02", "W04", "W01", "W07", "W09", "W06", "W02", "W01", "W05", "W06", "W08", "W05"],
    "SH-G3": ["W08", "W04", "W06", "W07", "W07", "W02", "W09", "W09", "W03", "W10", "W10", "W08", "W01", "W06", "W05", "W02"],
    "SH-G4": ["W04", "W09", "W02", "W01", "W08", "W06", "W04", "W05", "W08", "W10", "W06", "W03", "W07", "W10", "W09", "W07"],
    "SH-G2b": ["W07", "W03", "W04", "W01", "W10", "W05", "W02", "W02", "W05", "W09", "W07", "W04", "W06", "W03", "W01", "W08"],
    "LC-G1a": ["W05", "W02", "W04", "W06", "W10", "W03", "W08", "W03", "W01", "W07", "W05", "W02", "W04", "W09", "W10", "W01"],
    "LC-G1b": ["W01", "W07", "W05", "W08", "W03", "W01", "W06", "W02", "W04", "W09", "W07", "W10", "W08", "W09", "W06", "W10"],
    "LC-G2a": ["W03", "W01", "W09", "W02", "W05", "W10", "W03", "W04", "W06", "W08", "W01", "W05", "W02", "W08", "W07", "W04"],
    "LC-G2b": ["W07", "W05", "W08", "W10", "W01", "W09", "W02", "W08", "W10", "W06", "W04", "W09", "W03", "W07", "W03", "W06"],
    "LC-G2c": ["W06", "W10", "W10", "W03", "W09", "W04", "W07", "W06", "W02", "W09", "W08", "W07", "W08", "W05", "W01", "W03"],
}

ROUTINE_ORDER = {
    sequence_id: [METHODS.index(method) for method in order]
    for sequence_id, order in WILLIAMS.items()
}
ROUTINE_ORDER_ASSIGNMENT = {
    "smart-home": ["W01", "W02", "W03", "W04", "W05", "W06", "W07", "W08", "W09", "W10", "W01", "W02", "W03", "W04", "W05", "W07"],
    "long-chain": ["W06", "W07", "W08", "W09", "W10", "W01", "W02", "W03", "W04", "W05", "W03", "W06", "W07", "W08", "W09", "W10"],
}

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "number": "urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0",
    "of": "urn:oasis:names:tc:opendocument:xmlns:of:1.2",
    "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
    "dc": "http://purl.org/dc/elements/1.1/",
}
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)


def q(ns: str, tag: str) -> str:
    return f"{{{NS[ns]}}}{tag}"


def add_style(parent: ET.Element, name: str, *, background: str | None = None,
              color: str | None = None, bold: bool = False, size: str = "10pt",
              align: str | None = None, wrap: bool = True, border: bool = True) -> None:
    style = ET.SubElement(parent, q("style", "style"), {
        q("style", "name"): name,
        q("style", "family"): "table-cell",
    })
    props = {q("style", "vertical-align"): "middle"}
    if background:
        props[q("fo", "background-color")] = background
    if border:
        props[q("fo", "border")] = "0.5pt solid #C7D0D9"
    if wrap:
        props[q("fo", "wrap-option")] = "wrap"
    ET.SubElement(style, q("style", "table-cell-properties"), props)
    if align:
        ET.SubElement(style, q("style", "paragraph-properties"), {
            q("fo", "text-align"): align,
        })
    text_props = {q("fo", "font-size"): size}
    if color:
        text_props[q("fo", "color")] = color
    if bold:
        text_props[q("fo", "font-weight")] = "bold"
    ET.SubElement(style, q("style", "text-properties"), text_props)


def make_document() -> tuple[ET.Element, ET.Element, dict[float, str]]:
    root = ET.Element(q("office", "document"), {
        "xmlns:of": NS["of"],
        q("office", "version"): "1.3",
        q("office", "mimetype"): "application/vnd.oasis.opendocument.spreadsheet",
    })
    meta = ET.SubElement(root, q("office", "meta"))
    title = ET.SubElement(meta, q("dc", "title"))
    title.text = "FloWeaver Latency Perception User Study"
    creator = ET.SubElement(meta, q("meta", "initial-creator"))
    creator.text = "FloWeaver experiment workbook generator"

    styles = ET.SubElement(root, q("office", "styles"))
    default = ET.SubElement(styles, q("style", "default-style"), {
        q("style", "family"): "table-cell",
    })
    ET.SubElement(default, q("style", "table-cell-properties"), {
        q("style", "vertical-align"): "middle",
        q("fo", "wrap-option"): "wrap",
    })
    ET.SubElement(default, q("style", "text-properties"), {
        q("fo", "font-family"): "Liberation Sans",
        q("fo", "font-size"): "10pt",
    })
    add_style(styles, "Title", background="#24495F", color="#FFFFFF", bold=True, size="15pt", align="left")
    add_style(styles, "Section", background="#DCEAF1", color="#17394D", bold=True, size="11pt", align="left")
    add_style(styles, "Header", background="#4F7488", color="#FFFFFF", bold=True, align="center")
    add_style(styles, "SubHeader", background="#E8F0F4", color="#17394D", bold=True, align="left")
    add_style(styles, "Text", background="#FFFFFF", color="#1F2933", align="left")
    add_style(styles, "Center", background="#FFFFFF", color="#1F2933", align="center")
    add_style(styles, "Number", background="#FFFFFF", color="#1F2933", align="right")
    add_style(styles, "Input", background="#FFF3C4", color="#1F2933", align="center")
    add_style(styles, "InputText", background="#FFF3C4", color="#1F2933", align="left")
    add_style(styles, "Formula", background="#E8F4EA", color="#1F2933", align="right")
    add_style(styles, "Note", background="#F4F6F8", color="#4D5965", size="9pt", align="left")
    add_style(styles, "Warning", background="#FCE8E6", color="#8A2D24", bold=True, align="left")
    percent_format = ET.SubElement(styles, q("number", "percentage-style"), {
        q("style", "name"): "Percent1",
    })
    ET.SubElement(percent_format, q("number", "number"), {
        q("number", "decimal-places"): "1",
        q("number", "min-integer-digits"): "1",
    })
    ET.SubElement(percent_format, q("number", "text")).text = "%"
    percent_style = ET.SubElement(styles, q("style", "style"), {
        q("style", "name"): "Percent",
        q("style", "family"): "table-cell",
        q("style", "data-style-name"): "Percent1",
    })
    ET.SubElement(percent_style, q("style", "table-cell-properties"), {
        q("style", "vertical-align"): "middle",
        q("fo", "background-color"): "#E8F4EA",
        q("fo", "border"): "0.5pt solid #C7D0D9",
        q("fo", "wrap-option"): "wrap",
    })
    ET.SubElement(percent_style, q("style", "paragraph-properties"), {
        q("fo", "text-align"): "right",
    })
    ET.SubElement(percent_style, q("style", "text-properties"), {
        q("fo", "font-size"): "10pt",
        q("fo", "color"): "#1F2933",
    })

    auto = ET.SubElement(root, q("office", "automatic-styles"))
    column_styles: dict[float, str] = {}
    for i, width in enumerate([1.6, 2.0, 2.4, 2.8, 3.2, 3.8, 4.5, 5.5, 7.5, 10.5], start=1):
        name = f"co{i}"
        column_styles[width] = name
        style = ET.SubElement(auto, q("style", "style"), {
            q("style", "name"): name,
            q("style", "family"): "table-column",
        })
        ET.SubElement(style, q("style", "table-column-properties"), {
            q("style", "column-width"): f"{width}cm",
        })

    body = ET.SubElement(root, q("office", "body"))
    spreadsheet = ET.SubElement(body, q("office", "spreadsheet"))
    validations = ET.SubElement(spreadsheet, q("table", "content-validations"))
    score_validation = ET.SubElement(validations, q("table", "content-validation"), {
        q("table", "name"): "Score0to4",
        q("table", "condition"): "cell-content-is-whole-number() and cell-content()>=0 and cell-content()<=4",
        q("table", "allow-empty-cell"): "true",
        q("table", "base-cell-address"): "$Scores.$H$3",
    })
    help_message = ET.SubElement(score_validation, q("table", "help-message"), {
        q("table", "display"): "true",
        q("table", "title"): "Latency acceptance score",
    })
    ET.SubElement(help_message, q("text", "p")).text = "Enter an integer from 0 to 4."
    error_message = ET.SubElement(score_validation, q("table", "error-message"), {
        q("table", "display"): "true",
        q("table", "message-type"): "stop",
        q("table", "title"): "Invalid score",
    })
    ET.SubElement(error_message, q("text", "p")).text = "Only integer scores 0, 1, 2, 3, or 4 are valid."
    return root, spreadsheet, column_styles


def add_sheet(spreadsheet: ET.Element, name: str, widths: list[float],
              column_styles: dict[float, str]) -> ET.Element:
    table = ET.SubElement(spreadsheet, q("table", "table"), {q("table", "name"): name})
    for width in widths:
        ET.SubElement(table, q("table", "table-column"), {
            q("table", "style-name"): column_styles[width],
        })
    return table


def add_row(table: ET.Element, values: list[object], styles: list[str] | str = "Text",
            formulas: dict[int, str] | None = None,
            validations: set[int] | None = None) -> ET.Element:
    row = ET.SubElement(table, q("table", "table-row"))
    if isinstance(styles, str):
        styles = [styles] * len(values)
    formulas = formulas or {}
    validations = validations or set()
    for index, value in enumerate(values):
        attrs = {q("table", "style-name"): styles[index]}
        if index in validations:
            attrs[q("table", "content-validation-name")] = "Score0to4"
        if index in formulas:
            attrs[q("table", "formula")] = formulas[index]
            attrs[q("office", "value-type")] = "string"
            cell = ET.SubElement(row, q("table", "table-cell"), attrs)
            ET.SubElement(cell, q("text", "p"))
        elif value is None or value == "":
            cell = ET.SubElement(row, q("table", "table-cell"), attrs)
            ET.SubElement(cell, q("text", "p"))
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            attrs[q("office", "value-type")] = "float"
            attrs[q("office", "value")] = str(value)
            cell = ET.SubElement(row, q("table", "table-cell"), attrs)
            ET.SubElement(cell, q("text", "p")).text = str(value)
        else:
            attrs[q("office", "value-type")] = "string"
            cell = ET.SubElement(row, q("table", "table-cell"), attrs)
            ET.SubElement(cell, q("text", "p")).text = str(value)
    return row


def add_merged_title(table: ET.Element, text: str, columns: int, style: str = "Title") -> None:
    row = ET.SubElement(table, q("table", "table-row"))
    cell = ET.SubElement(row, q("table", "table-cell"), {
        q("table", "style-name"): style,
        q("table", "number-columns-spanned"): str(columns),
        q("office", "value-type"): "string",
    })
    ET.SubElement(cell, q("text", "p")).text = text
    for _ in range(columns - 1):
        ET.SubElement(row, q("table", "covered-table-cell"))


def blank_row(table: ET.Element, columns: int) -> None:
    add_row(table, [""] * columns, "Text")


def make_schedule() -> list[dict[str, object]]:
    routine_by_id = {routine["routine_id"]: routine for routine in ROUTINES}
    smart = ["R01", "R02", "R03", "R04", "R09"]
    long = ["R05", "R06", "R07", "R08", "R10"]
    schedule: list[dict[str, object]] = []
    for participant in range(1, 17):
        pid = f"P{participant:02d}"
        smart_order_id = ROUTINE_ORDER_ASSIGNMENT["smart-home"][participant - 1]
        long_order_id = ROUTINE_ORDER_ASSIGNMENT["long-chain"][participant - 1]
        smart_order = [(smart[index], smart_order_id) for index in ROUTINE_ORDER[smart_order_id]]
        long_order = [(long[index], long_order_id) for index in ROUTINE_ORDER[long_order_id]]
        if participant <= 8:
            visit_order = smart_order + long_order
            block_order = "smart-home -> long-chain"
        else:
            visit_order = long_order + smart_order
            block_order = "long-chain -> smart-home"
        for visit, (routine_id, routine_order_id) in enumerate(visit_order, start=1):
            routine = routine_by_id[routine_id]
            sequence_id = SEQUENCE_ASSIGNMENT[routine["schedule_id"]][participant - 1]
            order = WILLIAMS[sequence_id]
            schedule.append({
                "participant_id": pid,
                "block_order": block_order,
                "routine_order_id": routine_order_id,
                "visit": visit,
                "routine_id": routine_id,
                "dataset": routine["dataset"],
                "group": routine["group"],
                "routine_name": routine["name"],
                "sequence_id": sequence_id,
                "method_order": order,
            })
    return schedule


def simulate_scores(schedule: list[dict[str, object]]) -> dict[tuple[str, str, str], int]:

    rng = random.Random(SIMULATION_SEED)
    tolerance = [-0.55, -0.42, -0.34, -0.25, -0.18, -0.10, -0.04, 0.0,
                 0.04, 0.10, 0.18, 0.25, 0.34, 0.42, 0.50, 0.60]
    rng.shuffle(tolerance)
    lookup = {(str(row["routine_id"]), str(row["participant_id"])): row for row in schedule}
    scores: dict[tuple[str, str, str], int] = {}

    for routine in ROUTINES:
        routine_id = routine["routine_id"]
        for method in METHODS:
            target = SIMULATED_MEANS[routine_id][method]
            raw = []
            for participant in range(1, 17):
                pid = f"P{participant:02d}"
                item = lookup[(routine_id, pid)]
                position = list(item["method_order"]).index(method) + 1
                position_effect = {1: 0.06, 2: 0.03, 3: 0.0, 4: -0.03, 5: -0.06}[position]
                fatigue_effect = -0.025 * (int(item["visit"]) - 4.5)
                value = target + tolerance[participant - 1] + position_effect + fatigue_effect + rng.uniform(-0.32, 0.32)
                raw.append(value)

            values = [max(0, min(4, round(value))) for value in raw]
            target_sum = round(target * 16)
            while sum(values) < target_sum:
                candidates = [i for i, value in enumerate(values) if value < 4]
                index = max(candidates, key=lambda i: raw[i] - values[i])
                values[index] += 1
            while sum(values) > target_sum:
                candidates = [i for i, value in enumerate(values) if value > 0]
                index = min(candidates, key=lambda i: raw[i] - values[i])
                values[index] -= 1

            assert sum(values) == target_sum
            for participant, value in enumerate(values, start=1):
                scores[(routine_id, f"P{participant:02d}", method)] = value

    for routine in ROUTINES:
        means = {
            method: sum(scores[(routine["routine_id"], f"P{participant:02d}", method)]
                        for participant in range(1, 17)) / 16
            for method in METHODS
        }
        assert means["HA-native"] <= means["HEFT"] <= means["NaiveTopo"]
        assert means["NaiveTopo"] <= means["LLM-only"] <= means["FloWeaver"]
    return scores


def validate_schedule(schedule: list[dict[str, object]]) -> dict[str, object]:
    assert len(schedule) == 16 * len(ROUTINES)
    routine_pos: dict[str, Counter] = defaultdict(Counter)
    routine_adj: dict[str, Counter] = defaultdict(Counter)
    global_pos = Counter()
    participant_pos: dict[str, Counter] = defaultdict(Counter)
    for item in schedule:
        routine_id = str(item["routine_id"])
        participant_id = str(item["participant_id"])
        order = list(item["method_order"])
        for position, method in enumerate(order, start=1):
            routine_pos[routine_id][(method, position)] += 1
            global_pos[(method, position)] += 1
            participant_pos[participant_id][(method, position)] += 1
        for left, right in zip(order, order[1:]):
            routine_adj[routine_id][(left, right)] += 1

    for counts in routine_pos.values():
        assert min(counts.values()) >= 3 and max(counts.values()) <= 4
    assert min(global_pos.values()) >= 30 and max(global_pos.values()) <= 34
    for counts in participant_pos.values():
        assert min(counts.values()) >= 1 and max(counts.values()) <= 3

    return {
        "routine_position_range": [
            min(min(counts.values()) for counts in routine_pos.values()),
            max(max(counts.values()) for counts in routine_pos.values()),
        ],
        "routine_directed_adjacency_range": [
            min(min(counts.values()) for counts in routine_adj.values()),
            max(max(counts.values()) for counts in routine_adj.values()),
        ],
        "global_position_range": [min(global_pos.values()), max(global_pos.values())],
        "participant_method_position_range": [
            min(min(counts.values()) for counts in participant_pos.values()),
            max(max(counts.values()) for counts in participant_pos.values()),
        ],
        "routine_position_counts": routine_pos,
        "global_position_counts": global_pos,
    }


def build_readme(spreadsheet: ET.Element, columns: dict[float, str], simulated: bool) -> None:
    table = add_sheet(spreadsheet, "README", [3.2, 10.5], columns)
    add_merged_title(table, "FloWeaver Latency Perception User Study", 2)
    rows = [
        ("Data status", f"SIMULATED scores for study planning; seed={SIMULATION_SEED}. Do not report as observed user-study data." if simulated else "Blank template for observed user-study data."),
        ("Primary construct", "Perceived execution latency and acceptance, not functional correctness or interface preference."),
        ("Design", "Within-subject: 16 participants x 10 routines x 5 conditions = 800 scored observations."),
        ("Conditions", "HA-native, HEFT, NaiveTopo, LLM-only, and FloWeaver."),
        ("Condition order", "Balanced Williams design. Each routine uses all 10 five-condition Williams sequences once, plus six jointly balanced repeats."),
        ("Routine order", "Ten-sequence Williams order within each five-routine dataset block; 8 participants start with smart-home and 8 with long-chain."),
        ("Blinding", "Use opaque participant-facing condition labels. Method identities in this workbook are for the researcher only."),
        ("Score 0", "Unacceptable delay; the routine feels unusable."),
        ("Score 1", "Strongly disruptive delay."),
        ("Score 2", "Acceptable but clearly noticeable delay."),
        ("Score 3", "Responsive; only minor waiting is noticed."),
        ("Score 4", "Near-instant response."),
        ("Data entry", "Enter integer scores in yellow cells on Scores. Record per-trial measured latency and validity in Raw Long if available."),
        ("Selection rule", "Require complete, validator-passing outputs for all five conditions; then stratify by dataset, HA-native latency group, and modality/complexity."),
        ("Selection seed", str(SELECTION_SEED)),
        ("Coverage boundary", "The common-pass pool has no BLE routine and no long-chain Group3/Group4 routine. The study therefore estimates latency perception only over the listed executable comparison set."),
        ("Invalid trial", "Do not impute. Mark Trial Valid=0, record the reason, reset, and repeat at the end of the participant session."),
    ]
    for label, value in rows:
        style = ["SubHeader", "Warning" if label == "Coverage boundary" or (simulated and label == "Data status") else "Text"]
        add_row(table, [label, value], style)


def build_manifest(spreadsheet: ET.Element, columns: dict[float, str]) -> None:
    widths = [1.6, 2.0, 2.4, 2.0, 2.8, 7.5, 2.8, 1.6, 1.6, 1.6, 1.6, 2.0, 2.0, 2.0, 2.0, 2.0, 7.5]
    table = add_sheet(spreadsheet, "Routine Manifest", widths, columns)
    add_merged_title(table, "Selected Routine Manifest", len(widths))
    headers = [
        "Routine ID", "Dataset", "Latency Group", "Source Sample ID", "Protocol Mix", "Routine",
        "BLE", "Local", "Cloud", "Total Devices", "HA-native (s)", "HEFT (s)",
        "NaiveTopo (s)", "LLM-only (s)", "FloWeaver (s)", "All Five Pass", "Selection Note",
    ]
    add_row(table, headers, "Header")
    for routine in ROUTINES:
        values = [
            routine["routine_id"], routine["dataset"], routine["group"], routine["sample_id"],
            routine["protocol_mix"], routine["name"], routine["ble"], routine["local"], routine["cloud"],
            routine["devices"], routine["latencies"]["HA-native"], routine["latencies"]["HEFT"],
            routine["latencies"]["NaiveTopo"], routine["latencies"]["LLM-only"],
            routine["latencies"]["FloWeaver"], 1, routine["selection"],
        ]
        styles = ["Center", "Center", "Center", "Center", "Center", "Text"] + ["Number"] * 10 + ["Text"]
        add_row(table, values, styles)


def build_williams(spreadsheet: ET.Element, columns: dict[float, str]) -> None:
    table = add_sheet(spreadsheet, "Williams Sequences", [2.0, 2.8, 2.8, 2.8, 2.8, 2.8, 7.5], columns)
    add_merged_title(table, "Five-Condition Balanced Williams Sequences", 7)
    add_row(table, ["Sequence", "Position 1", "Position 2", "Position 3", "Position 4", "Position 5", "Method Codes"], "Header")
    for sequence_id, order in WILLIAMS.items():
        add_row(table, [sequence_id, *order, "A=HA-native; B=HEFT; C=NaiveTopo; D=LLM-only; E=FloWeaver"],
                ["Center"] * 6 + ["Text"])
    blank_row(table, 7)
    add_row(table, ["Routine-order sequence", "Position 1", "Position 2", "Position 3", "Position 4", "Position 5", ""], "Header")
    for sequence_id, indexes in ROUTINE_ORDER.items():
        add_row(table, [sequence_id, *[index + 1 for index in indexes], ""], ["Center"] * 7)
    add_row(table, ["Note", "For five conditions, perfect balance with N=16 is impossible because 16 is not divisible by 10. The selected repeats minimize position and directed-adjacency imbalance.", "", "", "", "", ""],
            ["SubHeader", "Note", "Note", "Note", "Note", "Note", "Note"])


def build_participant_schedule(spreadsheet: ET.Element, columns: dict[float, str],
                               schedule: list[dict[str, object]]) -> None:
    widths = [2.0, 3.8, 2.0, 1.6, 1.6, 2.0, 2.4, 2.4, 7.5, 2.0, 2.8, 2.8, 2.8, 2.8, 2.8]
    table = add_sheet(spreadsheet, "Participant Schedule", widths, columns)
    add_merged_title(table, "Participant and Condition Presentation Schedule", len(widths))
    headers = [
        "Participant", "Dataset Block Order", "Routine Order", "Visit", "Routine ID", "Dataset",
        "Group", "Sequence", "Routine", "Position 1", "Position 2", "Position 3", "Position 4", "Position 5", "Researcher Check",
    ]
    add_row(table, headers, "Header")
    for item in sorted(schedule, key=lambda row: (row["participant_id"], row["visit"])):
        values = [
            item["participant_id"], item["block_order"], item["routine_order_id"], item["visit"],
            item["routine_id"], item["dataset"], item["group"], item["sequence_id"], item["routine_name"],
            *item["method_order"], "",
        ]
        add_row(table, values, ["Center", "Center", "Center", "Center", "Center", "Center", "Center", "Center", "Text"] + ["Center"] * 5 + ["Input"])


def build_scores(spreadsheet: ET.Element, columns: dict[float, str],
                 schedule: list[dict[str, object]],
                 simulated_scores: dict[tuple[str, str, str], int] | None = None) -> dict[tuple[str, str], int]:
    widths = [2.0, 2.0, 2.8, 2.8, 2.8, 2.8, 2.8, 2.4, 2.4, 2.4, 2.4, 2.4, 2.0, 2.0, 7.5]
    table = add_sheet(spreadsheet, "Scores", widths, columns)
    schedule_lookup = {(row["routine_id"], row["participant_id"]): row for row in schedule}
    score_rows: dict[tuple[str, str], int] = {}
    current_row = 0
    for routine_index, routine in enumerate(ROUTINES):
        title = (f"{routine['routine_id']} | {routine['dataset']} | {routine['group']} | "
                 f"{routine['name']}")
        add_merged_title(table, title, len(widths), "Section")
        current_row += 1
        headers = [
            "Participant", "Sequence", "Position 1", "Position 2", "Position 3", "Position 4", "Position 5",
            "HA-native Score", "HEFT Score", "NaiveTopo Score", "LLM-only Score", "FloWeaver Score",
            "Trial Valid (1/0)", "Retry Count", "Comment",
        ]
        add_row(table, headers, "Header")
        current_row += 1
        for participant in range(1, 17):
            pid = f"P{participant:02d}"
            item = schedule_lookup[(routine["routine_id"], pid)]
            method_scores = [
                simulated_scores[(routine["routine_id"], pid, method)] if simulated_scores else ""
                for method in METHODS
            ]
            values = [pid, item["sequence_id"], *item["method_order"], *method_scores, 1, 0, ""]
            styles = ["Center"] * 7 + ["Input"] * 7 + ["InputText"]
            add_row(table, values, styles, validations=set(range(7, 12)))
            current_row += 1
            score_rows[(routine["routine_id"], pid)] = current_row
        if routine_index != len(ROUTINES) - 1:
            blank_row(table, len(widths))
            current_row += 1
    return score_rows


def build_raw_long(spreadsheet: ET.Element, columns: dict[float, str],
                   schedule: list[dict[str, object]], score_rows: dict[tuple[str, str], int]) -> None:
    widths = [2.0, 1.6, 2.0, 2.4, 2.4, 7.5, 2.0, 1.6, 2.8, 2.4, 2.4, 2.0, 2.0, 7.5]
    table = add_sheet(spreadsheet, "Raw Long", widths, columns)
    add_merged_title(table, "Long-Format Trial Records", len(widths))
    headers = [
        "Participant", "Visit", "Routine ID", "Dataset", "Group", "Routine", "Sequence", "Presentation Position",
        "Method", "Score", "Measured Latency (s)", "Trial Valid (1/0)", "Retry Count", "Comment",
    ]
    add_row(table, headers, "Header")
    for item in sorted(schedule, key=lambda row: (row["participant_id"], row["visit"])):
        score_row = score_rows[(str(item["routine_id"]), str(item["participant_id"]))]
        for position, method in enumerate(item["method_order"], start=1):
            score_col = SCORE_COLUMNS[method]
            formula = f"of:=IF(ISBLANK([Scores.{score_col}{score_row}]);\"\";[Scores.{score_col}{score_row}])"
            valid_formula = f"of:=[Scores.M{score_row}]"
            retry_formula = f"of:=[Scores.N{score_row}]"
            comment_formula = f"of:=[Scores.O{score_row}]"
            values = [
                item["participant_id"], item["visit"], item["routine_id"], item["dataset"], item["group"],
                item["routine_name"], item["sequence_id"], position, method, "", "", "", "", "",
            ]
            styles = ["Center", "Center", "Center", "Center", "Center", "Text", "Center", "Center", "Center", "Formula", "Input", "Formula", "Formula", "Formula"]
            add_row(table, values, styles, formulas={9: formula, 11: valid_formula, 12: retry_formula, 13: comment_formula})


def score_range(routine_index: int, method: str) -> str:
    start = 3 + 19 * routine_index
    end = start + 15
    col = SCORE_COLUMNS[method]
    return f"[Scores.{col}{start}:Scores.{col}{end}]"


def summary_formulas(ranges: list[str]) -> dict[str, str]:
    args = ";".join(ranges)
    count = f"COUNT({args})"
    accepted = "+".join(f"COUNTIF({cell_range};\">=3\")" for cell_range in ranges)
    return {
        "count": f"of:={count}",
        "mean": f"of:=IF({count}=0;\"\";AVERAGE({args}))",
        "median": f"of:=IF({count}=0;\"\";MEDIAN({args}))",
        "min": f"of:=IF({count}=0;\"\";MIN({args}))",
        "max": f"of:=IF({count}=0;\"\";MAX({args}))",
        "accept": f"of:=IF({count}=0;\"\";({accepted})/{count})",
    }


def build_summary(spreadsheet: ET.Element, columns: dict[float, str]) -> None:
    widths = [2.0, 2.4, 2.4, 2.8, 2.0, 2.4, 2.4, 2.4, 2.4, 3.2]
    table = add_sheet(spreadsheet, "Summary", widths, columns)
    add_merged_title(table, "Latency Acceptance Score Summary", len(widths))
    headers = ["Scope", "Dataset", "Group", "Method", "N", "Mean", "Median", "Min", "Max", "Score >= 3 Rate"]
    add_row(table, headers, "Header")
    for routine_index, routine in enumerate(ROUTINES):
        for method in METHODS:
            formulas = summary_formulas([score_range(routine_index, method)])
            values = [routine["routine_id"], routine["dataset"], routine["group"], method, "", "", "", "", "", ""]
            add_row(table, values, ["Center", "Center", "Center", "Center"] + ["Formula"] * 5 + ["Percent"],
                    formulas={4: formulas["count"], 5: formulas["mean"], 6: formulas["median"],
                              7: formulas["min"], 8: formulas["max"], 9: formulas["accept"]})
    blank_row(table, len(widths))
    add_row(table, ["Dataset aggregate", "Dataset", "", "Method", "N", "Mean", "Median", "Min", "Max", "Score >= 3 Rate"], "Header")
    for dataset in ["smart-home", "long-chain", "overall"]:
        indices = [i for i, routine in enumerate(ROUTINES) if dataset == "overall" or routine["dataset"] == dataset]
        for method in METHODS:
            formulas = summary_formulas([score_range(index, method) for index in indices])
            values = ["Aggregate", dataset, "", method, "", "", "", "", "", ""]
            add_row(table, values, ["Center", "Center", "Center", "Center"] + ["Formula"] * 5 + ["Percent"],
                    formulas={4: formulas["count"], 5: formulas["mean"], 6: formulas["median"],
                              7: formulas["min"], 8: formulas["max"], 9: formulas["accept"]})
    add_row(table, ["Interpretation", "", "", "", "", "", "", "", "", "Score >= 3 denotes responsive or near-instant execution."],
            ["SubHeader"] + ["Note"] * 9)


def build_balance(spreadsheet: ET.Element, columns: dict[float, str],
                  balance: dict[str, object]) -> None:
    widths = [2.0, 2.8, 2.0, 2.0, 2.0, 2.0, 2.0, 3.8]
    table = add_sheet(spreadsheet, "Balance Check", widths, columns)
    add_merged_title(table, "Williams Design Balance Check", len(widths))
    add_row(table, ["Check", "Observed", "Required", "Status", "", "", "", "Interpretation"], "Header")
    checks = [
        ("Per-routine method-position count", f"{balance['routine_position_range'][0]}-{balance['routine_position_range'][1]}", "3-4", "PASS", "Each method appears at every position three or four times per routine."),
        ("Per-routine directed adjacency count", f"{balance['routine_directed_adjacency_range'][0]}-{balance['routine_directed_adjacency_range'][1]}", "2-4", "PASS", "Each ordered method pair is represented with limited imbalance."),
        ("Global method-position count", f"{balance['global_position_range'][0]}-{balance['global_position_range'][1]}", "30-34", "PASS", "Across ten routines, method positions are nearly equal."),
        ("Per-participant method-position count", f"{balance['participant_method_position_range'][0]}-{balance['participant_method_position_range'][1]}", "1-3", "PASS", "Each participant sees every method in every position at least once."),
        ("Dataset block first", "8 smart-home / 8 long-chain", "8 / 8", "PASS", "Balances fatigue and learning across dataset blocks."),
    ]
    for label, observed, required, status, interpretation in checks:
        add_row(table, [label, observed, required, status, "", "", "", interpretation],
                ["SubHeader", "Center", "Center", "Center", "Text", "Text", "Text", "Text"])
    blank_row(table, len(widths))
    add_row(table, ["Routine", "Method", "Position 1", "Position 2", "Position 3", "Position 4", "Position 5", "Range"], "Header")
    routine_counts = balance["routine_position_counts"]
    for routine in ROUTINES:
        counts = routine_counts[routine["routine_id"]]
        for method in METHODS:
            values = [routine["routine_id"], method] + [counts[(method, pos)] for pos in range(1, 6)]
            values.append(f"{min(values[2:7])}-{max(values[2:7])}")
            add_row(table, values, ["Center"] * len(widths))
    blank_row(table, len(widths))
    add_row(table, ["Global", "Method", "Position 1", "Position 2", "Position 3", "Position 4", "Position 5", "Range"], "Header")
    global_counts = balance["global_position_counts"]
    for method in METHODS:
        values = ["All routines", method] + [global_counts[(method, pos)] for pos in range(1, 6)]
        values.append(f"{min(values[2:7])}-{max(values[2:7])}")
        add_row(table, values, ["Center"] * len(widths))


def serializable_balance(balance: dict[str, object]) -> dict[str, object]:
    return {
        key: value for key, value in balance.items()
        if key not in {"routine_position_counts", "global_position_counts"}
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulated", action="store_true", help="populate deterministic simulated scores")
    args = parser.parse_args()
    stem = "floweaver_latency_user_study_simulated" if args.simulated else "floweaver_latency_user_study"
    fods_path = OUTPUT_DIR / f"{stem}.fods"
    manifest_path = OUTPUT_DIR / f"{stem}_manifest.json"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    schedule = make_schedule()
    balance = validate_schedule(schedule)
    simulated_scores = simulate_scores(schedule) if args.simulated else None
    root, spreadsheet, columns = make_document()
    build_readme(spreadsheet, columns, args.simulated)
    build_manifest(spreadsheet, columns)
    build_williams(spreadsheet, columns)
    build_participant_schedule(spreadsheet, columns, schedule)
    score_rows = build_scores(spreadsheet, columns, schedule, simulated_scores)
    build_raw_long(spreadsheet, columns, schedule, score_rows)
    build_summary(spreadsheet, columns)
    build_balance(spreadsheet, columns, balance)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(fods_path, encoding="utf-8", xml_declaration=True)

    manifest = {
        "study": "FloWeaver latency perception and acceptance",
        "participants": 16,
        "routines": ROUTINES,
        "conditions": METHODS,
        "scored_observations": 16 * len(ROUTINES) * len(METHODS),
        "selection_seed": SELECTION_SEED,
        "data_status": "simulated" if args.simulated else "blank-template",
        "simulation_seed": SIMULATION_SEED if args.simulated else None,
        "simulated_target_means": SIMULATED_MEANS if args.simulated else None,
        "balance": serializable_balance(balance),
        "schedule": schedule,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(fods_path)
    print(manifest_path)


if __name__ == "__main__":
    main()
