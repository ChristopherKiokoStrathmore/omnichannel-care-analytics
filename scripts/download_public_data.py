#!/usr/bin/env python3
"""Download the public inputs, check their hashes, and write small summaries.

The raw files land in data/raw/ and are gitignored. Committed outputs are the
derived tables under data/derived/.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from care_analytics.public_data import file_sha256, write_public_summaries  # noqa: E402

CHECKSUMS = ROOT / "data" / "checksums.json"
RAW = ROOT / "data" / "raw"
DERIVED = ROOT / "data" / "derived"


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    temporary = dest.with_suffix(dest.suffix + ".partial")
    request = urllib.request.Request(url, headers={"User-Agent": "omnichannel-care-analytics"})
    with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as handle:
        while True:
            chunk = response.read(1 << 20)
            if not chunk:
                break
            handle.write(chunk)
    temporary.replace(dest)


def _require(path: Path, expected_sha256: str, expected_bytes: int) -> None:
    actual_bytes = path.stat().st_size
    actual_sha = file_sha256(path)
    if actual_sha != expected_sha256 or actual_bytes != expected_bytes:
        raise SystemExit(
            f"Checksum failed for {path}. "
            f"sha256 {actual_sha} ({actual_bytes} bytes), "
            f"expected {expected_sha256} ({expected_bytes} bytes)."
        )


def main() -> None:
    spec = json.loads(CHECKSUMS.read_text(encoding="utf-8"))
    bitext = spec["bitext_telco"]
    twitter = spec["twitter_preview"]
    bitext_path = ROOT / bitext["local_path"]
    twitter_path = ROOT / twitter["local_path"]

    print(f"Downloading Bitext CSV to {bitext_path}")
    _download(bitext["url"], bitext_path)
    _require(bitext_path, bitext["sha256"], bitext["bytes"])

    print(f"Downloading Twitter preview to {twitter_path}")
    _download(twitter["url"], twitter_path)
    _require(twitter_path, twitter["sha256"], twitter["bytes"])
    md5 = hashlib.md5(twitter_path.read_bytes()).hexdigest()
    if md5 != twitter["md5"]:
        raise SystemExit(f"MD5 failed for Twitter preview: {md5}")

    summaries = write_public_summaries(bitext_path, twitter_path, DERIVED)
    print(json.dumps({"bitext": summaries["bitext"], "twitter_rows": summaries["twitter_sample"]["n_rows"]}, indent=2))


if __name__ == "__main__":
    main()
