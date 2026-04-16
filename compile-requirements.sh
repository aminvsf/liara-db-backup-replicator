#!/usr/bin/env bash
set -euo pipefail

for file in requirements.in dev-requirements.in; do
  pip-compile "$file" --upgrade --generate-hashes --allow-unsafe
done
