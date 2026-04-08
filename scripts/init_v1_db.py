from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from v1.db import DEFAULT_DB_PATH, init_db


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize Traffic Factory V1 SQLite database.")
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="SQLite database path",
    )
    args = parser.parse_args()

    db_path = Path(args.db_path)
    init_db(db_path)
    print(f"Initialized V1 database at: {db_path}")


if __name__ == "__main__":
    main()
