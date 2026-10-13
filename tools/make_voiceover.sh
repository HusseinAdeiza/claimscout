#!/usr/bin/env bash
# Generate the ClaimScout voiceover with edge-tts (Microsoft neural voices, free,
# no API key). Each line is a separate clip so the final audio can be placed at
# exact timestamps matching the video beats.
#
# Voice: en-US-GuyNeural — natural male, good for a brisk dev-demo read.
# Rate: +8% — hackathon demos are read fast but unhurried.
set -euo pipefail

VOICE="${VOICE:-en-US-GuyNeural}"
RATE="${RATE:-+8%}"
OUT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/voiceover"
mkdir -p "$OUT"

# line_number|text   (kept short so each clip is one breath)
LINES=(
  "01|This is Kai. She's trying to land her first merged pull request."
  "02|She's got the skills. What she doesn't have, is time."
  "03|Forty open issues. Half are already claimed. The rest are epics, or ghosts nobody's touched in a year."
  "04|What if a tool just told her which ones are actually hers to take?"
  "05|This is ClaimScout. Point it at the repos you care about, and it hands back only the issues that are actually yours to take."
  "06|Watch. It strips out everything that's a dead end. Assigned work, bots, epics."
  "07|Issue 705: unclaimed, zero comments, labeled bug."
  "08|And 682. Good first issue."
  "09|Now the open-weight model ranks them against her skills."
  "10|And 682 floats straight to the top. That's the one she takes."
  "11|Under the hood, the fetching and filtering is plain code. No model in the loop, because small models can't sustain one."
  "12|The model does one thing: a single call that ranks a clean shortlist. That's why it's cheap enough to run, and why it doesn't hallucinate."
  "13|Scan any repo. Rank it on your skills. Pipe the JSON anywhere you want."
  "14|Same night. Same Kai. But now she's not digging. She's shipping."
  "15|Her PR is open. And merged."
  "16|ClaimScout. Claim what's yours."
)

for entry in "${LINES[@]}"; do
  num="${entry%%|*}"
  text="${entry#*|}"
  printf '  [%s] %s\n' "$num" "$text"
  edge-tts --voice "$VOICE" --rate "$RATE" --text "$text" \
    --write-media "$OUT/vo_${num}.mp3" >/dev/null 2>&1
done

echo "done: $OUT ($(ls "$OUT" | wc -l) clips)"
