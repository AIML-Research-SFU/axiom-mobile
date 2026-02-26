#!/usr/bin/env bash
set -euo pipefail

mode="${1:---staged}"

case "$mode" in
  --staged|--all) ;;
  *)
    echo "Usage: $0 [--staged|--all]"
    exit 2
    ;;
esac

pattern='(^data/raw/|^data/images/|\.png$|\.jpg$|\.jpeg$|\.heic$|\.webp$)'

if [[ "$mode" == "--all" ]]; then
  file_list="$(git ls-files)"
else
  file_list="$(git diff --cached --name-only --diff-filter=ACMR)"
fi

if [[ -z "${file_list}" ]]; then
  echo "Image guard passed (${mode#--}): no files to check."
  exit 0
fi

if command -v rg >/dev/null 2>&1; then
  matches="$(printf '%s\n' "$file_list" | rg -i -N "$pattern" || true)"
else
  matches="$(printf '%s\n' "$file_list" | grep -E -i "$pattern" || true)"
fi

if [[ -n "$matches" ]]; then
  cat <<EOF
ERROR: Raw screenshots/images are not allowed in git.
Remove these files from the commit (or repo) and keep screenshots in private storage:
$matches
EOF
  exit 1
fi

echo "Image guard passed (${mode#--})."

