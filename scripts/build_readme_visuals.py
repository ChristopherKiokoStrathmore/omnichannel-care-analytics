#!/usr/bin/env python3
"""Draw the README story poster, social preview, and supporting charts.

Numbers and bar lengths come from care_analytics.pipeline.build_report, which
regenerates the synthetic log and the DuckDB KPIs. The script does not rewrite
committed outputs. Journey figures are synthetic data.
"""

from __future__ import annotations

import struct
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cairosvg
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

from care_analytics.pipeline import build_report
from care_analytics.report import one_decimal, share

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
FONT_DIR = Path("/tmp/care-analytics-fonts")

GREEN = "#0B3D2E"
GOLD = "#C8962E"
CREAM = "#F7F4EC"
CARD = "#FFFFFF"
MUTED = "#5C6F64"
LINE = "#E6DCC8"
TRACK = "#EFE6D6"
CREAM_INK = "#F7F4EC"

FRAUNCES_URL = (
    "https://github.com/google/fonts/raw/main/ofl/fraunces/"
    "Fraunces%5BSOFT%2CWONK%2Copsz%2Cwght%5D.ttf"
)
INTER_URL = (
    "https://github.com/google/fonts/raw/main/ofl/intertight/"
    "InterTight%5Bwght%5D.ttf"
)


def esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def pct(numerator: int, denominator: int) -> str:
    """Same rounding as care_analytics.report.share, without the fraction."""

    rendered = share(numerator, denominator)
    return rendered.split(" ", 1)[0]


def ensure_fonts() -> None:
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    fraunces_var = FONT_DIR / "Fraunces-var.ttf"
    inter_var = FONT_DIR / "InterTight-var.ttf"
    if not fraunces_var.exists():
        urllib.request.urlretrieve(FRAUNCES_URL, fraunces_var)
    if not inter_var.exists():
        urllib.request.urlretrieve(INTER_URL, inter_var)

    specs = [
        (fraunces_var, "Fraunces-Bold.ttf", {"opsz": 96, "wght": 700, "SOFT": 0, "WONK": 0}, "Fraunces", "Bold", 700),
        (fraunces_var, "Fraunces-Semi.ttf", {"opsz": 72, "wght": 600, "SOFT": 0, "WONK": 0}, "Fraunces", "SemiBold", 600),
        (inter_var, "InterTight-Regular.ttf", {"wght": 400}, "Inter Tight", "Regular", 400),
        (inter_var, "InterTight-Medium.ttf", {"wght": 500}, "Inter Tight", "Medium", 500),
        (inter_var, "InterTight-Semi.ttf", {"wght": 600}, "Inter Tight", "SemiBold", 600),
        (inter_var, "InterTight-Bold.ttf", {"wght": 700}, "Inter Tight", "Bold", 700),
    ]
    for src, filename, axes, family, subfamily, weight in specs:
        dest = FONT_DIR / filename
        if dest.exists():
            continue
        font = TTFont(src)
        inst = instantiateVariableFont(font, axes, inplace=False)
        for record in inst["name"].names:
            if record.nameID in (1, 16):
                record.string = family
            elif record.nameID in (2, 17):
                record.string = subfamily
            elif record.nameID == 4:
                record.string = f"{family} {subfamily}"
            elif record.nameID == 6:
                record.string = (family + "-" + subfamily).replace(" ", "")
        inst["OS/2"].usWeightClass = weight
        inst.save(dest)

    user_fonts = Path.home() / ".local" / "share" / "fonts"
    user_fonts.mkdir(parents=True, exist_ok=True)
    for path in FONT_DIR.glob("*.ttf"):
        if path.name.endswith("-var.ttf"):
            continue
        target = user_fonts / path.name
        if not target.exists() or target.stat().st_size != path.stat().st_size:
            target.write_bytes(path.read_bytes())
    subprocess.run(["fc-cache", "-f", str(user_fonts)], check=True, capture_output=True)


