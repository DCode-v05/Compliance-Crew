"""Initialise (or reset) the SQLite database used for the audit trail.

Run before the first pipeline execution, or any time you want a clean DB."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db import DB_PATH, init_db, reset_db  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the ComplianceCrew database.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete the existing compliance.db before recreating it.",
    )
    args = parser.parse_args()

    if args.reset:
        reset_db()
        print(f"Reset {DB_PATH.absolute()} (all prior audit data deleted)")
    else:
        init_db()
        print(f"Initialised {DB_PATH.absolute()} (tables created if missing)")


if __name__ == "__main__":
    main()
