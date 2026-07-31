#!/usr/bin/env python3
"""Generate the synthetic HTML pages the v0.5.0 Safari scenarios point at.

Ground truth lives in generate_exact_scenarios.py's WEB_VARIANTS (single
source of truth) -- this script only renders that data to static HTML
files, deterministically, so re-running it always produces byte-identical
pages. No manual content authoring; no LLM; nothing to review.

Usage:
    python3 scripts/generate_synthetic_web_pages.py
    python3 scripts/generate_synthetic_web_pages.py --output-dir /tmp/pages
"""
from __future__ import annotations

import argparse
from pathlib import Path

from generate_exact_scenarios import WEB_VARIANTS

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "synthetic_web_pages"

PAGE_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{var_id}</title>
</head>
<body style="font-family: -apple-system, sans-serif; padding: 32px; font-size: 28px; background: white;">
<h1 style="font-size: 40px; margin-bottom: 24px;">Order Total: ${order_total}</h1>
<p style="margin-bottom: 16px;">Item count: {item_count}</p>
<p>Status: {status}</p>
</body>
</html>
"""


def generate(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for var_id, order_total, item_count, status in WEB_VARIANTS:
        content = PAGE_TEMPLATE.format(
            var_id=var_id, order_total=order_total, item_count=item_count, status=status
        )
        path = output_dir / f"{var_id}.html"
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    written = generate(output_dir)

    print(f"Wrote {len(written)} synthetic pages to {output_dir}")
    for p in written:
        print(f"  {p.name}")


if __name__ == "__main__":
    main()
