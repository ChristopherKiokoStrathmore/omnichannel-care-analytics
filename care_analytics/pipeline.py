"""Reproduce the committed tables, charts, and written figures."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from care_analytics.charts import friction_matrix, write_friction_heatmap, write_sankey
from care_analytics.journeys import build_journeys, directly_follows
from care_analytics.kpis import compute_kpis
from care_analytics.public_data import load_json
from care_analytics.report import render_headlines, render_recommendations
from care_analytics.synthetic import generate_events, load_config, load_taxonomy

ROOT = Path(__file__).resolve().parents[1]


def _instruction_length(by_intent: pd.DataFrame) -> dict:
    shortest = by_intent.sort_values(
        ["median_instruction_chars", "intent"], ascending=[True, True]
    ).iloc[0]
    longest = by_intent.sort_values(
        ["median_instruction_chars", "intent"], ascending=[False, True]
    ).iloc[0]
    return {
        "shortest_intent": str(shortest["intent"]),
        "shortest_median_chars": float(shortest["median_instruction_chars"]),
        "longest_intent": str(longest["intent"]),
        "longest_median_chars": float(longest["median_instruction_chars"]),
    }


def _public_block(root: Path) -> dict:
    derived = root / "data" / "derived"
    meta = load_json(derived / "bitext_meta.json")
    by_intent = pd.read_csv(derived / "bitext_by_intent.csv")
    by_category = pd.read_csv(derived / "bitext_by_category.csv")
    by_tag = pd.read_csv(derived / "bitext_by_tag.csv")
    meta["by_category"] = by_category.to_dict(orient="records")
    meta["by_tag"] = by_tag.to_dict(orient="records")
    meta["instruction_length"] = _instruction_length(by_intent)
    twitter = load_json(derived / "twitter_sample_summary.json")
    return {"bitext": meta, "twitter_sample": twitter}


def _write_frame(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, float_format="%.6f", lineterminator="\n")


def build_report(root: Path = ROOT) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    config = load_config(root / "config" / "synthetic.yaml")
    taxonomy = load_taxonomy(root / "data" / "derived" / "bitext_by_intent.csv")
    events = generate_events(config, taxonomy)
    journeys = build_journeys(
        events,
        digital_channels=list(config["digital_channels"]),
        assisted_channel=config["assisted_channel"],
    )
    synthetic = compute_kpis(events, journeys, config)
    synthetic["config"] = config
    report = {"public": _public_block(root), "synthetic": synthetic}
    return report, events, journeys


def write_outputs(root: Path, report: dict, events: pd.DataFrame, journeys: pd.DataFrame) -> None:
    derived = root / "data" / "derived"
    charts = root / "reports" / "charts"
    _write_frame(events, derived / "SYNTHETIC_multichannel_events.csv")
    journey_columns = [
        "data_origin",
        "journey_id",
        "customer_id",
        "intent",
        "category",
        "intent_group",
        "first_channel",
        "first_event_ts",
        "ttfr_minutes",
        "n_contacts",
        "n_channels",
        "channel_path",
        "resolved",
        "resolved_on_first_contact",
        "resolving_channel",
        "resolving_contact_index",
        "repeat_contact",
        "channel_switch",
        "digital_first",
        "digital_to_call",
        "journey_end_reason",
    ]
    _write_frame(journeys[journey_columns], derived / "SYNTHETIC_journeys.csv")
    matrix = friction_matrix(events)
    _write_frame(matrix, charts / "SYNTHETIC_friction_matrix.csv")
    flows = directly_follows(events)
    _write_frame(flows, charts / "SYNTHETIC_directly_follows.csv")
    write_sankey(pd.DataFrame(report["synthetic"]["sankey"]), charts / "SYNTHETIC_sankey.html")
    write_friction_heatmap(matrix, charts / "SYNTHETIC_friction_heatmap.html")
    (root / "reports" / "kpis.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (root / "reports" / "headlines.md").write_text(
        render_headlines(report), encoding="utf-8"
    )
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "recommendations.md").write_text(
        render_recommendations(report), encoding="utf-8"
    )


def run(root: Path = ROOT) -> dict:
    report, events, journeys = build_report(root)
    write_outputs(root, report, events, journeys)
    funnel = report["synthetic"]["funnel"]
    print(
        "Wrote synthetic journeys "
        f"{funnel['journeys']} and events {funnel['events']} "
        f"(seed {report['synthetic']['seed']})."
    )
    return report
