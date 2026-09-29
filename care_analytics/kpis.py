"""KPI tables for the synthetic log, with the definitions beside the numbers."""

from __future__ import annotations

import duckdb
import pandas as pd

from care_analytics.journeys import directly_follows, sankey_links

DEFINITIONS = {
    "time_to_first_response": (
        "Time-to-first-response is the delay, in minutes, between a journey's first "
        "inbound timestamp and the response timestamp on that same first contact. "
        "Median and the 90th percentile use DuckDB quantile_cont (linear). "
        "The synthetic generator draws each delay from the channel lognormal in "
        "config/synthetic.yaml and then clips it. Every synthetic contact has a "
        "response, so there are no censored non-responses."
    ),
    "repeat_contact": (
        "Repeat-contact rate is the share of synthetic journeys with two or more "
        "contacts. A repeat contact is a later contact in the same journey after an "
        "unresolved contact. The synthetic log has one journey per customer, so this "
        "is not a later, separate issue from the same person."
    ),
    "channel_switch": (
        "Channel-switch rate is the share of synthetic journeys whose contacts use "
        "more than one distinct channel. A second contact on the same channel is a "
        "repeat contact and is not a channel switch."
    ),
    "digital_to_call": (
        "A synthetic digital-to-call journey starts on a digital channel (ussd, app, "
        "web, or social) and has a later contact on the call channel. That is the "
        "operational definition of a failed digital attempt that ends in a call. "
        "The rate is reported for all journeys and again among digital-first "
        "journeys only."
    ),
    "resolution_rate": (
        "On the synthetic log, contact resolution rate for a channel, or for an "
        "intent group on a channel, is resolved contacts divided by contacts on "
        "that slice. A journey has at "
        "most one resolved contact, the one that closes it. Journey resolution rate "
        "is journeys whose end reason is resolved, divided by journeys. Realised "
        "rates are outputs. They are not the base probabilities in the config: each "
        "contact multiplies that base by attempt decay and, when the response is "
        "slower than the configured threshold, by the slow-response factor."
    ),
}


TTFR_SQL = """
SELECT
  first_channel AS channel,
  count(*)::INTEGER AS journeys,
  quantile_cont(ttfr_minutes, 0.5) AS median_minutes,
  quantile_cont(ttfr_minutes, 0.9) AS p90_minutes
FROM journeys
GROUP BY first_channel
ORDER BY first_channel
"""


def _records(frame: pd.DataFrame) -> list[dict]:
    rows = []
    for record in frame.to_dict(orient="records"):
        cleaned = {}
        for key, value in record.items():
            if pd.isna(value):
                cleaned[key] = None
            elif hasattr(value, "item"):
                cleaned[key] = value.item()
            else:
                cleaned[key] = value
        rows.append(cleaned)
    return rows


def _group_resolution(events: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    grouped = events.groupby(keys, as_index=False).agg(
        contacts=("resolved", "size"),
        resolved_contacts=("resolved", "sum"),
    )
    grouped["contacts"] = grouped["contacts"].astype(int)
    grouped["resolved_contacts"] = grouped["resolved_contacts"].astype(int)
    return grouped.sort_values(keys).reset_index(drop=True)


def compute_kpis(events: pd.DataFrame, journeys: pd.DataFrame, config: dict) -> dict:
    connection = duckdb.connect()
    connection.register("journeys", journeys)
    ttfr = connection.execute(TTFR_SQL).df()
    connection.close()

    n_journeys = int(len(journeys))
    digital_first = int(journeys["digital_first"].sum())
    digital_to_call = int(journeys["digital_to_call"].sum())
    funnel = {
        "journeys": n_journeys,
        "events": int(len(events)),
        "customers": int(journeys["customer_id"].nunique()),
        "resolved_on_first_contact": int(journeys["resolved_on_first_contact"].sum()),
        "repeat_contact": int(journeys["repeat_contact"].sum()),
        "channel_switch": int(journeys["channel_switch"].sum()),
        "digital_first": digital_first,
        "digital_to_call": digital_to_call,
        "resolved": int(journeys["resolved"].sum()),
        "abandoned": int((~journeys["resolved"]).sum()),
        "end_chose_abandon": int((journeys["journey_end_reason"] == "chose_abandon").sum()),
        "end_max_contacts": int((journeys["journey_end_reason"] == "max_contacts").sum()),
        "end_resolved": int((journeys["journey_end_reason"] == "resolved").sum()),
    }
    if funnel["resolved"] + funnel["abandoned"] != n_journeys:
        raise ValueError("funnel resolved and abandoned do not cover every journey")
    if funnel["end_resolved"] != funnel["resolved"]:
        raise ValueError("end reason disagrees with the resolved flag")

    by_intent = (
        journeys.groupby(["category", "intent", "intent_group"], as_index=False)
        .agg(
            journeys=("journey_id", "size"),
            resolved_journeys=("resolved", "sum"),
            digital_first=("digital_first", "sum"),
            digital_to_call=("digital_to_call", "sum"),
        )
        .sort_values(["category", "intent"])
        .reset_index(drop=True)
    )
    for column in ["journeys", "resolved_journeys", "digital_first", "digital_to_call"]:
        by_intent[column] = by_intent[column].astype(int)

    by_group = (
        journeys.groupby("intent_group", as_index=False)
        .agg(
            journeys=("journey_id", "size"),
            resolved_journeys=("resolved", "sum"),
            digital_first=("digital_first", "sum"),
            digital_to_call=("digital_to_call", "sum"),
            resolved_on_first_contact=("resolved_on_first_contact", "sum"),
        )
        .sort_values("intent_group")
        .reset_index(drop=True)
    )
    for column in by_group.columns:
        if column != "intent_group":
            by_group[column] = by_group[column].astype(int)

    flows = directly_follows(events).drop(columns=["data_origin"])
    links = sankey_links(journeys).drop(columns=["data_origin"])
    if int(links["n"].sum()) != n_journeys:
        raise ValueError("Sankey links do not sum to the journey count")
    if int(flows["n"].sum()) != int(len(events)):
        raise ValueError("directly-follows counts do not sum to the event count")

    return {
        "label": "SYNTHETIC",
        "not_a_real_world_measurement": True,
        "seed": int(config["seed"]),
        "definitions": DEFINITIONS,
        "assumptions": {
            "attempt_decay": float(config["attempt_decay"]),
            "slow_response_minutes": float(config["slow_response_minutes"]),
            "slow_response_factor": float(config["slow_response_factor"]),
            "resolution_probability_cap": float(config["resolution_probability_cap"]),
            "resolution_probability": config["resolution_probability"],
            "first_channel_weights": config["first_channel_weights"],
            "digital_channels": list(config["digital_channels"]),
            "assisted_channel": config["assisted_channel"],
        },
        "funnel": funnel,
        "ttfr_by_first_channel": _records(ttfr),
        "resolution_by_channel": _records(_group_resolution(events, ["channel"])),
        "resolution_by_group_channel": _records(
            _group_resolution(events, ["intent_group", "channel"])
        ),
        "resolution_by_intent": _records(by_intent),
        "by_intent_group": _records(by_group),
        "directly_follows": _records(flows),
        "sankey": _records(links),
    }
