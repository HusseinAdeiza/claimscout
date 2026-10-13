#!/usr/bin/env bash
# End-to-end demo: scan the example repos, then rank the marginfi shortlist with
# an open-weight model. Run from the repo root:  ./examples/demo.sh
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> 1. Scanning example repos for claimable issues (deterministic, no model)"
"$here/bin/claimscout" scan --repos-file "$here/examples/repos.txt" --max-comments 1

echo
echo "==> 2. Ranking the marginfi shortlist with an open-weight model"
if [ -z "${NVIDIA_API_KEY:-}${CLAIMSCOUT_API_KEY:-}" ]; then
  echo "    (set NVIDIA_API_KEY or CLAIMSCOUT_API_KEY to run the ranker; skipping)"
  exit 0
fi
"$here/bin/claimscout" scan --repos 0dotxyz/marginfi-v2 --max-comments 0 --json \
  | "$here/bin/claimscout-rank" --profile "rust,anchor,solana,security"
