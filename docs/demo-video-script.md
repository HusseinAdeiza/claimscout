# ClaimScout — 85-Second Hackathon Demo Script

Framework: 6-beat persona arc (Maya/Senar style). Runtime target: **85s**.

**Persona:** "Kai," a junior dev trying to land a first merged PR for a hackathon/bounty.
Late night, laptop, issue tracker open. All screen recordings are real ClaimScout runs.

---

## Beat 1 — Persona & Friction (0:00–0:15)

**Visuals:** Close on Kai, lit by laptop, tired. Cut to screen: a GitHub issue tracker
scrolling endlessly. Zoom on an issue — the assignee avatar appears: *taken*. Quick montage
of three more dead ends: "assigned," "23 comments," an `epic` label. Kai leans back,
exhales. Text slam: **"Sound familiar?"**

**VO:** "This is Kai. She's trying to land her first merged pull request. She's got the
skills. What she doesn't have — is time. Forty open issues. Half are already claimed. The
rest are epics, or ghosts nobody's touched in a year. She could spend all night digging…
or she could ask: what if a tool just told her which ones are actually hers to take?"

**Audio:** tense lo-fi pulse ~90 BPM. Each dead issue = dull thud. Text slam = bass hit.

**Capture:** issue-list scroll; cursor on an assignee avatar; 3 dead-issue tabs; 3 reaction
shots (tired, lean-back, exhale).

---

## Beat 2 — Reveal (0:15–0:25)

**Visuals:** Hard cut to clean terminal. ClaimScout logo types on. One line types:
`claimscout scan --repos 0dotxyz/marginfi-v2`. Text overlay: **"ClaimScout. Only the
issues worth your time."**

**VO:** "This is ClaimScout. Point it at the repos you care about, and it hands back only
the issues that are actually yours to take — unclaimed, bounded, and real."

**Audio:** pulse drops, single confident synth note. Keyboard clack, soft chime.

**Capture:** clean terminal, type the scan command for real. Logo card as overlay.

---

## Beat 3 — Live Demo & Aha (0:25–0:50)

**Visuals:** Command runs, output streams. **Callout 1 (zoom+circle):** `#705 unclaimed,
0 comments [bug]` — *"unclaimed · 0 comments · labeled bug."* **Callout 2:** `#682 [good
first issue]` — *"bounded, startable."* **The Aha:** pipe into ranker — `| claimscout-rank
--profile "rust,anchor"`. Ranked list appears, #682 floats to #1. Kai smiles. Text:
**"Number one. Hers to take."**

**VO:** "Watch. It scans the repo and strips out everything that's a dead end — assigned
work, bots, epics. What's left is real. Look here: issue 705, unclaimed, zero comments,
labeled bug. And 682 — good first issue. Now the open-weight model ranks them against her
skills… and 682 floats straight to the top. That's the one she takes."

**Audio:** arpeggio builds. Result lines = tick. Callouts = whoosh. #682 → #1 = rising
chime + warm pad.

**Capture:** `claimscout scan` full output; zoomed crops of #705/#682 lines; the full
`scan --json | claimscout-rank` pipe with #682 at #1. 2 annotations in edit.

---

## Beat 4 — Architecture (0:50–1:05)

**Visuals:** Clean 3-box diagram, animated draw-on: **GitHub API → ClaimScout (deterministic
filter) → Open-weight model (single-call rank)**. Zoom middle box: *"No model in the loop."*
Zoom right box: *"meta/llama-3.2, one stateless call."* Caption: *"No tool-loop. No
hallucinated calls. No per-fetch API bill."*

**VO:** "Under the hood, the fetching and filtering is plain, deterministic code — no model
in the loop, because small models can't sustain one. The model does exactly one thing: a
single call that ranks an already-clean shortlist. That's why it's cheap enough to actually
run — and why it doesn't hallucinate."

**Audio:** minimal tech beat. Box draws = synth blip. Zooms = whoosh.

**Capture:** 3-box diagram (Figma/Excalidraw), PNG or short MP4 with draw-on.

---

## Beat 5 — Feature Montage (1:05–1:15)

**Visuals:** Rapid ~2s cuts, imperative captions: **"Scan any repo."** → **"Rank on your
skills."** → **"Pipe it anywhere."** (`--json | jq`). Three-up split screen.

**VO:** "Scan any repo. Rank it on your skills. Pipe the JSON anywhere you want."

**Audio:** driving ~120 BPM. Hard-cut whoosh per caption.

**Capture:** scan a different repo; rank with a different profile; `--json | jq '.[].number'`.

---

## Beat 6 — Resolution & Slogan (1:15–1:25)

**Visuals:** Back to Kai, same desk, same late night — now typing a PR description, calm,
in flow. Screen: **her real pull request** — genvm-manager **#48** (+82/−1) showing the
**green "Merged"** badge (genuine, not mocked). She grins. Cut to black. Logo card:
**ClaimScout**. Tagline types on: **"Claim what's yours."**

**VO:** "Same night. Same Kai. But now she's not digging — she's shipping. Her PR is
open… and merged. ClaimScout. Claim what's yours."

**Audio:** warm triumphant final chord, tail off. Merge badge = chime + confetti pop.

**Capture:** screen-record the real merged PR #48
(`https://github.com/genlayerlabs/genvm-manager/pull/48`); Kai typing + grin; logo + tagline.

---

## Consolidated capture list

**Screen (real runs, dark theme):** issue-list scroll + assignee avatar + 3 dead tabs;
`claimscout scan` output; zoomed #705/#682 crops; `scan --json | claimscout-rank` (#682 #1);
different repo; different profile; `--json | jq`.
**Talent:** tired; exhale; the aha-smile; calm typing; grin.
**Graphics:** 2 callouts; 3-box architecture diagram; logo + tagline card.
**Edit:** cut on the beat; hold the two callouts and the #682→#1 moment a beat long.