def load_metrics() -> dict:
    report, _events, _journeys = build_report(ROOT)
    synthetic = report["synthetic"]
    funnel = synthetic["funnel"]
    bitext = report["public"]["bitext"]
    groups = {row["intent_group"]: row for row in synthetic["by_intent_group"]}
    order = ["self_service_candidate", "assisted", "complaint"]
    labels = {
        "self_service_candidate": "Self-service",
        "assisted": "Assisted",
        "complaint": "Complaint",
    }
    group_rows = []
    for key in order:
        row = groups[key]
        group_rows.append(
            {
                "key": key,
                "label": labels[key],
                "rate": row["digital_to_call"] / row["digital_first"],
                "pct": pct(row["digital_to_call"], row["digital_first"]),
                "fraction": f"{row['digital_to_call']}/{row['digital_first']}",
            }
        )
    channel_order = ["ussd", "app", "web", "social", "call"]
    ttfr = {row["channel"]: row for row in synthetic["ttfr_by_first_channel"]}
    resolution = {row["channel"]: row for row in synthetic["resolution_by_channel"]}
    ttfr_rows = []
    resolution_rows = []
    for channel in channel_order:
        timing = ttfr[channel]
        resolved = resolution[channel]
        ttfr_rows.append(
            {
                "channel": channel,
                "median": float(timing["median_minutes"]),
                "median_label": one_decimal(timing["median_minutes"]),
                "p90_label": one_decimal(timing["p90_minutes"]),
                "n": int(timing["journeys"]),
            }
        )
        resolution_rows.append(
            {
                "channel": channel,
                "rate": resolved["resolved_contacts"] / resolved["contacts"],
                "pct": pct(resolved["resolved_contacts"], resolved["contacts"]),
                "fraction": f"{resolved['resolved_contacts']}/{resolved['contacts']}",
            }
        )
    return {
        "seed": synthetic["seed"],
        "journeys": funnel["journeys"],
        "events": funnel["events"],
        "digital_to_call_pct": pct(funnel["digital_to_call"], funnel["digital_first"]),
        "digital_to_call_fraction": f"{funnel['digital_to_call']}/{funnel['digital_first']}",
        "resolved_pct": pct(funnel["resolved"], funnel["journeys"]),
        "resolved_fraction": f"{funnel['resolved']}/{funnel['journeys']}",
        "groups": group_rows,
        "ttfr": ttfr_rows,
        "resolution": resolution_rows,
        "n_intents": bitext["n_intents"],
        "n_categories": bitext["n_categories"],
    }


def svg_document(width: int, height: int, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        f'<rect width="{width}" height="{height}" fill="{CREAM}"/>'
        f"{body}</svg>"
    )


def text(
    x: float,
    y: float,
    content: str,
    size: float,
    family: str = "Inter Tight",
    weight: int = 500,
    fill: str = GREEN,
    anchor: str = "start",
    spacing: float | None = None,
) -> str:
    extra = f' letter-spacing="{spacing}"' if spacing else ""
    return (
        f'<text x="{x}" y="{y}" fill="{fill}" font-family="{family}" '
        f'font-weight="{weight}" font-size="{size}" text-anchor="{anchor}"{extra}>'
        f"{esc(content)}</text>"
    )


def pill(x: float, y: float, label: str, width: float = 168, height: float = 32) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="16" fill="{GREEN}"/>'
        + text(x + width / 2, y + 22, label, 14, weight=600, fill=GOLD, anchor="middle", spacing=0.4)
    )


def arrow(x1: float, y: float, x2: float) -> str:
    head = 14
    return (
        f'<line x1="{x1}" y1="{y}" x2="{x2 - head}" y2="{y}" stroke="{GOLD}" '
        f'stroke-width="3" stroke-linecap="round"/>'
        f'<polygon points="{x2},{y} {x2 - head},{y - 7} {x2 - head},{y + 7}" fill="{GOLD}"/>'
    )


def down_arrow(x: float, y1: float, y2: float) -> str:
    head = 9
    return (
        f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2 - head}" stroke="{GOLD}" '
        f'stroke-width="2.4" stroke-linecap="round"/>'
        f'<polygon points="{x},{y2} {x - 6},{y2 - head} {x + 6},{y2 - head}" fill="{GOLD}"/>'
    )


