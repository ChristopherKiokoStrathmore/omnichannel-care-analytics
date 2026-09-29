from pathlib import Path

import pandas as pd

from care_analytics.charts import friction_matrix, write_friction_heatmap, write_sankey
from tests.test_journeys_kpis import fixture_events
from care_analytics.journeys import build_journeys, sankey_links


def test_charts_are_labelled_synthetic(tmp_path: Path):
    events = fixture_events()
    journeys = build_journeys(events)
    sankey_path = tmp_path / "SYNTHETIC_sankey.html"
    heat_path = tmp_path / "SYNTHETIC_friction_heatmap.html"
    write_sankey(sankey_links(journeys), sankey_path)
    matrix = friction_matrix(events)
    write_friction_heatmap(matrix, heat_path)
    for path in (sankey_path, heat_path):
        text = path.read_text(encoding="utf-8")
        assert "SYNTHETIC" in text
        assert "Not observed customer behaviour" in text
    ussd_check = matrix[
        (matrix["intent"] == "check_usage") & (matrix["channel"] == "ussd")
    ].iloc[0]
    assert int(ussd_check["contacts"]) == 3
    assert int(ussd_check["resolved_contacts"]) == 2
    assert ussd_check["friction"] == 1 - (2 / 3)
    assert set(matrix["data_origin"]) == {"SYNTHETIC"}
