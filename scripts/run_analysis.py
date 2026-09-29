#!/usr/bin/env python3
"""Regenerate the synthetic log, KPIs, charts, and written figures."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from care_analytics.pipeline import run  # noqa: E402


if __name__ == "__main__":
    run()