ICON_GLYPHS = {
    "ussd": """
        <rect x="20" y="8" width="24" height="48" rx="5" fill="none" stroke="#F7F4EC" stroke-width="2.2"/>
        <line x1="26" y1="18" x2="38" y2="18" stroke="#C8962E" stroke-width="2.2" stroke-linecap="round"/>
        <line x1="26" y1="25" x2="38" y2="25" stroke="#F7F4EC" stroke-width="2.2" stroke-linecap="round"/>
        <line x1="26" y1="32" x2="34" y2="32" stroke="#F7F4EC" stroke-width="2.2" stroke-linecap="round"/>
        <circle cx="32" cy="46" r="2.3" fill="#C8962E"/>
    """,
    "app": """
        <rect x="20" y="8" width="24" height="48" rx="5" fill="none" stroke="#F7F4EC" stroke-width="2.2"/>
        <rect x="24" y="16" width="7" height="7" rx="1.6" fill="#C8962E"/>
        <rect x="33" y="16" width="7" height="7" rx="1.6" fill="#F7F4EC"/>
        <rect x="24" y="25" width="7" height="7" rx="1.6" fill="#F7F4EC"/>
        <rect x="33" y="25" width="7" height="7" rx="1.6" fill="#C8962E"/>
        <circle cx="32" cy="46" r="2.3" fill="#F7F4EC"/>
    """,
    "web": """
        <rect x="8" y="14" width="48" height="34" rx="4" fill="none" stroke="#F7F4EC" stroke-width="2.2"/>
        <line x1="8" y1="23" x2="56" y2="23" stroke="#F7F4EC" stroke-width="2"/>
        <circle cx="15" cy="18.5" r="1.7" fill="#C8962E"/>
        <circle cx="21" cy="18.5" r="1.7" fill="#F7F4EC"/>
        <circle cx="27" cy="18.5" r="1.7" fill="#F7F4EC"/>
        <circle cx="32" cy="36" r="6.5" fill="none" stroke="#C8962E" stroke-width="2"/>
        <path d="M32 29.5 v13 M25.5 36 h13" stroke="#C8962E" stroke-width="1.5" stroke-linecap="round"/>
    """,
    "social": """
        <rect x="6" y="14" width="30" height="22" rx="8" fill="none" stroke="#F7F4EC" stroke-width="2.2"/>
        <path d="M14 36 l5 -5" fill="none" stroke="#F7F4EC" stroke-width="2.2" stroke-linecap="round"/>
        <rect x="26" y="24" width="30" height="22" rx="8" fill="#0B3D2E" stroke="#C8962E" stroke-width="2.2"/>
        <path d="M48 46 l5 5" fill="none" stroke="#C8962E" stroke-width="2.2" stroke-linecap="round"/>
    """,
    "call": """
        <g transform="translate(32 32) rotate(-38) translate(-32 -32)">
            <rect x="27" y="14" width="10" height="36" rx="5" fill="#F7F4EC"/>
            <circle cx="32" cy="16" r="8" fill="#C8962E"/>
            <circle cx="32" cy="48" r="8" fill="#C8962E"/>
        </g>
    """,
}


def channel_tile(x: float, y: float, channel: str, size: float = 64, label: bool = True) -> str:
    scale = size / 64
    glyph = (
        f'<g transform="translate({x} {y}) scale({scale})">'
        f'<rect width="64" height="64" rx="16" fill="{GREEN}"/>'
        f"{ICON_GLYPHS[channel]}</g>"
    )
    if not label:
        return glyph
    return glyph + text(x + size / 2, y + size + 22, channel, 14, weight=600, anchor="middle")


def channel_hop(x: float, y: float, size: float, gap: float, channels: list[str]) -> str:
    parts = []
    cursor = x
    for index, channel in enumerate(channels):
        parts.append(channel_tile(cursor, y, channel, size))
        cursor += size
        if index < len(channels) - 1:
            mid_y = y + size / 2
            parts.append(arrow(cursor + 4, mid_y, cursor + gap - 4))
            cursor += gap
    return "".join(parts)


def card(x: float, y: float, w: float, h: float) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="22" fill="{CARD}" '
        f'stroke="{LINE}" stroke-width="1.5"/>'
    )


def hero_svg(metrics: dict) -> str:
    width, height = 1600, 800
    margin = 40
    gap = 56
    card_w = (width - margin * 2 - gap * 2) / 3
    card_h = 648
    card_y = 88
    xs = [margin + index * (card_w + gap) for index in range(3)]
    parts = [
        text(margin, 52, "Omnichannel care analytics", 26, family="Fraunces", weight=700),
        pill(width - margin - 176, 28, "synthetic data", 176, 34),
    ]
    for index in range(2):
        x1 = xs[index] + card_w + 8
        x2 = xs[index + 1] - 8
        parts.append(arrow(x1, card_y + card_h / 2, x2))

    parts.append(problem_card(xs[0], card_y, card_w, card_h))
    parts.append(method_card(xs[1], card_y, card_w, card_h, metrics))
    parts.append(result_card(xs[2], card_y, card_w, card_h, metrics))
    parts.append(
        text(
            width / 2,
            778,
            (
                f"Seed {metrics['seed']}. {metrics['journeys']:,} synthetic journeys. "
                f"{metrics['events']:,} events. Not a field measurement."
            ),
            15,
            weight=500,
            fill=MUTED,
            anchor="middle",
        )
    )
    return svg_document(width, height, "".join(parts))


