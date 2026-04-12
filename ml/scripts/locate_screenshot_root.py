#!/usr/bin/env python3
"""Locate the private screenshot root (screenshots_v1/) on macOS.

Searches common Google Drive sync locations, home-directory paths, and
environment variables. Prints the first valid path found or setup
instructions if nothing is discovered.

Usage:
    python3 ml/scripts/locate_screenshot_root.py
"""

from __future__ import annotations

import os
from pathlib import Path


def _candidate_paths() -> list[Path]:
    """Return ordered list of directories to probe for screenshots_v1/."""
    home = Path.home()
    candidates: list[Path] = []

    # 1. Explicit env var — highest priority
    env_root = os.environ.get("AXIOM_SCREENSHOT_ROOT")
    if env_root:
        candidates.append(Path(env_root))

    # 2. Google Drive for Desktop (Stream mode) — modern macOS location
    cloud_storage = home / "Library" / "CloudStorage"
    if cloud_storage.is_dir():
        for child in sorted(cloud_storage.iterdir()):
            if "google" in child.name.lower():
                candidates.append(child / "My Drive" / "screenshots_v1")
                candidates.append(child / "Shared drives" / "screenshots_v1")
                # Also search one level down for project folders
                candidates.append(child / "My Drive" / "AXIOM-Mobile" / "screenshots_v1")
                candidates.append(child / "My Drive" / "CMPT 416" / "screenshots_v1")

    # 3. Google Drive for Desktop (Mirror mode) — legacy location
    candidates.append(home / "Google Drive" / "My Drive" / "screenshots_v1")
    candidates.append(home / "Google Drive" / "screenshots_v1")

    # 4. Manual download locations
    candidates.append(home / "Desktop" / "screenshots_v1")
    candidates.append(home / "Downloads" / "screenshots_v1")
    candidates.append(home / "Documents" / "screenshots_v1")
    candidates.append(home / "Desktop" / "SFU" / "screenshots_v1")
    candidates.append(home / "Desktop" / "AXIOM-Mobile" / "screenshots_v1")

    # 5. Volumes (external drives, Google Drive File Stream legacy)
    volumes = Path("/Volumes")
    if volumes.is_dir():
        for vol in sorted(volumes.iterdir()):
            if "google" in vol.name.lower():
                candidates.append(vol / "My Drive" / "screenshots_v1")
                candidates.append(vol / "screenshots_v1")

    return candidates


def locate() -> Path | None:
    """Return the first valid screenshots_v1 directory, or None."""
    for path in _candidate_paths():
        resolved = path.resolve()
        if resolved.is_dir():
            # Quick sanity: should contain at least one image-like file
            has_images = any(
                f.suffix.lower() in (".png", ".jpg", ".jpeg", ".heic", ".webp")
                for f in resolved.iterdir()
                if f.is_file()
            )
            if has_images:
                return resolved
    return None


def main() -> int:
    print("Searching for screenshots_v1/ on this machine...\n")

    found = locate()
    if found:
        print(f"  FOUND: {found}")
        image_count = sum(
            1 for f in found.iterdir()
            if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".heic", ".webp")
        )
        print(f"  Images: {image_count}")
        print(f"\nTo use this root, either:")
        print(f"  export AXIOM_SCREENSHOT_ROOT='{found}'")
        print(f"  # or pass --image-root '{found}' to training/export scripts")
        return 0

    print("  NOT FOUND\n")
    print("The private screenshot folder was not discovered automatically.")
    print("See docs/PRIVATE_DATA_SETUP.md for setup instructions.\n")
    print("Probed locations:")
    for path in _candidate_paths():
        tag = "  exists (no images)" if path.is_dir() else "  missing"
        print(f"  {tag}: {path}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
