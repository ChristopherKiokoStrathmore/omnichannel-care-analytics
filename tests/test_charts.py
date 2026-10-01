from pathlib import Path

from care_analytics.charts import (
    friction_matrix,
    friction_png_figure,
    sankey_png_figure,
    write_friction_heatmap,
    write_friction_heatmap_png,
    write_sankey,
    write_sankey_png,
)
from tests.test_journeys_kpis import fixture_events
from care_analytics.journeys import build_journeys, sankey_links


def _png_is_labelled(path: Path) -> None:
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert b"SYNTHETIC DATA" in data


def test_charts_are_labelled_synthetic(tmp_path: Path):
    events = fixture_events()
    journeys = build_journeys(events)
    links = sankey_links(journeys)
    sankey_path = tmp_path / "SYNTHETIC_sankey.html"
    heat_path = tmp_path / "SYNTHETIC_friction_heatmap.html"
    sankey_png = tmp_path / "SYNTHETIC_sankey.png"
    heat_png = tmp_path / "SYNTHETIC_friction_heatmap.png"
    write_sankey(links, sankey_path)
    matrix = friction_matrix(events)
    write_friction_heatmap(matrix, heat_path)
    write_sankey_png(links, sankey_png)
    write_friction_heatmap_png(matrix, heat_png)
    for path in (sankey_path, heat_path):
        text = path.read_text(encoding="utf-8")
        assert "SYNTHETIC" in text
        assert "Not observed customer behaviour" in text
    for path in (sankey_png, heat_png):
        _png_is_labelled(path)
    sankey_fig = sankey_png_figure(links)
    heat_fig = friction_png_figure(matrix)
    assert "SYNTHETIC DATA" in sankey_fig.axes[0].get_title(loc="left")
    assert "SYNTHETIC DATA" in heat_fig.axes[0].get_title(loc="left")
    sankey_fig.clf()
    heat_fig.clf()
    ussd_check = matrix[
        (matrix["intent"] == "check_usage") & (matrix["channel"] == "ussd")
    ].iloc[0]
    assert int(ussd_check["contacts"]) == 3
    assert int(ussd_check["resolved_contacts"]) == 2
    assert ussd_check["friction"] == 1 - (2 / 3)
    assert set(matrix["data_origin"]) == {"SYNTHETIC"}