def problem_card(x: float, y: float, w: float, h: float) -> str:
    """Channel hop only. No outcome claim: the result panel carries the rates."""

    parts = [card(x, y, w, h)]
    left = x + 32
    parts.append(text(left, y + 44, "PROBLEM", 13, weight=700, fill=GOLD, spacing=1.8))
    parts.append(text(left, y + 90, "Customers keep hopping", 30, family="Fraunces", weight=700))
    parts.append(text(left, y + 122, "One issue moves across channels", 16, weight=500, fill=MUTED))
    parts.append(text(left, y + 144, "before it is closed.", 16, weight=500, fill=MUTED))

    channels = ["ussd", "app", "web", "social", "call"]
    size = 56
    step = 78
    icon_x = x + 48
    top = y + 184
    for index, channel in enumerate(channels):
        iy = top + index * step
        parts.append(channel_tile(icon_x, iy, channel, size, label=False))
        parts.append(text(icon_x + size + 20, iy + 34, channel, 22, weight=700))
        if index < len(channels) - 1:
            parts.append(down_arrow(icon_x + size / 2, iy + size + 2, iy + step - 2))
    parts.append(
        text(
            x + w / 2,
            y + h - 28,
            "Same issue. Next channel.",
            15,
            weight=500,
            fill=MUTED,
            anchor="middle",
        )
    )
    return "".join(parts)


def method_card(x: float, y: float, w: float, h: float, metrics: dict) -> str:
    parts = [card(x, y, w, h)]
    left = x + 32
    parts.append(text(left, y + 44, "METHOD", 13, weight=700, fill=GOLD, spacing=1.8))
    parts.append(text(left, y + 92, "Score the path", 32, family="Fraunces", weight=700))
    parts.append(text(left, y + 128, "The pipeline this repo actually runs.", 16, weight=500, fill=MUTED))

    steps = [
        ("1", "Bitext taxonomy", f"{metrics['n_intents']} public intents, {metrics['n_categories']} categories"),
        ("2", "Journey generator", "synthetic.py and synthetic.yaml"),
        ("3", "DuckDB KPIs", "Funnel, first response, switches"),
        ("4", "Sankey and friction", "Charts the pipeline writes"),
    ]
    top = y + 176
    step_h = 86
    step_gap = 28
    box_x = x + 32
    box_w = w - 64
    for index, (num, title, subtitle) in enumerate(steps):
        sy = top + index * (step_h + step_gap)
        parts.append(f'<rect x="{box_x}" y="{sy}" width="{box_w}" height="{step_h}" rx="16" fill="{CREAM}"/>')
        parts.append(f'<circle cx="{box_x + 36}" cy="{sy + step_h / 2}" r="16" fill="{GREEN}"/>')
        parts.append(
            text(
                box_x + 36,
                sy + step_h / 2 + 6,
                num,
                16,
                family="Fraunces",
                weight=700,
                fill=CREAM,
                anchor="middle",
            )
        )
        parts.append(text(box_x + 68, sy + 36, title, 18, weight=700))
        parts.append(text(box_x + 68, sy + 60, subtitle, 14, weight=500, fill=MUTED))
        if index < len(steps) - 1:
            parts.append(down_arrow(box_x + 36, sy + step_h + 2, sy + step_h + step_gap - 2))
    return "".join(parts)


