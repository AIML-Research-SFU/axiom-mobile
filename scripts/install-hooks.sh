#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

chmod +x scripts/check_no_raw_images.sh
chmod +x .githooks/pre-commit
git config core.hooksPath .githooks

echo "Installed hooks. Current core.hooksPath=$(git config core.hooksPath)"
echo "Pre-commit guard enabled for raw screenshot/image files."

