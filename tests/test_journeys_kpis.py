import pandas as pd

from care_analytics.journeys import build_journeys, directly_follows, sankey_links
from care_analytics.kpis import DEFINITIONS, compute_kpis


def _row(**overrides):
    base = {
        "data_origin": "SYNTHETIC",
        "event_id": "x",
        "journey_id": "J00001",
        "customer_id": "C00001",
        "intent": "check_usage",
        "category": "CONSUMPTION",
        "intent_group": "self_service_candidate",
        "channel": "ussd",
        "contact_index": 1,
        "event_ts": "2024-06-03T08:00:00Z",
        "response_ts": "2024-06-03T08:01:00Z",
        "ttfr_minutes": 1.0,
        "base_resolution_probability": 0.82,
        "slow_response_applied": 0,
        "resolution_probability_used": 0.82,
        "resolved": True,
        "journey_end_reason": "resolved",
    }
    base.update(overrides)
    return base


def fixture_events() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _row(),
            _row(
                event_id="J00002-01",
                journey_id="J00002",
                customer_id="C00002",
                intent="pay",
                category="PAYMENT",
                intent_group="assisted",
                channel="app",
                contact_index=1,
                event_ts="2024-06-03T09:00:00Z",
                response_ts="2024-06-03T09:05:00Z",
                ttfr_minutes=5.0,
                resolved=False,
                journey_end_reason="resolved",
            ),
            _row(
                event_id="J00002-02",
                journey_id="J00002",
                customer_id="C00002",
                intent="pay",
                category="PAYMENT",
                intent_group="assisted",
                channel="call",
                contact_index=2,
                event_ts="2024-06-03T12:00:00Z",
                response_ts="2024-06-03T12:04:00Z",
                ttfr_minutes=4.0,
                base_resolution_probability=0.78,
                resolution_probability_used=0.663,
                resolved=True,
                journey_end_reason="resolved",
            ),
            _row(
                event_id="J00003-01",
                journey_id="J00003",
                customer_id="C00003",
                intent="report_problem",
                category="COMPLAINTS",
                intent_group="complaint",
                channel="web",
                contact_index=1,
                event_ts="2024-06-04T09:00:00Z",
                response_ts="2024-06-04T09:02:00Z",
                ttfr_minutes=2.0,
                resolved=False,
                journey_end_reason="chose_abandon",
            ),
            _row(
                event_id="J00004-01",
                journey_id="J00004",
                customer_id="C00004",
                channel="ussd",
                contact_index=1,
                event_ts="2024-06-04T10:00:00Z",
                response_ts="2024-06-04T10:01:00Z",
                ttfr_minutes=1.5,
                resolved=False,
                journey_end_reason="resolved",
            ),
            _row(
                event_id="J00004-02",
                journey_id="J00004",
                customer_id="C00004",
                channel="ussd",
                contact_index=2,
                event_ts="2024-06-04T13:00:00Z",
                response_ts="2024-06-04T13:01:00Z",
                ttfr_minutes=1.25,
                resolved=True,
                journey_end_reason="resolved",
            ),
        ]
    )


def test_journey_flags_and_kpis_on_a_hand_built_log():
    events = fixture_events()
    journeys = build_journeys(events)
    assert list(journeys["journey_id"]) == ["J00001", "J00002", "J00003", "J00004"]
    by_id = journeys.set_index("journey_id")
    assert bool(by_id.loc["J00001", "resolved_on_first_contact"])
    assert not bool(by_id.loc["J00001", "repeat_contact"])
    assert not bool(by_id.loc["J00001", "digital_to_call"])
    assert bool(by_id.loc["J00002", "digital_to_call"])
    assert bool(by_id.loc["J00002", "channel_switch"])
    assert bool(by_id.loc["J00002", "repeat_contact"])
    assert by_id.loc["J00002", "channel_path"] == "app > call"
    assert by_id.loc["J00002", "resolving_channel"] == "call"
    assert not bool(by_id.loc["J00003", "resolved"])
    assert not bool(by_id.loc["J00003", "digital_to_call"])
    assert bool(by_id.loc["J00004", "repeat_contact"])
    assert not bool(by_id.loc["J00004", "channel_switch"])
    assert not bool(by_id.loc["J00004", "digital_to_call"])
    assert by_id.loc["J00001", "ttfr_minutes"] == 1.0
    assert by_id.loc["J00002", "ttfr_minutes"] == 5.0

    sizes = events.groupby("journey_id").size().sort_index()
    assert list(journeys["n_contacts"]) == list(sizes)

    flows = directly_follows(events)
    observed = {
        (row.from_activity, row.to_activity): int(row.n) for row in flows.itertuples()
    }
    assert observed[("ussd", "resolved")] == 2
    assert observed[("app", "call")] == 1
    assert observed[("call", "resolved")] == 1
    assert observed[("web", "abandoned")] == 1
    assert int(flows["n"].sum()) == len(events)

    links = sankey_links(journeys)
    assert int(links["n"].sum()) == 4

    config = {
        "seed": 1,
        "attempt_decay": 0.85,
        "slow_response_minutes": 30,
        "slow_response_factor": 0.75,
        "resolution_probability_cap": 0.98,
        "resolution_probability": {},
        "first_channel_weights": {},
        "digital_channels": ["ussd", "app", "web", "social"],
        "assisted_channel": "call",
    }
    kpis = compute_kpis(events, journeys, config)
    funnel = kpis["funnel"]
    assert funnel["journeys"] == 4
    assert funnel["repeat_contact"] == 2
    assert funnel["channel_switch"] == 1
    assert funnel["digital_to_call"] == 1
    assert funnel["digital_first"] == 4
    assert funnel["resolved"] == 3
    assert funnel["abandoned"] == 1
    assert funnel["resolved_on_first_contact"] == 1
    ussd = next(row for row in kpis["resolution_by_channel"] if row["channel"] == "ussd")
    assert ussd["contacts"] == 3
    assert ussd["resolved_contacts"] == 2
    app = next(row for row in kpis["ttfr_by_first_channel"] if row["channel"] == "app")
    assert app["median_minutes"] == 5.0
    assert app["journeys"] == 1
    for text in DEFINITIONS.values():
        assert "synthetic" in text.lower() or "Synthetic" in text or "config/synthetic.yaml" in text
