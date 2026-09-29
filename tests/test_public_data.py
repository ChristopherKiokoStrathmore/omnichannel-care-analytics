from pathlib import Path

from care_analytics.public_data import summarize_bitext, summarize_twitter_sample

FIXTURES = Path(__file__).parent / "fixtures"


def test_bitext_mini_counts_and_tags():
    summary = summarize_bitext(FIXTURES / "bitext_mini.csv")
    assert summary["meta"]["n_examples"] == 4
    assert summary["meta"]["n_intents"] == 2
    assert summary["meta"]["n_categories"] == 2
    assert summary["meta"]["examples_per_intent_min"] == 2
    assert summary["meta"]["examples_per_intent_max"] == 2
    tags = {row.tag: row.n_examples for row in summary["by_tag"].itertuples()}
    assert tags["B"] == 4
    assert tags["Q"] == 3
    assert tags["Z"] == 2
    assert tags["I"] == 1
    assert tags["L"] == 1
    assert tags["P"] == 1
    assert tags["C"] == 1
    assert tags["W"] == 0


def test_twitter_mini_reply_delay_is_60_minutes():
    summary = summarize_twitter_sample(FIXTURES / "twitter_mini.csv")
    assert summary["n_rows"] == 3
    assert summary["n_inbound"] == 2
    assert summary["n_outbound"] == 1
    assert summary["in_sample_reply_links"] == 1
    assert summary["inbound_to_company_reply_pairs"] == 1
    assert summary["reply_delay_minutes_median"] == 60
    assert summary["telecom_or_cable_tweets"] == 1
    assert summary["telecom_or_cable_accounts"][0]["author_id"] == "O2"
    assert summary["telecom_or_cable_accounts"][0]["kind"] == "mobile"
    assert "hello" not in str(summary)
