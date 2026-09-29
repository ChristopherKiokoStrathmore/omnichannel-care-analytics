from pathlib import Path

import pandas as pd
import pytest

from care_analytics.synthetic import (
    contact_resolution_probability,
    generate_events,
    load_config,
    load_taxonomy,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def mini_config():
    return load_config(FIXTURES / "synthetic_min.yaml")


@pytest.fixture()
def mini_taxonomy():
    return load_taxonomy(FIXTURES / "taxonomy_min.csv")


def test_resolution_probability_formula():
    assert contact_resolution_probability(0.8, 1, False, 0.85, 0.75, 0.98) == pytest.approx(0.8)
    assert contact_resolution_probability(0.8, 2, False, 0.85, 0.75, 0.98) == pytest.approx(0.68)
    assert contact_resolution_probability(0.8, 2, True, 0.85, 0.75, 0.98) == pytest.approx(0.51)
    assert contact_resolution_probability(0.99, 1, False, 0.85, 0.75, 0.98) == pytest.approx(0.98)


def test_generator_is_deterministic(mini_config, mini_taxonomy):
    first = generate_events(mini_config, mini_taxonomy)
    second = generate_events(mini_config, mini_taxonomy)
    pd.testing.assert_frame_equal(first, second)


def test_generator_invariants_and_recorded_probability(mini_config, mini_taxonomy):
    events = generate_events(mini_config, mini_taxonomy)
    assert set(events["data_origin"]) == {"SYNTHETIC"}
    assert events["journey_id"].nunique() == mini_config["n_journeys"]
    assert set(events["channel"]) <= set(mini_config["channels"])
    assert events["contact_index"].min() == 1
    for _, group in events.groupby("journey_id"):
        indexes = group["contact_index"].tolist()
        assert indexes == list(range(1, len(group) + 1))
        resolved = group.loc[group["resolved"]]
        assert len(resolved) <= 1
        if len(resolved) == 1:
            assert int(resolved["contact_index"].iloc[0]) == indexes[-1]
            assert group["journey_end_reason"].iloc[0] == "resolved"
        else:
            assert group["journey_end_reason"].iloc[0] in {"chose_abandon", "max_contacts"}
        assert group["journey_end_reason"].nunique() == 1
        assert (group["response_ts"] >= group["event_ts"]).all()
        if len(group) > 1:
            assert not bool(group.iloc[:-1]["resolved"].any())
    for row in events.itertuples():
        expected = contact_resolution_probability(
            row.base_resolution_probability,
            int(row.contact_index),
            bool(row.slow_response_applied),
            mini_config["attempt_decay"],
            mini_config["slow_response_factor"],
            mini_config["resolution_probability_cap"],
        )
        assert abs(row.resolution_probability_used - expected) < 5e-7


def test_config_must_cover_the_taxonomy(mini_config, mini_taxonomy):
    broken = dict(mini_config)
    broken["intent_weights"] = dict(mini_config["intent_weights"])
    del broken["intent_weights"]["pay"]
    with pytest.raises(ValueError, match="intent_weights"):
        generate_events(broken, mini_taxonomy)
