from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FLASK_API_DIR = ROOT / "flask_api"
sys.path.insert(0, str(FLASK_API_DIR))

from app import app  # noqa: E402
from versioning import ensure_snapshot, load_manifest  # noqa: E402


def main() -> int:
    entry = ensure_snapshot(app)
    manifest = load_manifest()
    print(f"latest={manifest.get('latest')}")
    print(f"version={entry['version']}")
    print(f"hash={entry['spec_hash']}")
    print(f"summary={entry['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
