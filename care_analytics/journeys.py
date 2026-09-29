"""Build one row per journey and the directly-follows table.

DuckDB does the grouped journey aggregation and the directly-follows counts.
Pandas applies the channel-shift flags from the configured channel roles.
"""

from __future__ import annotations

import duckdb
import pandas as pd

DIGITAL_CHANNELS = ["ussd", "app", "web", "social"]
ASSISTED_CHANNEL = "call"


def _as_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.map(lambda value: bool(value) if isinstance(value, (bool, int, float)) and not isinstance(value, str) else str(value).strip().lower() == "true")

JOURNEY_SQL = """
SELECT
  journey_id,
  arg_min(customer_id, contact_index) AS customer_id,
  arg_min(intent, contact_index) AS intent,
  arg_min(category, contact_index) AS category,
  arg_min(intent_group, contact_index) AS intent_group,
  arg_min(channel, contact_index) AS first_channel,
  arg_min(event_ts, contact_index) AS first_event_ts,
  arg_min(ttfr_minutes, contact_index) AS ttfr_minutes,
  arg_min(journey_end_reason, contact_index) AS journey_end_reason,
  count(*)::INTEGER AS n_contacts,
  bool_or(resolved) AS resolved,
  string_agg(channel, ' > ' ORDER BY contact_index) AS channel_path
FROM events
GROUP BY journey_id
ORDER BY journey_id
"""

DIRECTLY_FOLLOWS_SQL = """
WITH ordered AS (
  SELECT
    journey_id,
    contact_index,
    channel,
    resolved,
    lead(channel) OVER (PARTITION BY journey_id ORDER BY contact_index) AS next_channel
  FROM events
)
SELECT
  channel AS from_activity,
  CASE
    WHEN resolved THEN 'resolved'
    WHEN next_channel IS NULL THEN 'abandoned'
    ELSE next_channel
  END AS to_activity,
  count(*)::INTEGER AS n
FROM ordered
GROUP BY 1, 2
ORDER BY 1, 2
"""


def _connect(events: pd.DataFrame) -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect()
    connection.register("events", events)
    return connection


def build_journeys(
    events: pd.DataFrame,
    digital_channels: list[str] | None = None,
    assisted_channel: str = ASSISTED_CHANNEL,
) -> pd.DataFrame:
    if events.empty:
        raise ValueError("events is empty")
    prepared = events.copy()
    prepared["resolved"] = _as_bool(prepared["resolved"])
    digital = digital_channels or DIGITAL_CHANNELS
    connection = _connect(prepared)
    journeys = connection.execute(JOURNEY_SQL).df()
    connection.close()
    journeys["resolved"] = _as_bool(journeys["resolved"])
    journeys["n_contacts"] = journeys["n_contacts"].astype(int)

    resolved_rows = prepared.loc[prepared["resolved"], ["journey_id", "channel", "contact_index"]]
    if resolved_rows["journey_id"].duplicated().any():
        raise ValueError("a journey has more than one resolved contact")
    resolving = resolved_rows.rename(columns={"channel": "resolving_channel", "contact_index": "resolving_contact_index"})
    journeys = journeys.merge(resolving, on="journey_id", how="left")

    later_assisted = prepared.loc[
        (prepared["channel"] == assisted_channel) & (prepared["contact_index"] > 1),
        "journey_id",
    ].unique()
    assisted_ids = set(later_assisted)
    paths = journeys["channel_path"].str.split(" > ")
    journeys["n_channels"] = paths.map(lambda steps: len(set(steps))).astype(int)
    journeys["repeat_contact"] = journeys["n_contacts"] >= 2
    journeys["channel_switch"] = journeys["n_channels"] > 1
    journeys["digital_first"] = journeys["first_channel"].isin(digital)
    journeys["digital_to_call"] = journeys["digital_first"] & journeys["journey_id"].isin(assisted_ids)
    journeys["resolved_on_first_contact"] = journeys["resolved"] & (journeys["n_contacts"] == 1)
    journeys["data_origin"] = "SYNTHETIC"

    inconsistent = journeys["resolved"] & journeys["resolving_channel"].isna()
    if bool(inconsistent.any()):
        raise ValueError("resolved journey is missing a resolving channel")
    return journeys


def directly_follows(events: pd.DataFrame) -> pd.DataFrame:
    connection = _connect(events)
    table = connection.execute(DIRECTLY_FOLLOWS_SQL).df()
    connection.close()
    table["data_origin"] = "SYNTHETIC"
    return table


def sankey_links(journeys: pd.DataFrame) -> pd.DataFrame:
    """First channel to a three-way outcome. Counts sum to the journey count."""

    def outcome(row: pd.Series) -> str:
        if bool(row["resolved_on_first_contact"]):
            return "Resolved on first contact"
        if bool(row["resolved"]):
            return "Resolved after another contact"
        return "Abandoned"

    labelled = journeys.copy()
    labelled["outcome"] = labelled.apply(outcome, axis=1)
    links = (
        labelled.groupby(["first_channel", "outcome"], as_index=False)
        .size()
        .rename(columns={"size": "n"})
        .sort_values(["first_channel", "outcome"])
        .reset_index(drop=True)
    )
    links["data_origin"] = "SYNTHETIC"
    return links
