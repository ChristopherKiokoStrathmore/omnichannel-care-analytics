"""Seeded SYNTHETIC multichannel event log.

The generator does not estimate anything from public files except the intent
names and categories in the Bitext taxonomy table. Demand, channel mix,
resolution chances, and clocks come from config/synthetic.yaml.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

CHANNEL_ORDER = ["ussd", "app", "web", "social", "call"]
NEXT_STEPS = CHANNEL_ORDER + ["abandon"]
EVENT_COLUMNS = [
    "data_origin",
    "event_id",
    "journey_id",
    "customer_id",
    "intent",
    "category",
    "intent_group",
    "channel",
    "contact_index",
    "event_ts",
    "response_ts",
    "ttfr_minutes",
    "base_resolution_probability",
    "slow_response_applied",
    "resolution_probability_used",
    "resolved",
    "journey_end_reason",
]


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("synthetic config must be a mapping")
    return config


def load_taxonomy(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = {"intent", "category"} - set(frame.columns)
    if missing:
        raise ValueError(f"taxonomy missing columns: {sorted(missing)}")
    taxonomy = frame[["intent", "category"]].drop_duplicates()
    if taxonomy["intent"].duplicated().any():
        raise ValueError("taxonomy has more than one category for an intent")
    return taxonomy.sort_values("intent").reset_index(drop=True)


def contact_resolution_probability(
    base: float,
    contact_index: int,
    slow_response_applied: bool,
    attempt_decay: float,
    slow_response_factor: float,
    cap: float,
) -> float:
    """Adjusted resolution probability for one synthetic contact.

    p = min(cap, base * attempt_decay ** (contact_index - 1) * slow_factor)
    slow_factor is 1 unless that contact's response was slower than the
    configured threshold.
    """
    if contact_index < 1:
        raise ValueError("contact_index starts at 1")
    probability = float(base) * (float(attempt_decay) ** (contact_index - 1))
    if slow_response_applied:
        probability *= float(slow_response_factor)
    return float(min(max(probability, 0.0), float(cap)))


def _as_utc_naive(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _fmt(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _weights(mapping: dict, keys: list[str], label: str) -> np.ndarray:
    missing = [key for key in keys if key not in mapping]
    extra = [key for key in mapping if key not in keys]
    if missing or extra:
        raise ValueError(f"{label} keys must be {keys}, missing {missing}, extra {extra}")
    values = np.asarray([float(mapping[key]) for key in keys], dtype=float)
    if np.any(values < 0) or values.sum() <= 0:
        raise ValueError(f"{label} weights must be non-negative and not all zero")
    return values / values.sum()


def _row_sums_to_one(mapping: dict, keys: list[str], label: str) -> np.ndarray:
    missing = [key for key in keys if key not in mapping]
    extra = [key for key in mapping if key not in keys]
    if missing or extra:
        raise ValueError(f"{label} keys must be {keys}, missing {missing}, extra {extra}")
    values = np.asarray([float(mapping[key]) for key in keys], dtype=float)
    if np.any(values < 0) or abs(float(values.sum()) - 1.0) > 1e-6:
        raise ValueError(f"{label} must be non-negative and sum to 1, got {values.sum()}")
    return values


def validate_config(config: dict, taxonomy: pd.DataFrame) -> None:
    intents = set(taxonomy["intent"])
    weight_intents = set(config["intent_weights"])
    if weight_intents != intents:
        raise ValueError(
            "intent_weights must match the taxonomy exactly. "
            f"Missing {sorted(intents - weight_intents)}. "
            f"Extra {sorted(weight_intents - intents)}."
        )
    grouped: list[str] = []
    for name, members in config["intent_groups"].items():
        if name not in {"self_service_candidate", "assisted", "complaint"}:
            raise ValueError(f"unexpected intent group {name}")
        grouped.extend(members)
    if set(grouped) != intents or len(grouped) != len(intents):
        raise ValueError("intent_groups must partition the taxonomy")
    if config["channels"] != CHANNEL_ORDER:
        raise ValueError(f"channels must be {CHANNEL_ORDER}")
    if config["digital_channels"] != ["ussd", "app", "web", "social"]:
        raise ValueError("digital_channels must be ussd, app, web, social")
    if config["assisted_channel"] != "call":
        raise ValueError("assisted_channel must be call")
    if int(config["n_journeys"]) < 1:
        raise ValueError("n_journeys must be at least 1")
    if int(config["max_contacts"]) < 1:
        raise ValueError("max_contacts must be at least 1")
    _weights(config["intent_weights"], sorted(config["intent_weights"]), "intent_weights")
    _row_sums_to_one(config["first_channel_weights"], CHANNEL_ORDER, "first_channel_weights")
    for channel in CHANNEL_ORDER:
        _row_sums_to_one(
            config["next_channel_if_unresolved"][channel],
            NEXT_STEPS,
            f"next_channel_if_unresolved.{channel}",
        )
        spec = config["ttfr_lognormal_minutes"][channel]
        if "mu" not in spec or "sigma" not in spec:
            raise ValueError(f"ttfr_lognormal_minutes.{channel} needs mu and sigma")
    for group, channels in config["resolution_probability"].items():
        for channel in CHANNEL_ORDER:
            probability = float(channels[channel])
            if not 0.0 <= probability <= 1.0:
                raise ValueError(f"resolution probability out of range for {group}.{channel}")
    low, high = config["ttfr_clip_minutes"]
    if not (0 <= float(low) < float(high)):
        raise ValueError("ttfr clip bounds are invalid")
    low, high = config["retry_gap_clip_hours"]
    if not (0 <= float(low) < float(high)):
        raise ValueError("retry gap clip bounds are invalid")


def intent_group_lookup(config: dict) -> dict[str, str]:
    lookup = {}
    for name, members in config["intent_groups"].items():
        for intent in members:
            lookup[intent] = name
    return lookup


def _clip_lognormal(rng: np.random.Generator, mu: float, sigma: float, bounds: list) -> float:
    draw = float(rng.lognormal(float(mu), float(sigma)))
    return float(min(max(draw, float(bounds[0])), float(bounds[1])))


def generate_events(config: dict, taxonomy: pd.DataFrame) -> pd.DataFrame:
    """Return one row per synthetic contact.

    Random draws for each journey, in order: intent, first channel, start
    offset, then for each contact the response delay, the resolve draw, and
    (only if the journey continues) the next step and the gap.
    """
    validate_config(config, taxonomy)
    rng = np.random.default_rng(int(config["seed"]))
    categories = dict(zip(taxonomy["intent"], taxonomy["category"]))
    groups = intent_group_lookup(config)
    intent_names = sorted(config["intent_weights"])
    intent_p = _weights(config["intent_weights"], intent_names, "intent_weights")
    first_p = _row_sums_to_one(config["first_channel_weights"], CHANNEL_ORDER, "first_channel_weights")
    next_p = {
        channel: _row_sums_to_one(
            config["next_channel_if_unresolved"][channel],
            NEXT_STEPS,
            f"next_channel_if_unresolved.{channel}",
        )
        for channel in CHANNEL_ORDER
    }
    start = _as_utc_naive(config["start"])
    horizon_minutes = float(config["horizon_days"]) * 24 * 60
    max_contacts = int(config["max_contacts"])
    decay = float(config["attempt_decay"])
    slow_after = float(config["slow_response_minutes"])
    slow_factor = float(config["slow_response_factor"])
    cap = float(config["resolution_probability_cap"])
    gap_spec = config["retry_gap_lognormal_hours"]

    rows: list[dict] = []
    for number in range(1, int(config["n_journeys"]) + 1):
        intent = str(rng.choice(intent_names, p=intent_p))
        group = groups[intent]
        channel = str(rng.choice(CHANNEL_ORDER, p=first_p))
        moment = start + timedelta(minutes=float(rng.uniform(0, horizon_minutes)))
        journey_id = f"J{number:05d}"
        customer_id = f"C{number:05d}"
        pending: list[dict] = []
        end_reason = "max_contacts"
        contact_index = 1
        while True:
            ttfr_spec = config["ttfr_lognormal_minutes"][channel]
            ttfr = _clip_lognormal(
                rng, ttfr_spec["mu"], ttfr_spec["sigma"], config["ttfr_clip_minutes"]
            )
            slow = ttfr > slow_after
            base = float(config["resolution_probability"][group][channel])
            probability = contact_resolution_probability(
                base, contact_index, slow, decay, slow_factor, cap
            )
            resolved = bool(rng.random() < probability)
            response_at = moment + timedelta(minutes=ttfr)
            pending.append(
                {
                    "data_origin": "SYNTHETIC",
                    "event_id": f"{journey_id}-{contact_index:02d}",
                    "journey_id": journey_id,
                    "customer_id": customer_id,
                    "intent": intent,
                    "category": categories[intent],
                    "intent_group": group,
                    "channel": channel,
                    "contact_index": contact_index,
                    "event_ts": _fmt(moment),
                    "response_ts": _fmt(response_at),
                    "ttfr_minutes": float(f"{ttfr:.6f}"),
                    "base_resolution_probability": float(f"{base:.6f}"),
                    "slow_response_applied": int(slow),
                    "resolution_probability_used": float(f"{probability:.6f}"),
                    "resolved": resolved,
                }
            )
            if resolved:
                end_reason = "resolved"
                break
            if contact_index >= max_contacts:
                end_reason = "max_contacts"
                break
            step = str(rng.choice(NEXT_STEPS, p=next_p[channel]))
            if step == "abandon":
                end_reason = "chose_abandon"
                break
            gap = _clip_lognormal(
                rng, gap_spec["mu"], gap_spec["sigma"], config["retry_gap_clip_hours"]
            )
            moment = response_at + timedelta(hours=gap)
            channel = step
            contact_index += 1
        for row in pending:
            row["journey_end_reason"] = end_reason
            rows.append(row)

    events = pd.DataFrame(rows, columns=EVENT_COLUMNS)
    return events
