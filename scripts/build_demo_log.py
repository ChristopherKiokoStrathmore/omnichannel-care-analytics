"""Write web/data/demo-log.json from the committed synthetic journeys and Bitext tables."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from care_analytics.demo_log import write_demo_log  # noqa: E402
from care_analytics.pipeline import ROOT  # noqa: E402


def main() -> None:
    path = write_demo_log(ROOT)
    print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
