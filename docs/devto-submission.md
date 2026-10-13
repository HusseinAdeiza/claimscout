<!--
SUBMISSION TEMPLATE — paste the body below into dev.to/new with these UI fields:
  Title: I built an open-weight-model agent that finds OSS issues worth your time
  Tags:  devchallenge, hf26challenge, opensource, ai, python
  (Do NOT use frontmatter with `published: false` — dev.to's Liquid parser chokes on it.
   Set the publish state in the UI instead.)
Delete every HTML comment before publishing.
-->

*This is a submission for the [Hacktoberfest Open-Source AI Challenge: Week 2: Side Hustle](https://dev.to/challenges/hacktoberfest-week2-2026-10-12)*

## What I Built

**ClaimScout** — a tool that tells you which open-source issues are actually worth your time.

Point it at the repos you care about and it hands back a short list of issues that are genuinely *yours to take*: unclaimed, low-traffic, bounded bugs — not assigned work, not bot chores, not architecture epics dressed up as quick wins. Then, if you want, an open-weight model ranks that shortlist against your skills so the best first contribution floats to the top.

Who would pay for this? Anyone trying to land merged pull requests — hackathon entrants, bug-bounty hunters, developers building a hiring portfolio. The problem is real and expensive: I lost *days* this month trawling issue trackers for work that turned out to be already claimed, vaguely scoped, or a months-long epic. ClaimScout turns that grep-and-pray into a one-line command.

It found the two bugs I actually shipped PRs for — so I'm user number one, with receipts.

👉 **Repo:** https://github.com/HusseinAdeiza/claimscout

## Demo

Here's a real run, not a mockup. Scanning `marginfi-v2`:

```
$ claimscout scan --repos 0dotxyz/marginfi-v2

0dotxyz/marginfi-v2: 10 claimable
  #705   unclaimed, 0 comment(s), created 2026-10-12  Same-asset-emode weight inversion
         labels: bug
  #682   unclaimed, 0 comment(s), created 2026-09-18  Allow empty-but-active integration balances to close
         labels: bug, good first issue
  #701   unclaimed, 0 comment(s), created 2026-10-10  Liquidation interplay with Order tagging
         labels: bug, low priority
```

Every line is a real, open, unassigned issue. Then the open-weight model ranks the shortlist against a Rust/Anchor skill profile:

```
$ claimscout scan --repos 0dotxyz/marginfi-v2 --max-comments 0 --json \
    | claimscout-rank --profile "rust,anchor,solana,security"

 1. #682   [90]  Allow empty-but-active integration balances to close
      Bounded bug with clear reproduction, matches contributor's skills
 2. #705   [80]  Same-asset-emode weight inversion
      Bounded bug, matches contributor's skills
```

Those two — #682 and #705 — are exactly the issues I went on to build and open PRs for. The ranker put them at the top on its own.

Run the whole thing yourself with `./examples/demo.sh`.

## Code

The core is ~250 lines of dependency-free Python (stdlib only, Python 3.9+). The scanner fetches and filters deterministically; the ranker is a separate, optional single-call step.

```python
# The filter that does the real work — an issue is reported only if it is ALL of:
#   an issue (not a PR), unassigned, low-traffic, not architecture, not bot-authored,
#   and actionable (bug / good-first-issue / help-wanted, or a recent unlabelled report)
for i in issues:
    if "pull_request" in i:            continue   # PRs are not claimable issues
    if i.get("assignees"):             continue   # already assigned
    if i["comments"] > max_comments:   continue   # contested / already discussed
    labels = [l["name"] for l in i.get("labels", [])]
    if any(ARCH_LABELS.search(l) for l in labels): continue  # epic/roadmap/spike
    if (i.get("user") or {}).get("login", "").endswith("[bot]"): continue
    ...
```

Full source, tests, and the ranker are in the repo.

## How I Built It

Two deliberate pieces:

**1. The fetch/filter loop is plain code — no model in it.** This is the whole design. I spent weeks watching small open-weight models try to drive multi-step agent loops, and they fail in a specific, ugly way: they call one tool five to eight times, give up, and the run still reports "ok." So ClaimScout never asks the model to fetch or filter. That's deterministic, testable Python. The model is only invoked at the very end, on an already-clean shortlist.

**2. The model does one stateless call.** When you enable ranking, ClaimScout sends the filtered shortlist to an open-weight model (`meta/llama-3.2-11b` via NVIDIA's OpenAI-compatible endpoint by default; any OpenAI-compatible server — local Ollama, vLLM — works) and asks for a ranked JSON array. No tool calls, no multi-turn loop, no agent harness. That's the exact workload a small model handles well.

It still needs guardrails. On the first live test the model answered with a Python code block instead of JSON, so the ranker strips code fences, extracts the array even when it's wrapped in prose, and issues one strict "JSON only" retry before giving up. There's a test for each of those failure modes — because I watched them happen.

19 stdlib `unittest` tests cover the triage filter, the messy-JSON parsing, and prompt construction.

## Why Does Open Innovation Matter?

This is the part that decides whether the "side hustle" actually works, and it comes down to cost.

ClaimScout is useful *per scan* and used *often* — you run it every time you sit down to find work. A version built on a hosted API would call a paid model on every fetch, and that per-run cost is more than a contributor chasing a $100 bounty would ever pay. The economics only close because the model is **open-weight and cheap to run**. The open model isn't a nice-to-have here; it's the reason the product can exist at a price anyone would pay.

Second, it keeps your data yours. ClaimScout reads your repos and your skill profile. Running inference on an open model you control means that never has to leave for a third party to log.

Third, openness is what let me build around the model's *real* limits instead of an idealized demo. Because the model is open and I could test it directly, I designed the deterministic/model split around how it actually behaves — the same lesson that makes the tool reliable is the lesson that closed, black-box APIs hide from you until production.

Where the open approach beat a closed one: a hosted model would have cost more per scan than the tool is worth, and would have forced my fetch logic behind an API I couldn't inspect. The open-weight model made a cheap, private, inspectable tool possible — which is the only version of this that works as a hustle.

## My Agent Session

ClaimScout was built *inside* an agent session — an AI coding agent driving the terminal, running the real toolchain, and iterating against live output. That's fitting, because the tool is itself about making agent-assisted open-source work reliable.

The session is where several of the design decisions were forced into the open rather than guessed at:

- **The model returned Python code instead of JSON** on the first live ranker test. I caught it, added code-fence stripping, prose-array extraction, and a strict retry — then wrote a test for each failure mode. A closed API would have hidden that until production.
- **The `amix` of 16 delayed narration clips collapsed to ~0s** because `amix` truncates to the shortest stream. Fixed by padding each clip with `apad` to the full timeline.
- **edge-tts silently dropped a line** (0-byte file) twice — fixed with retries, which is now why the voiceover generator re-attempts.

The honest thread through all of it: build around what the open model *actually* does, verified by running it, not what the demo says it should do. That's the same principle ClaimScout encodes in its architecture.

## My First User

Me — and it paid off concretely.

I built ClaimScout to solve my own Hacktoberfest problem, then used it the same week. It surfaced `marginfi-v2` #682 (a stuck integration-balance bug) and #705 (a same-asset e-mode weight inversion). I opened PRs for both. Earlier in the session, the same fetch-and-filter approach caught a cosmos-sdk PR getting closed by a maintainer — the kind of signal you only get if something is watching your PRs, not just the issue board.

The first "user" is a developer who'd been burned by claimed-and-gone issues, and what they asked for next was exactly what I built: *just tell me which ones are actually mine.*

## Prize Categories

- Best Use of Gemma (open-weight model at the core — genuinely, not bolted on)
