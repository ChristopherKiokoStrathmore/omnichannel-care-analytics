"""Compact synthetic log for the interactive demo.

The Next.js app cannot see files outside ``web/`` when Vercel builds with that
directory as the project root. This module writes a JSON copy of the committed
journey rows plus the public Bitext taxonomy tables. It does not copy raw
training utterances.

Journey tuples, in order:
id, intent, category, group, first channel, time-to-first-response minutes,
contact count, channel path, resolved (1 or 0), end reason.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from care_analytics.synthetic import load_config

DIGITAL_CHANNELS = ["ussd", "app", "web", "social"]
END_REASONS = ("resolved", "chose_abandon", "max_contacts")


def _clean_float(value: float, places: int = 6) -> float:
    return float(f"{float(value):.{places}f}")


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() == "true"


def _group_for_intent(config: dict) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for group, names in config["intent_groups"].items():
        for name in names:
            if name in mapping:
                raise ValueError(f"{name} is in more than one intent group")
            mapping[name] = str(group)
    return mapping


def _journey_tuple(row: pd.Series) -> list:
    path = str(row["channel_path"]).split(" > ")
    contacts = int(row["n_contacts"])
    if len(path) != contacts:
        raise ValueError(f"{row['journey_id']} path length does not match n_contacts")
    resolved = _as_bool(row["resolved"])
    end = str(row["journey_end_reason"])
    if end not in END_REASONS:
        raise ValueError(f"{row['journey_id']} has end reason {end}")
    if resolved != (end == "resolved"):
        raise ValueError(f"{row['journey_id']} resolved flag disagrees with end reason")
    first = str(row["first_channel"])
    if path[0] != first:
        raise ValueError(f"{row['journey_id']} path does not start on {first}")
    later_call = "call" in path[1:]
    digital_first = first in DIGITAL_CHANNELS
    if _as_bool(row["digital_first"]) != digital_first:
        raise ValueError(f"{row['journey_id']} digital_first disagrees with the path")
    if _as_bool(row["digital_to_call"]) != (digital_first and later_call):
        raise ValueError(f"{row['journey_id']} digital_to_call disagrees with the path")
    if _as_bool(row["repeat_contact"]) != (contacts >= 2):
        raise ValueError(f"{row['journey_id']} repeat_contact disagrees with the path")
    if _as_bool(row["channel_switch"]) != (len(set(path)) > 1):
        raise ValueError(f"{row['journey_id']} channel_switch disagrees with the path")
    if _as_bool(row["resolved_on_first_contact"]) != (resolved and contacts == 1):
        raise ValueError(f"{row['journey_id']} first-contact flag disagrees with the path")
    return [
        str(row["journey_id"]),
        str(row["intent"]),
        str(row["category"]),
        str(row["intent_group"]),
        first,
        _clean_float(float(row["ttfr_minutes"])),
        contacts,
        path,
        1 if resolved else 0,
        end,
    ]


def build_demo_log(root: Path) -> dict:
    config = load_config(root / "config" / "synthetic.yaml")
    groups = _group_for_intent(config)
    weights = {str(name): int(weight) for name, weight in config["intent_weights"].items()}
    journeys = pd.read_csv(root / "data" / "derived" / "SYNTHETIC_journeys.csv")
    by_intent = pd.read_csv(root / "data" / "derived" / "bitext_by_intent.csv")
    by_category = pd.read_csv(root / "data" / "derived" / "bitext_by_category.csv")
    by_tag = pd.read_csv(root / "data" / "derived" / "bitext_by_tag.csv")

    if set(by_intent["intent"]) != set(groups):
        raise ValueError("Bitext intents and config intent groups do not match")
    if set(by_intent["intent"]) != set(weights):
        raise ValueError("Bitext intents and config intent weights do not match")

    intent_rows = []
    for record in by_intent.to_dict(orient="records"):
        intent = str(record["intent"])
        intent_rows.append(
            {
                "category": str(record["category"]),
                "group": groups[intent],
                "intent": intent,
                "median_instruction_chars": _clean_float(float(record["median_instruction_chars"]), 1),
                "median_response_chars": _clean_float(float(record["median_response_chars"]), 1),
                "n_examples": int(record["n_examples"]),
                "weight": weights[intent],
            }
        )

    tuples = [_journey_tuple(row) for _, row in journeys.sort_values("journey_id").iterrows()]
    n_events = sum(item[6] for item in tuples)
    return {
        "assisted_channel": "call",
        "digital_channels": list(DIGITAL_CHANNELS),
        "journeys": tuples,
        "label": "SYNTHETIC",
        "n_events": n_events,
        "n_journeys": len(tuples),
        "not_a_real_world_measurement": True,
        "seed": int(config["seed"]),
        "taxonomy": {
            "categories": [
                {
                    "category": str(row["category"]),
                    "n_examples": int(row["n_examples"]),
                    "n_intents": int(row["n_intents"]),
                }
                for row in by_category.to_dict(orient="records")
            ],
            "described_as": "hybrid synthetic training set",
            "examples_per_intent": 1000,
            "intents": intent_rows,
            "licence": "CDLA-Sharing-1.0",
            "n_categories": int(by_category["category"].nunique()),
            "n_examples": int(by_intent["n_examples"].sum()),
            "n_intents": int(len(by_intent)),
            "source": "bitext/Bitext-telco-llm-chatbot-training-dataset",
            "tags": [
                {
                    "meaning": str(row["meaning"]),
                    "n_examples": int(row["n_examples"]),
                    "tag": str(row["tag"]),
                }
                for row in by_tag.to_dict(orient="records")
            ],
        },
    }


def demo_log_path(root: Path) -> Path:
    return root / "web" / "data" / "demo-log.json"


def dumps_demo_log(payload: dict) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"


def write_demo_log(root: Path) -> Path:
    path = demo_log_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_demo_log(build_demo_log(root)), encoding="utf-8")
    return path
