#!/usr/bin/env python3
"""Stage app-exported benchmark artifacts into a device-profile session directory.

Copies CSV + _meta.json from the app's Documents directory (or a custom
source) into a properly named session folder under results/device_profiles/.

Usage:
    # From simulator app container (auto-discovers Documents):
    python3 ml/scripts/stage_device_profile_session.py \
        --source-dir /path/to/simulator/Documents \
        --device-name "iphone17pro-sim"

    # Auto-detect from a booted simulator's app container:
    python3 ml/scripts/stage_device_profile_session.py \
        --from-simulator \
        --device-name "iphone17pro-sim"

    # From manually saved files:
    python3 ml/scripts/stage_device_profile_session.py \
        --source-dir ~/Desktop/exported_benchmark/ \
        --device-name "iphone14pro"
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent


def find_simulator_documents() -> Path | None:
    """Find the app's Documents directory in the booted simulator."""
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "get_app_container", "booted",
             "com.arieljtyson.AXIOMMobile", "data"],
            capture_output=True, text=True, check=True,
        )
        container = Path(result.stdout.strip())
        docs = container / "Documents"
        if docs.is_dir():
            return docs
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return None


def find_latest_session_files(source_dir: Path) -> tuple[Path, Path] | None:
    """Find the most recent CSV + _meta.json pair in source_dir."""
    csv_files = sorted(source_dir.glob("axiom_benchmark_*.csv"), reverse=True)
    for csv_path in csv_files:
        # Derive the expected meta path from the CSV filename
        stamp = csv_path.stem.replace("axiom_benchmark_", "")
        meta_path = source_dir / f"axiom_benchmark_{stamp}_meta.json"
        if meta_path.exists():
            return csv_path, meta_path

    return None


def derive_session_name(meta_path: Path, device_name: str) -> str:
    """Build a session directory name from metadata and device name."""
    raw = json.loads(meta_path.read_text(encoding="utf-8"))
    model_id = raw.get("model_id", "unknown")
    export_ts = raw.get("export_timestamp", "")

    # Try to extract a clean timestamp from the export_timestamp
    # Format: 2026-04-12T18:33:30Z or similar ISO 8601
    ts_clean = re.sub(r"[^0-9T]", "", export_ts)[:15]
    if not ts_clean:
        ts_clean = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    elif not ts_clean.endswith("Z"):
        ts_clean += "Z"

    # Sanitize device name for filesystem
    safe_device = re.sub(r"[^a-zA-Z0-9_-]", "_", device_name).lower()
    safe_model = re.sub(r"[^a-zA-Z0-9_-]", "_", model_id)

    return f"{safe_device}_{safe_model}_{ts_clean}"


def stage_session(
    csv_path: Path,
    meta_path: Path,
    device_name: str,
    profiles_dir: Path,
    notes_text: str | None = None,
) -> Path:
    """Copy session files into a properly named profile directory."""
    session_name = derive_session_name(meta_path, device_name)
    session_dir = profiles_dir / session_name
    session_dir.mkdir(parents=True, exist_ok=True)

    # Copy required artifacts
    shutil.copy2(csv_path, session_dir / csv_path.name)
    shutil.copy2(meta_path, session_dir / meta_path.name)

    # Write a notes.md if provided
    if notes_text:
        (session_dir / "notes.md").write_text(notes_text, encoding="utf-8")

    return session_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help="Directory containing exported CSV + _meta.json files.",
    )
    parser.add_argument(
        "--from-simulator",
        action="store_true",
        help="Auto-discover source from the booted simulator's app container.",
    )
    parser.add_argument(
        "--device-name",
        required=True,
        help="Device identifier for the session folder name (e.g., 'iphone17pro-sim').",
    )
    parser.add_argument(
        "--profiles-dir",
        type=Path,
        default=_PROJECT_ROOT / "results" / "device_profiles",
        help="Target directory for device profiles.",
    )
    parser.add_argument(
        "--notes",
        default=None,
        help="Optional notes text to include in notes.md.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Resolve source directory
    if args.from_simulator:
        source_dir = find_simulator_documents()
        if source_dir is None:
            print("ERROR: Could not find booted simulator app container.")
            print("Ensure the app is installed and a simulator is booted.")
            return 1
        print(f"Simulator Documents: {source_dir}")
    elif args.source_dir:
        source_dir = args.source_dir.resolve()
        if not source_dir.is_dir():
            print(f"ERROR: Source directory does not exist: {source_dir}")
            return 1
    else:
        print("ERROR: Provide either --source-dir or --from-simulator.")
        return 1

    # Find latest session files
    pair = find_latest_session_files(source_dir)
    if pair is None:
        print(f"ERROR: No matching CSV + _meta.json pair found in {source_dir}")
        print("Expected filenames like: axiom_benchmark_*.csv + axiom_benchmark_*_meta.json")
        return 1

    csv_path, meta_path = pair
    print(f"CSV:  {csv_path.name}")
    print(f"Meta: {meta_path.name}")

    # Read metadata for display
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    print(f"Model: {meta.get('model_id', 'unknown')}")
    print(f"Placeholder: {meta.get('is_placeholder', 'unknown')}")
    print(f"Records: {meta.get('record_count', 'unknown')}")

    # Stage
    profiles_dir = args.profiles_dir.resolve()
    session_dir = stage_session(
        csv_path, meta_path, args.device_name, profiles_dir, args.notes
    )

    print(f"\nStaged to: {session_dir}")
    print(f"Contents:")
    for f in sorted(session_dir.iterdir()):
        print(f"  {f.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
