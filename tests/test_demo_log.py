"""The interactive demo reads a compact copy of the committed synthetic log."""

import json
import math
from pathlib import Path

import duckdb
import pandas as pd

from care_analytics.demo_log import build_demo_log, demo_log_path, dumps_demo_log

ROOT = Path(__file__).resolve().parents[1]

CHANNELS = ["ussd", "app", "web", "social", "call"]
OUTCOMES = (
    "Resolved on first contact",
    "Resolved after another contact",
    "Abandoned",
)


def quantile_cont(values: list[float], q: float) -> float:
    """DuckDB quantile_cont linear interpolation: position q * (n - 1)."""

    ordered = sorted(values)
    count = len(ordered)
    if count == 0:
        raise ValueError("empty")
    if count == 1:
        return ordered[0]
    pos = q * (count - 1)
    index = math.floor(pos)
    frac = pos - index
    if index >= count - 1:
        return ordered[-1]
    return ordered[index] * (1 - frac) + ordered[index + 1] * frac


def _flows(journeys: list) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = {}
    for item in journeys:
        path = item[7]
        resolved = item[8] == 1
        for index, channel in enumerate(path):
            if index == len(path) - 1:
                target = "resolved" if resolved else "abandoned"
            else:
                target = path[index + 1]
            key = (channel, target)
            counts[key] = counts.get(key, 0) + 1
    return counts


def test_committed_demo_log_matches_the_builder():
    payload = build_demo_log(ROOT)
    path = demo_log_path(ROOT)
    assert path.is_file()
    assert dumps_demo_log(payload) == path.read_text(encoding="utf-8")
    assert json.loads(path.read_text(encoding="utf-8"))["label"] == "SYNTHETIC"
    assert payload["not_a_real_world_measurement"] is True
    assert payload["seed"] == 20260929
    assert payload["n_journeys"] == 4000
    assert payload["n_events"] == 6376
    assert payload["taxonomy"]["n_examples"] == 26000
    assert payload["taxonomy"]["n_intents"] == 26
    assert payload["taxonomy"]["examples_per_intent"] == 1000
    text = path.read_text(encoding="utf-8")
    assert "instruction" not in text or "median_instruction_chars" in text
    assert "utterance" not in text


def test_demo_log_paths_reproduce_committed_kpis():
    payload = build_demo_log(ROOT)
    report = json.loads((ROOT / "reports" / "kpis.json").read_text(encoding="utf-8"))
    journeys = payload["journeys"]
    saved = pd.read_csv(ROOT / "data" / "derived" / "SYNTHETIC_journeys.csv")
    assert [item[0] for item in journeys] == saved.sort_values("journey_id")["journey_id"].tolist()

    resolved = sum(item[8] for item in journeys)
    first = sum(1 for item in journeys if item[8] == 1 and item[6] == 1)
    repeat = sum(1 for item in journeys if item[6] >= 2)
    switched = sum(1 for item in journeys if len(set(item[7])) > 1)
    digital_first = sum(1 for item in journeys if item[4] in payload["digital_channels"])
    digital_to_call = sum(
        1 for item in journeys if item[4] in payload["digital_channels"] and "call" in item[7][1:]
    )
    funnel = report["synthetic"]["funnel"]
    assert resolved == funnel["resolved"] == 3256
    assert first == funnel["resolved_on_first_contact"] == 2223
    assert repeat == funnel["repeat_contact"] == 1462
    assert switched == funnel["channel_switch"] == 1235
    assert digital_first == funnel["digital_first"] == 3035
    assert digital_to_call == funnel["digital_to_call"] == 971

    contacts: dict[str, int] = {channel: 0 for channel in CHANNELS}
    resolved_contacts: dict[str, int] = {channel: 0 for channel in CHANNELS}
    for item in journeys:
        path = item[7]
        for index, channel in enumerate(path):
            contacts[channel] += 1
            if index == len(path) - 1 and item[8] == 1:
                resolved_contacts[channel] += 1
    for row in report["synthetic"]["resolution_by_channel"]:
        assert contacts[row["channel"]] == row["contacts"]
        assert resolved_contacts[row["channel"]] == row["resolved_contacts"]

    flows = _flows(journeys)
    stored = {
        (row["from_activity"], row["to_activity"]): row["n"]
        for row in report["synthetic"]["directly_follows"]
    }
    assert flows == stored
    assert flows[("ussd", "call")] == 385

    sankey: dict[tuple[str, str], int] = {}
    for item in journeys:
        if item[8] == 1 and item[6] == 1:
            outcome = OUTCOMES[0]
        elif item[8] == 1:
            outcome = OUTCOMES[1]
        else:
            outcome = OUTCOMES[2]
        key = (item[4], outcome)
        sankey[key] = sankey.get(key, 0) + 1
    for row in report["synthetic"]["sankey"]:
        assert sankey[(row["first_channel"], row["outcome"])] == row["n"]

    frame = saved.copy()
    connection = duckdb.connect()
    connection.register("journeys", frame)
    duck = connection.execute(
        """
        SELECT first_channel AS channel,
               quantile_cont(ttfr_minutes, 0.5) AS median_minutes,
               quantile_cont(ttfr_minutes, 0.9) AS p90_minutes
        FROM journeys
        GROUP BY first_channel
        """
    ).df()
    connection.close()
    by_channel: dict[str, list[float]] = {channel: [] for channel in CHANNELS}
    for item in journeys:
        by_channel[item[4]].append(float(item[5]))
    for row in duck.to_dict(orient="records"):
        channel = str(row["channel"])
        assert quantile_cont(by_channel[channel], 0.5) == pytest_approx(row["median_minutes"])
        assert quantile_cont(by_channel[channel], 0.9) == pytest_approx(row["p90_minutes"])
        stored_row = next(
            item for item in report["synthetic"]["ttfr_by_first_channel"] if item["channel"] == channel
        )
        assert f"{quantile_cont(by_channel[channel], 0.5):.1f}" == f"{stored_row['median_minutes']:.1f}"
        assert f"{quantile_cont(by_channel[channel], 0.9):.1f}" == f"{stored_row['p90_minutes']:.1f}"


def pytest_approx(value: float):
    import pytest

    return pytest.approx(value)
