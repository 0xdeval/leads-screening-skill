#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
canonical="$repo_root/candidate-screening"
plugin_copy="$repo_root/plugins/candidate-screening/skills/candidate-screening"

diff -qr \
  --exclude="evals" \
  --exclude="tests" \
  --exclude="__pycache__" \
  "$canonical" \
  "$plugin_copy"

printf 'Plugin skill copy matches canonical skill.\n'