def result_card(x: float, y: float, w: float, h: float, metrics: dict) -> str:
    parts = [card(x, y, w, h)]
    left = x + 32
    parts.append(text(left, y + 44, "RESULT", 13, weight=700, fill=GOLD, spacing=1.8))
    parts.append(pill(x + w - 32 - 158, y + 22, "synthetic data", 158, 30))
    parts.append(text(left, y + 92, "Where they get stuck", 30, family="Fraunces", weight=700))

    col_w = (w - 64 - 16) / 2
    stat_y = y + 168
    stats = [
        (metrics["digital_to_call_pct"], "digital-first journeys", "that later reach a call", metrics["digital_to_call_fraction"]),
        (metrics["resolved_pct"], "of all journeys", "resolve", metrics["resolved_fraction"]),
    ]
    for index, (big, line_a, line_b, fraction) in enumerate(stats):
        sx = left + index * (col_w + 16)
        parts.append(f'<rect x="{sx}" y="{stat_y}" width="{col_w}" height="148" rx="16" fill="{CREAM}"/>')
        parts.append(text(sx + 16, stat_y + 58, big, 40, family="Fraunces", weight=700))
        parts.append(text(sx + 16, stat_y + 86, line_a, 13, weight=500, fill=MUTED))
        parts.append(text(sx + 16, stat_y + 104, line_b, 13, weight=500, fill=MUTED))
        parts.append(text(sx + 16, stat_y + 128, fraction, 13, weight=600, fill=GOLD))

    parts.append(text(left, y + 356, "Still a call, by intent group", 16, weight=700))
    parts.append(
        text(
            left,
            y + 378,
            "Share of that group's digital-first journeys.",
            13,
            weight=500,
            fill=MUTED,
        )
    )
    bar_x = left
    bar_w = w - 64
    max_track = bar_w - 118
    top = y + 404
    for index, row in enumerate(metrics["groups"]):
        by = top + index * 70
        parts.append(text(bar_x, by + 16, row["label"], 14, weight=600))
        parts.append(
            f'<rect x="{bar_x}" y="{by + 26}" width="{max_track}" height="16" rx="8" fill="{TRACK}"/>'
        )
        fill = GOLD if row["key"] == "complaint" else GREEN
        length = max(8, max_track * row["rate"])
        parts.append(
            f'<rect x="{bar_x}" y="{by + 26}" width="{length:.1f}" height="16" rx="8" fill="{fill}"/>'
        )
        parts.append(text(bar_x + max_track + 12, by + 39, row["pct"], 14, weight=700))
        parts.append(text(bar_x + max_track + 12, by + 56, row["fraction"], 11, weight=500, fill=MUTED))
    return "".join(parts)


def social_svg(metrics: dict) -> str:
    width, height = 1280, 640
    margin = 48
    parts = [
        text(margin, 92, "omnichannel-care-analytics", 34, family="Fraunces", weight=700),
        text(
            margin,
            128,
            "Customers hop channels before a resolution.",
            20,
            weight=500,
            fill=MUTED,
        ),
        pill(width - margin - 168, 62, "synthetic data", 168, 32),
    ]
    panel_y = 168
    panel_h = 420
    gap = 36
    panel_w = (width - margin * 2 - gap * 2) / 3
    xs = [margin + index * (panel_w + gap) for index in range(3)]
    for index in range(2):
        parts.append(arrow(xs[index] + panel_w + 6, panel_y + 78, xs[index + 1] - 6))

    parts.append(social_problem(xs[0], panel_y, panel_w, panel_h))
    parts.append(social_method(xs[1], panel_y, panel_w, panel_h))
    parts.append(social_result(xs[2], panel_y, panel_w, panel_h, metrics))
    return svg_document(width, height, "".join(parts))


def social_problem(x: float, y: float, w: float, h: float) -> str:
    parts = [card(x, y, w, h)]
    parts.append(text(x + 22, y + 36, "PROBLEM", 12, weight=700, fill=GOLD, spacing=1.6))
    parts.append(text(x + 22, y + 68, "They hop first", 24, family="Fraunces", weight=700))
    channels = ["ussd", "app", "web", "social", "call"]
    size = 44
    step = 62
    icon_x = x + 28
    top = y + 96
    for index, channel in enumerate(channels):
        iy = top + index * step
        parts.append(channel_tile(icon_x, iy, channel, size, label=False))
        parts.append(text(icon_x + size + 14, iy + size / 2 + 6, channel, 16, weight=700))
        if index < len(channels) - 1:
            parts.append(down_arrow(icon_x + size / 2, iy + size + 1, iy + step - 1))
    return "".join(parts)


