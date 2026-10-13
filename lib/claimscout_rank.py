#!/usr/bin/env python3
"""
ClaimScout ranker — rank already-filtered candidates with an open-weight model.

The scanner (lib/claimscout.py) is deliberately model-free: small open-weight
models cannot reliably drive a multi-turn tool-calling loop, so the fetching and
filtering is plain code. This ranker takes that clean shortlist and asks an
open-weight model to order it by "how good a first contribution is this for
someone with my skills" — a single, stateless call, no tool loop, which is
exactly the workload small models handle well.

Default provider is NVIDIA's OpenAI-compatible endpoint running open-weight
models (llama-3.2, nemotron). Any OpenAI-compatible endpoint works — set
CLAIMSCOUT_BASE_URL / CLAIMSCOUT_API_KEY / CLAIMSCOUT_MODEL to point elsewhere
(a local Ollama/vLLM server, for instance).

Usage:
    echo '<json from claimscout scan --json>' | claimscout-rank \
        [--profile "rust,anchor,security"]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "meta/llama-3.2-11b-vision-instruct"

SYSTEM = """You rank open-source issues for a developer looking for a good first \
contribution. You are given a JSON list of already-filtered, unclaimed issues. \
For each, judge how good a contribution target it is: prefer bounded bugs with \
clear reproduction over vague feature requests; prefer issues whose labels match \
the contributor's skills; penalise anything that needs external accounts or \
long setup. Return ONLY a JSON array, most promising first, each element:
{"number": <int>, "score": <0-100>, "reason": "<<=140 chars, concrete>"}."""


def build_prompt(candidates: list[dict], profile: str | None) -> str:
    slim = [
        {
            "number": c["number"],
            "repo": c["repo"],
            "title": c["title"],
            "labels": c["labels"],
            "comments": c["comments"],
        }
        for c in candidates
    ]
    profile_line = f"Contributor skills: {profile}." if profile else (
        "No skill profile given; judge general approachability."
    )
    return (
        f"{profile_line}\n\n"
        f"Issues (JSON):\n{json.dumps(slim)}\n\n"
        "Return the ranked JSON array, most promising first."
    )


def call_model(prompt: str, base_url: str, api_key: str, model: str) -> str:
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            # Force a single JSON object back — no tool calls, no multi-turn loop.
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` / ``` ... ``` fences a model wraps its answer in."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # drop the opening fence line (``` or ```json)
        lines = lines[1:]
        # drop the closing fence if present
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def parse_ranking(text: str) -> list[dict]:
    """Tolerate a model that wraps the array in an object, fences it, or adds prose."""
    text = strip_code_fences(text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("["), text.rfind("]")
        if start == -1 or end == -1:
            return []
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return []
    if isinstance(parsed, dict):
        for v in parsed.values():
            if isinstance(v, list):
                parsed = v
                break
        else:
            return []
    return [r for r in parsed if isinstance(r, dict) and "number" in r]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="claimscout-rank")
    p.add_argument("--profile", help="comma-separated skills, e.g. 'rust,anchor'")
    p.add_argument(
        "--base-url",
        default=os.environ.get("CLAIMSCOUT_BASE_URL", DEFAULT_BASE_URL),
    )
    p.add_argument(
        "--model", default=os.environ.get("CLAIMSCOUT_MODEL", DEFAULT_MODEL)
    )
    args = p.parse_args(argv)

    api_key = os.environ.get("CLAIMSCOUT_API_KEY") or os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        print(
            "error: set CLAIMSCOUT_API_KEY (or NVIDIA_API_KEY) to use the ranker",
            file=sys.stderr,
        )
        return 1

    raw = sys.stdin.read()
    try:
        candidates = json.loads(raw)
    except json.JSONDecodeError:
        print("error: stdin is not valid JSON (pipe `claimscout scan --json`)",
              file=sys.stderr)
        return 1
    if not candidates:
        print("No candidates to rank.")
        return 0

    prompt = build_prompt(candidates, args.profile)
    text = ""
    try:
        text = call_model(prompt, args.base_url, api_key, args.model)
        ranking = parse_ranking(text)
        # Small open-weight models sometimes answer with prose or code instead of
        # JSON. One strict retry with an explicit "no prose" instruction recovers
        # most of these without a multi-turn loop (which they can't sustain).
        if not ranking:
            retry_prompt = (
                prompt
                + "\n\nYour previous reply was not valid JSON. Reply with ONLY the "
                "JSON array — no prose, no markdown fences, no code. Start with [ "
                "and end with ]."
            )
            text = call_model(retry_prompt, args.base_url, api_key, args.model)
            ranking = parse_ranking(text)
    except (urllib.error.URLError, TimeoutError, KeyError) as e:
        print(f"error: ranker call failed: {e}", file=sys.stderr)
        return 1

    if not ranking:
        print("error: model returned no parseable ranking after retry", file=sys.stderr)
        print(text[:500], file=sys.stderr)
        return 1

    by_number = {c["number"]: c for c in candidates}
    for rank, r in enumerate(ranking, 1):
        c = by_number.get(r.get("number"))
        if not c:
            continue
        score = r.get("score", "?")
        reason = r.get("reason", "")
        print(f"{rank:>2}. #{c['number']:<5} [{score}] {c['repo']}")
        print(f"      {c['title'][:70]}")
        print(f"      {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
