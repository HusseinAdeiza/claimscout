# ClaimScout

**Find open-source issues that are actually worth your time.**

Point ClaimScout at the repos you care about. It strips out the noise — already-assigned
work, bot-generated chores, architecture epics, contested threads — and hands back a short
list of bounded, startable issues. Optionally, an **open-weight model** ranks that shortlist
against your skills so the best first contribution floats to the top.

Built for contributors chasing merged PRs: hackathon entries, bounty programs, or a hiring
portfolio. The problem it solves is real and expensive: hours lost trawling issue trackers
for work that turns out to be taken, vague, or a months-long epic.

## Why it's built this way

ClaimScout is **deterministic in the fetch/filter loop and model-assisted only at the end.**

Small open-weight models cannot reliably drive a multi-turn tool-calling loop — they repeat
one tool five to eight times, give up, and the run still reports "ok." So the fetching and
filtering is plain, testable code. The model, when you enable it, does the one thing small
models do well: a single stateless call that ranks an already-clean shortlist. No tool loop,
no agent harness, no hallucinated API calls.

That split is also why it's cheap to run — see "Why open innovation matters" in the
[accompanying write-up](#). A closed-API version that called a hosted model on every fetch
would cost more per scan than a contributor would ever pay.

## Install

No dependencies beyond Python 3.9+ stdlib. Clone and run:

```bash
git clone https://github.com/HusseinAdeiza/claimscout
cd claimscout
chmod +x bin/claimscout bin/claimscout-rank
```

## Usage

### 1. Scan for claimable issues

```bash
export GH_TOKEN=ghp_...        # optional but raises rate limit 60 -> 5000/hr

./bin/claimscout scan --repos 0dotxyz/marginfi-v2,pushchain/push-chain-sdk
```

Or from a file:

```bash
./bin/claimscout scan --repos-file examples/repos.txt
```

Output:

```
0dotxyz/marginfi-v2: 10 claimable
  #705   unclaimed, 0 comment(s), created 2026-10-12 Same-asset-emode weight inversion
         labels: bug
         https://github.com/0dotxyz/marginfi-v2/issues/705
  #682   unclaimed, 0 comment(s), created 2026-09-18 Allow empty-but-active integration balances to close
         labels: bug, good first issue
         https://github.com/0dotxyz/marginfi-v2/issues/682
```

### 2. (Optional) Rank with an open-weight model

Pipe the JSON output into the ranker. It defaults to NVIDIA's OpenAI-compatible endpoint
running open-weight models; point it at any OpenAI-compatible server (local Ollama, vLLM):

```bash
export NVIDIA_API_KEY=nvapi-...        # or CLAIMSCOUT_API_KEY

./bin/claimscout scan --repos 0dotxyz/marginfi-v2 --max-comments 0 --json \
  | ./bin/claimscout-rank --profile "rust,anchor,solana,security"
```

```
 1. #682   [90] 0dotxyz/marginfi-v2
      Allow empty-but-active integration balances to close
      Bounded bug with clear reproduction, matches contributor's skills
 2. #705   [80] 0dotxyz/marginfi-v2
      Same-asset-emode weight inversion
      Bounded bug, matches contributor's skills
```

Configure the ranker via env vars:

| Var | Default | Purpose |
|---|---|---|
| `CLAIMSCOUT_API_KEY` | — | API key (falls back to `NVIDIA_API_KEY`) |
| `CLAIMSCOUT_BASE_URL` | `https://integrate.api.nvidia.com/v1` | any OpenAI-compatible endpoint |
| `CLAIMSCOUT_MODEL` | `meta/llama-3.2-11b-vision-instruct` | the open-weight model to rank with |

## What gets filtered out

An issue is reported only if it is **all** of:

- an **issue**, not a pull request
- **unassigned** (no assignees)
- **low-traffic** (`comments <= --max-comments`, default 1) — contested threads are usually taken
- **not architecture** — no `epic`/`roadmap`/`spike`/`feature`/`design` labels
- **not bot-authored** — skips dependabot, release bots
- **actionable** — carries a `bug`/`good first issue`/`help wanted`/`enhancement` label, or is
  a recent unlabelled report

Real work that isn't a good *first* contribution — pure refactors, crypto research, test
chores — is deliberately dropped so the signal stays high.

## JSON output

Every command speaks JSON for scripting:

```bash
./bin/claimscout scan --repos owner/repo --json | jq '.[].number'
```

## Tests

```bash
python3 tests/test_claimscout.py
```

19 tests, stdlib `unittest`, no dependencies. Covers the triage filter, the ranker's JSON
parsing against messy model output (fenced code, prose-wrapped arrays, garbage), and prompt
construction.

## License

MIT
