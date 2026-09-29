"""Summaries of the public files. No journey KPIs are computed here.

Bitext is a published training set. Bitext's own README calls it hybrid
synthetic. The Twitter file is a short publisher preview, not the Kaggle corpus.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

BITEXT_TAG_LETTERS = {
    "B": "basic syntactic structure",
    "I": "interrogative structure",
    "C": "coordinated syntactic structure",
    "N": "negation",
    "P": "politeness",
    "Q": "colloquial",
    "W": "offensive language",
    "K": "keyword mode",
    "E": "abbreviations",
    "Z": "errors and typos",
    "M": "morphological variation",
    "L": "semantic variation",
}

# Exact author_id values. Cable-ISP accounts are separated from mobile so the
# preview is not described as a telco sample.
TELECOM_AUTHORS = {
    "O2": "mobile",
    "sprintcare": "mobile",
    "VerizonSupport": "mobile",
    "TMobileHelp": "mobile",
    "ATT": "mobile",
    "VodafoneUK": "mobile",
    "comcastcares": "cable_isp",
    "Ask_Spectrum": "cable_isp",
}

TWITTER_TIME_FORMAT = "%a %b %d %H:%M:%S %z %Y"
BITEXT_COLUMNS = ["instruction", "intent", "category", "tags", "response"]
TWITTER_COLUMNS = [
    "tweet_id",
    "author_id",
    "inbound",
    "created_at",
    "text",
    "response_tweet_id",
    "in_response_to_tweet_id",
]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quantile(values: list[float], q: float) -> float | None:
    """Linear quantile, the same definition as numpy's method='linear'."""
    if not values:
        return None
    return float(np.quantile(np.asarray(values, dtype=float), q, method="linear"))


