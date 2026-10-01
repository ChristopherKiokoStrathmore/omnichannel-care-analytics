"""Lock the committed outputs to the code that produced them."""

import json
from pathlib import Path

import pandas as pd
import pytest

from care_analytics.journeys import build_journeys
from care_analytics.kpis import compute_kpis
from care_analytics.report import render_headlines, render_readme_kpis, render_recommendations
from care_analytics.synthetic import generate_events, load_config, load_taxonomy

ROOT = Path(__file__).resolve().parents[1]


def _report() -> dict:
    return json.loads((ROOT / "reports" / "kpis.json").read_text(encoding="utf-8"))


def test_committed_events_match_the_generator():
    config = load_config(ROOT / "config" / "synthetic.yaml")
    taxonomy = load_taxonomy(ROOT / "data" / "derived" / "bitext_by_intent.csv")
    generated = generate_events(config, taxonomy)
    saved = pd.read_csv(ROOT / "data" / "derived" / "SYNTHETIC_multichannel_events.csv")
    pd.testing.assert_frame_equal(generated, saved, check_dtype=False)
    assert set(saved["data_origin"]) == {"SYNTHETIC"}


def test_committed_kpis_match_a_rebuild_from_the_event_log():
    events = pd.read_csv(ROOT / "data" / "derived" / "SYNTHETIC_multichannel_events.csv")
    report = _report()
    config = report["synthetic"]["config"]
    journeys = build_journeys(
        events,
        digital_channels=list(config["digital_channels"]),
        assisted_channel=config["assisted_channel"],
    )
    rebuilt = compute_kpis(events, journeys, config)
    assert rebuilt["funnel"] == report["synthetic"]["funnel"]
    assert rebuilt["sankey"] == report["synthetic"]["sankey"]
    assert rebuilt["directly_follows"] == report["synthetic"]["directly_follows"]
    for fresh, stored in zip(
        rebuilt["ttfr_by_first_channel"], report["synthetic"]["ttfr_by_first_channel"]
    ):
        assert fresh["channel"] == stored["channel"]
        assert fresh["journeys"] == stored["journeys"]
        assert fresh["median_minutes"] == pytest.approx(stored["median_minutes"])
        assert fresh["p90_minutes"] == pytest.approx(stored["p90_minutes"])
    assert sum(row["n"] for row in report["synthetic"]["sankey"]) == report["synthetic"]["funnel"]["journeys"]


def test_written_reports_match_the_renderer():
    report = _report()
    assert (ROOT / "reports" / "headlines.md").read_text(encoding="utf-8") == render_headlines(report)
    assert (ROOT / "docs" / "recommendations.md").read_text(encoding="utf-8") == render_recommendations(
        report
    )


def test_readme_kpis_match_committed_outputs():
    report = _report()
    headlines = (ROOT / "reports" / "headlines.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert headlines == render_headlines(report)
    assert render_readme_kpis(report).strip("\n") in readme
    assert "reports/headlines.md" in readme
    assert headlines.strip("\n") not in readme
    twitter_rows = report["public"]["twitter_sample"]["n_rows"]
    assert f"{twitter_rows} rows" in readme
    assert "a few dozen" not in readme.lower()


def test_committed_charts_are_labelled_synthetic():
    for name in ("SYNTHETIC_sankey.html", "SYNTHETIC_friction_heatmap.html"):
        text = (ROOT / "reports" / "charts" / name).read_text(encoding="utf-8")
        assert "SYNTHETIC" in text
        assert "Not observed customer behaviour" in text
    for name in ("SYNTHETIC_sankey.png", "SYNTHETIC_friction_heatmap.png"):
        data = (ROOT / "reports" / "charts" / name).read_bytes()
        assert data.startswith(b"\x89PNG\r\n\x1a\n")
        assert b"SYNTHETIC DATA" in data


def test_committed_outputs_do_not_contain_raw_utterances():
    needles = (
        "tapped notification under the keyboard",
        "i do not recogniae",
    )
    roots = [
        ROOT / "data" / "derived",
        ROOT / "reports",
        ROOT / "docs",
        ROOT / "README.md",
    ]
    for root in roots:
        paths = [root] if root.is_file() else [path for path in root.rglob("*") if path.is_file()]
        for path in paths:
            if path.suffix not in {".md", ".json", ".csv", ".html", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for needle in needles:
                assert needle not in text, f"{needle} found in {path}"


def test_prose_does_not_present_synthetic_rates_as_field_evidence():
    blob = "\n".join(
        [
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "docs" / "recommendations.md").read_text(encoding="utf-8"),
            (ROOT / "reports" / "headlines.md").read_text(encoding="utf-8"),
        ]
    ).lower()
    for banned in (
        "safaricom customers",
        "airtel customers",
        "production data",
        "real-world rate",
        "we observed customers",
    ):
        assert banned not in blob
    assert "no synthetic rate in this repository is a real-world measurement" in blob
    assert "synthetic" in (ROOT / "docs" / "recommendations.md").read_text(encoding="utf-8").lower()