def social_method(x: float, y: float, w: float, h: float) -> str:
    parts = [card(x, y, w, h)]
    parts.append(text(x + 24, y + 40, "METHOD", 13, weight=700, fill=GOLD, spacing=1.6))
    parts.append(text(x + 24, y + 78, "Then score it", 26, family="Fraunces", weight=700))
    steps = ["Bitext intents", "Synthetic journeys", "DuckDB KPIs", "Sankey and friction"]
    top = y + 112
    step_h = 48
    step_gap = 16
    for index, label in enumerate(steps):
        sy = top + index * (step_h + step_gap)
        parts.append(f'<rect x="{x + 24}" y="{sy}" width="{w - 48}" height="{step_h}" rx="12" fill="{CREAM}"/>')
        parts.append(f'<circle cx="{x + 48}" cy="{sy + step_h / 2}" r="12" fill="{GREEN}"/>')
        parts.append(
            text(x + 48, sy + step_h / 2 + 5, str(index + 1), 13, family="Fraunces", weight=700, fill=CREAM, anchor="middle")
        )
        parts.append(text(x + 72, sy + 30, label, 15, weight=600))
        if index < len(steps) - 1:
            parts.append(down_arrow(x + 48, sy + step_h + 1, sy + step_h + step_gap - 1))
    return "".join(parts)


def social_result(x: float, y: float, w: float, h: float, metrics: dict) -> str:
    parts = [card(x, y, w, h)]
    parts.append(text(x + 24, y + 40, "RESULT", 13, weight=700, fill=GOLD, spacing=1.6))
    parts.append(text(x + 24, y + 86, metrics["digital_to_call_pct"], 48, family="Fraunces", weight=700))
    parts.append(text(x + 24, y + 114, "of digital-first journeys", 14, weight=500, fill=MUTED))
    parts.append(text(x + 24, y + 134, "later reach a call", 14, weight=500, fill=MUTED))
    parts.append(text(x + 24, y + 156, metrics["digital_to_call_fraction"], 13, weight=600, fill=GOLD))
    bar_x = x + 24
    max_track = w - 48 - 64
    top = y + 186
    for index, row in enumerate(metrics["groups"]):
        by = top + index * 52
        parts.append(text(bar_x, by + 12, row["label"], 13, weight=600))
        parts.append(f'<rect x="{bar_x}" y="{by + 20}" width="{max_track}" height="12" rx="6" fill="{TRACK}"/>')
        fill = GOLD if row["key"] == "complaint" else GREEN
        length = max(6, max_track * row["rate"])
        parts.append(f'<rect x="{bar_x}" y="{by + 20}" width="{length:.1f}" height="12" rx="6" fill="{fill}"/>')
        parts.append(text(bar_x + max_track + 8, by + 31, row["pct"], 13, weight=700))
    return "".join(parts)


def write_png(svg: str, path: Path, width: int, height: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(
        bytestring=svg.encode("utf-8"),
        write_to=str(path),
        output_width=width,
        output_height=height,
    )
    optimize(path)


def optimize(path: Path) -> None:
    before = path.stat().st_size
    subprocess.run(
        ["pngquant", "--force", "--skip-if-larger", "--quality", "80-100", "--output", str(path), str(path)],
        check=False,
        capture_output=True,
    )
    subprocess.run(["optipng", "-o2", "-quiet", str(path)], check=False, capture_output=True)
    after = path.stat().st_size
    print(f"{path.name}: {before} -> {after} bytes")


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        signature = handle.read(8)
        if signature != b"\x89PNG\r\n\x1a\n":
            raise SystemExit(f"{path} is not a PNG")
        handle.read(4)
        if handle.read(4) != b"IHDR":
            raise SystemExit(f"{path} missing IHDR")
        width, height = struct.unpack(">II", handle.read(8))
    return width, height


def main() -> None:
    ensure_fonts()
    metrics = load_metrics()
    write_png(hero_svg(metrics), ASSETS / "hero.png", 1600, 800)
    write_png(social_svg(metrics), ASSETS / "social-preview.png", 1280, 640)
    for name, expected in (
        ("hero.png", (1600, 800)),
        ("social-preview.png", (1280, 640)),
    ):
        actual = png_size(ASSETS / name)
        if actual != expected:
            raise SystemExit(f"{name} is {actual}, expected {expected}")
    print("digital-to-call", metrics["digital_to_call_pct"], metrics["digital_to_call_fraction"])
    print("resolved", metrics["resolved_pct"], metrics["resolved_fraction"])
    for row in metrics["groups"]:
        print("group", row["label"], row["pct"], row["fraction"])
    for row in metrics["ttfr"]:
        print("ttfr", row["channel"], row["median_label"], row["p90_label"], row["n"])
    for row in metrics["resolution"]:
        print("resolution", row["channel"], row["pct"], row["fraction"])


if __name__ == "__main__":
    main()