def summarize_bitext(csv_path: Path) -> dict:
    frame = pd.read_csv(csv_path)
    missing = set(BITEXT_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Bitext file missing columns: {sorted(missing)}")

    by_intent = (
        frame.groupby(["category", "intent"], as_index=False)
        .agg(
            n_examples=("instruction", "size"),
            median_instruction_chars=(
                "instruction",
                lambda series: float(
                    np.quantile(series.astype(str).str.len().to_numpy(), 0.5, method="linear")
                ),
            ),
            median_response_chars=(
                "response",
                lambda series: float(
                    np.quantile(series.astype(str).str.len().to_numpy(), 0.5, method="linear")
                ),
            ),
        )
        .sort_values(["category", "intent"])
        .reset_index(drop=True)
    )
    by_category = (
        frame.groupby("category", as_index=False)
        .agg(n_examples=("intent", "size"), n_intents=("intent", "nunique"))
        .sort_values("category")
        .reset_index(drop=True)
    )

    tags = frame["tags"].fillna("").astype(str)
    n_examples = int(len(frame))
    tag_rows = []
    for letter, meaning in BITEXT_TAG_LETTERS.items():
        count = int(tags.str.contains(letter, regex=False).sum())
        tag_rows.append(
            {
                "tag": letter,
                "meaning": meaning,
                "n_examples": count,
                "share_of_examples": (count / n_examples) if n_examples else 0.0,
            }
        )
    by_tag = pd.DataFrame(tag_rows)
    meta = {
        "source": "bitext/Bitext-telco-llm-chatbot-training-dataset",
        "origin": "public",
        "bitext_describes_dataset_as": "hybrid synthetic training set",
        "n_examples": n_examples,
        "n_intents": int(frame["intent"].nunique()),
        "n_categories": int(frame["category"].nunique()),
        "examples_per_intent_min": int(by_intent["n_examples"].min()) if n_examples else 0,
        "examples_per_intent_max": int(by_intent["n_examples"].max()) if n_examples else 0,
        "sha256": file_sha256(csv_path),
    }
    return {
        "by_intent": by_intent,
        "by_category": by_category,
        "by_tag": by_tag,
        "meta": meta,
    }


def summarize_twitter_sample(csv_path: Path) -> dict:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("Twitter sample has no data rows")
    missing = set(TWITTER_COLUMNS) - set(rows[0])
    if missing:
        raise ValueError(f"Twitter sample missing columns: {sorted(missing)}")

    by_id = {}
    for row in rows:
        if row["tweet_id"] in by_id:
            raise ValueError(f"Duplicate tweet_id in preview: {row['tweet_id']}")
        by_id[row["tweet_id"]] = row

    inbound = sum(1 for row in rows if row["inbound"] == "True")
    outbound = sum(1 for row in rows if row["inbound"] == "False")
    other_inbound_flag = len(rows) - inbound - outbound
    companies = Counter(row["author_id"] for row in rows if not str(row["author_id"]).isdigit())
    telecom_counts = []
    for author, kind in sorted(TELECOM_AUTHORS.items()):
        count = int(companies.get(author, 0))
        if count:
            telecom_counts.append({"author_id": author, "kind": kind, "tweets": count})

    links = 0
    delays: list[float] = []
    negative_delays = 0
    for row in rows:
        parent_id = (row.get("in_response_to_tweet_id") or "").strip()
        if not parent_id or parent_id not in by_id:
            continue
        links += 1
        parent = by_id[parent_id]
        if row["inbound"] == "False" and parent["inbound"] == "True":
            started = datetime.strptime(parent["created_at"], TWITTER_TIME_FORMAT)
            ended = datetime.strptime(row["created_at"], TWITTER_TIME_FORMAT)
            minutes = (ended - started).total_seconds() / 60.0
            if minutes < 0:
                negative_delays += 1
            delays.append(minutes)

    return {
        "source": "BERD record 4c9xb-k5q03 sample.csv__100lines.csv",
        "upstream": "Kaggle thoughtvector/customer-support-on-twitter",
        "origin": "public_preview",
        "full_corpus_downloaded": False,
        "full_corpus_reason": (
            "Unauthenticated requests to the Kaggle dataset page and the Kaggle "
            "download API returned HTTP 404. No Kaggle credentials were used. "
            "This file is the publisher preview only."
        ),
        "sha256": file_sha256(csv_path),
        "physical_newlines": csv_path.read_bytes().count(b"\n"),
        "n_rows": len(rows),
        "n_inbound": inbound,
        "n_outbound": outbound,
        "n_unparsed_inbound_flag": other_inbound_flag,
        "n_company_accounts": len(companies),
        "company_account_counts": [
            {"author_id": author, "tweets": int(count)}
            for author, count in companies.most_common()
        ],
        "telecom_or_cable_accounts": telecom_counts,
        "telecom_or_cable_tweets": int(sum(item["tweets"] for item in telecom_counts)),
        "in_sample_reply_links": links,
        "inbound_to_company_reply_pairs": len(delays),
        "negative_reply_delays": negative_delays,
        "reply_delay_minutes_median": quantile(delays, 0.5),
        "reply_delay_minutes_p90": quantile(delays, 0.9),
        "reply_delay_definition": (
            "For each outbound tweet in this preview whose in_response_to_tweet_id "
            "points at an inbound tweet that is also inside this same file, delay "
            "is the response created_at minus the parent created_at, in minutes. "
            "Pairs outside the preview are not counted. This is not a population "
            "time-to-first-response."
        ),
    }


def write_public_summaries(bitext_csv: Path, twitter_csv: Path, derived_dir: Path) -> dict:
    derived_dir.mkdir(parents=True, exist_ok=True)
    bitext = summarize_bitext(bitext_csv)
    twitter = summarize_twitter_sample(twitter_csv)
    bitext["by_intent"].to_csv(derived_dir / "bitext_by_intent.csv", index=False, lineterminator="\n")
    bitext["by_category"].to_csv(
        derived_dir / "bitext_by_category.csv", index=False, lineterminator="\n"
    )
    bitext["by_tag"].to_csv(derived_dir / "bitext_by_tag.csv", index=False, lineterminator="\n")
    (derived_dir / "bitext_meta.json").write_text(
        json.dumps(bitext["meta"], indent=2) + "\n", encoding="utf-8"
    )
    (derived_dir / "twitter_sample_summary.json").write_text(
        json.dumps(twitter, indent=2) + "\n", encoding="utf-8"
    )
    return {"bitext": bitext["meta"], "twitter_sample": twitter}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
