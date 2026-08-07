#!/usr/bin/env python3
"""
Generate panel_maker YAML config for a slider panel from chord definitions.

Interval sequence (each cell is 5 mm wide × 8 mm tall):
  1  b2  2  b3  3  4  b5  5  b6  6  b7  7  8  b9  9  #9  10  11  b12  12  b13  13

Alternative names: b6 = #5, 6 = bb7

Chord definition format (as Python dict or YAML file):
    "CHORD NAME": {"col": 1-4, "row": 1-9, "intervals": ["1", "3", "5", ...]}

Usage:
    python generate_slider.py                       # built-in definitions → stdout
    python generate_slider.py chords.yaml           # load definitions from file
    python generate_slider.py -o examples/slider.yaml          # write to file
    python generate_slider.py chords.yaml -o examples/slider.yaml
"""

import sys
import re
import argparse
import yaml

# ─── Interval grid ────────────────────────────────────────────────────────────

ALL_INTERVALS = [
    "1",  "b2", "2",  "b3", "3",  "4",  "b5", "5",
    "b6", "6",  "b7", "7",  "8",  "b9", "9",  "#9",
    "10", "11", "b12","12", "b13","13",
]

ALIASES = {"#5": "b6", "bb7": "6"}

CELL_W = 5      # mm
CELL_H = 8      # mm
ROW_STRIDE = 16  # mm between row tops (row height + equal gap)

# ─── Panel / column geometry ──────────────────────────────────────────────────

PANEL = {
    "name": "Big muff",
    "width": "255mm",
    "height": "168mm",
    "render_mode": "drill_mask",
}

COLUMNS = {
    1: {"x": 10,  "y": 16, "width": 60,  "height": 136, },
    2: {"x": 70,  "y": 16, "width": 60,  "height": 136, },
    3: {"x": 130, "y": 16, "width": 80,  "height": 136, },
    4: {"x": 190, "y": 16, "width": 55,  "height": 136, },
}

# ─── Built-in chord definitions ───────────────────────────────────────────────
# Edit or extend this dict, or supply an external YAML file.
# "intervals" uses the names from ALL_INTERVALS above (aliases also accepted).

DEFAULT_CHORDS = {
    "MAJOR TRIAD": {
        "col": 1, "row": 1,
        "intervals": ["1", "3", "5"],
    },
    "SEVEN CHORD - Dominant 7": {
        "col": 1, "row": 2,
        "intervals": ["1", "3", "5", "b7"],
    },
    "MAJOR SEVEN CHORD - Major 7 - maj7": {
        "col": 1, "row": 3,
        "intervals": ["1", "3", "5", "7"],
    },
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def canonical(name: str) -> str:
    return ALIASES.get(name, name)


def interval_idx(name: str) -> int:
    c = canonical(name)
    if c not in ALL_INTERVALS:
        raise ValueError(f"Unknown interval: '{name}' (canonical: '{c}')")
    return ALL_INTERVALS.index(c)


def slug(text: str) -> str:
    """Lower-case alphanumeric slug, spaces/punctuation → underscores."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


# ─── Element builders ─────────────────────────────────────────────────────────

def cell_element(group_slug: str, interval: str) -> dict:
    idx = interval_idx(interval)
    x_center = idx * CELL_W + CELL_W / 2
    cell_id = f"{group_slug}_{re.sub(r'[^a-z0-9]', '_', interval.lower())}"
    return {
        "type": "custom",
        "id": cell_id,
        "x": f"{x_center}mm",
        "y": f"{CELL_H / 2}mm",
        # distance 4.5mm from element centre puts the baseline ~2mm below the
        # cell bottom edge (within the 8mm row gap); 7pt fits inside a 5mm cell.
        "label": {
            "text": interval,
            "position": "bottom",
            "distance": "4.5mm",
            "font": {"size": "7pt", "weight": "bold"},
        },
        "mount": {"width": f"{CELL_W}mm", "height": f"{CELL_H}mm"},
        "border": {"type": "full", "thickness": "0.1mm", "color": "black"},
    }


def chord_group(name: str, row: int, intervals: list) -> dict:
    indices = [interval_idx(iv) for iv in intervals]
    # Width spans from the left edge of the first cell to the right edge of the last
    group_width = (max(indices) + 1) * CELL_W
    group_y = (row - 1) * ROW_STRIDE
    gslug = slug(name)

    return {
        "type": "group",
        "id": gslug,
        "x": "0mm",
        "y": f"{group_y}mm",
        "width": f"{group_width}mm",
        "height": f"{CELL_H}mm",
        "background": {"color": "#ffffff"},
        "border": {"type": "full", "color": "black", "thickness": "0.1mm"},
        "background": {
            "color": "#ccc"
        },
        "label": {
            "text": name,
            "position": "top-left",
            "distance": "1mm",
            "font": {"color": "black", "size": "7pt", "weight": "bold"},
        },
        "elements": [cell_element(gslug, iv) for iv in intervals],
    }


def column_group(col_num: int, col_cfg: dict, chord_entries: list) -> dict:
    # Sort by row so the YAML reads top-to-bottom
    chord_entries.sort(key=lambda t: t[1]["row"])

    elements = [
        chord_group(name, defn["row"], defn["intervals"])
        for name, defn in chord_entries
    ]

    return {
        "type": "group",
        "id": f"column_{col_num}",
        "x": f"{col_cfg['x']}mm",
        "y": f"{col_cfg['y']}mm",
        "width": f"{col_cfg['width']}mm",
        "height": f"{col_cfg['height']}mm",
        "elements": elements,
    }


# ─── Main generator ───────────────────────────────────────────────────────────

def generate(chords: dict) -> dict:
    by_col = {c: [] for c in COLUMNS}

    for name, defn in chords.items():
        col = defn["col"]
        row = defn["row"]
        if col not in COLUMNS:
            raise ValueError(f"Chord '{name}': column {col} not defined (must be 1–4)")
        if not 1 <= row <= 9:
            raise ValueError(f"Chord '{name}': row {row} out of range (1–9)")
        by_col[col].append((name, defn))

    col_groups = [
        column_group(col_num, col_cfg, by_col[col_num])
        for col_num, col_cfg in COLUMNS.items()
    ]

    return {**PANEL, "elements": col_groups}


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate panel_maker YAML from chord definitions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "input", nargs="?",
        help="YAML file with chord definitions (omit to use built-in defaults)",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output YAML file (omit to print to stdout)",
    )
    args = parser.parse_args()

    if args.input:
        with open(args.input) as f:
            chords = yaml.safe_load(f)
    else:
        chords = DEFAULT_CHORDS

    panel = generate(chords)
    output_yaml = yaml.dump(
        panel,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )

    if args.output:
        with open(args.output, "w") as f:
            f.write(output_yaml)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(output_yaml)


if __name__ == "__main__":
    main()
