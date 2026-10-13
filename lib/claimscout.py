#!/usr/bin/env python3
"""
ClaimScout — surface genuinely claimable open-source issues.

Point it at repos you care about; it fetches open issues, strips out the noise
(assigned work, bots, architecture epics, contested threads), and reports only
bounded, startable issues worth your time.

Deterministic by design: no model in the fetch/filter loop. Small open-weight
models cannot sustain a multi-turn tool-calling loop reliably (they repeat one
tool 5-8 times and give up), so the fetching and filtering is plain code and the
model — when enabled — only ranks the already-filtered shortlist.

Usage:
    claimscout scan --repos owner/a,owner/b [--max-comments 1] [--json]
    claimscout scan --repos-file repos.txt

Auth: set GH_TOKEN (or GITHUB_TOKEN) in the environment. A token raises the
rate limit from 60 to 5000 requests/hour; without one ClaimScout still works
against public repos, just more slowly.

Exit codes:
    0  ran successfully (may have found nothing)
    1  configuration / auth error
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict

API = "https://api.github.com"
UA = "claimscout/1.0"

# Labels that mark architecture / planning work rather than a bounded fix.
ARCH_LABELS = re.compile(
    r"epic|roadmap|spike|feature|design|discussion|wontfix|question|meta", re.I
)
# Labels that mark a bounded, startable piece of work.
ACTIONABLE = re.compile(
    r"bug|good first issue|help wanted|enhancement|low priority|documentation", re.I
)
# Real work, but not the kind of thing you claim and finish in a sitting.
NOISE = re.compile(r"refactoring|to-groom|spike|optimization|cryptography|test\b", re.I)


@dataclass
class Candidate:
    repo: str
    number: int
    title: str
    comments: int
    created: str
    labels: list[str]
    url: str

    def why(self) -> str:
        return f"unclaimed, {self.comments} comment(s), created {self.created}"


class GitHubError(Exception):
    pass


def _request(url: str, token: str | None, retries: int = 3) -> object:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": UA}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    last_err: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # 403/429 = rate limited. Honour Retry-After when present.
            if e.code in (403, 429) and attempt < retries - 1:
                wait = int(e.headers.get("Retry-After", 2 ** attempt))
                time.sleep(wait)
                last_err = e
                continue
            raise GitHubError(f"HTTP {e.code} for {url}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                last_err = e
                continue
            raise GitHubError(f"network error for {url}: {e}") from e
    raise GitHubError(f"giving up on {url}: {last_err}")


def fetch_open_issues(repo: str, token: str | None) -> list[dict]:
    url = f"{API}/repos/{repo}/issues?state=open&sort=updated&direction=desc&per_page=50"
    data = _request(url, token)
    return data if isinstance(data, list) else []


def triage(issues: list[dict], repo: str, max_comments: int) -> list[Candidate]:
    rows: list[Candidate] = []
    for i in issues:
        if "pull_request" in i:
            continue  # PRs are not claimable issues
        if i.get("assignees"):
            continue  # already assigned
        if i["comments"] > max_comments:
            continue  # contested / already heavily discussed
        labels = [l["name"] for l in i.get("labels", [])]
        if any(ARCH_LABELS.search(l) for l in labels):
            continue  # architecture, not a bounded bug
        user = (i.get("user") or {}).get("login", "")
        if user.endswith("[bot]"):
            continue  # release bots, dependabot, etc.
        rows.append(
            Candidate(
                repo=repo,
                number=i["number"],
                title=i["title"],
                comments=i["comments"],
                created=i["created_at"][:10],
                labels=labels,
                url=i["html_url"],
            )
        )

    best: list[Candidate] = []
    for c in rows:
        lab = " ".join(c.labels)
        is_actionable = bool(ACTIONABLE.search(lab)) or not c.labels
        is_noise = bool(NOISE.search(lab)) and not ACTIONABLE.search(lab)
        if is_actionable and not is_noise:
            best.append(c)
    return best


def scan(repos: list[str], max_comments: int, token: str | None) -> list[Candidate]:
    found: list[Candidate] = []
    for repo in repos:
        try:
            issues = fetch_open_issues(repo, token)
        except GitHubError as e:
            print(f"  ! {repo}: {e}", file=sys.stderr)
            continue
        found.extend(triage(issues, repo, max_comments))
    return found


def render(candidates: list[Candidate], as_json: bool) -> str:
    if as_json:
        return json.dumps([asdict(c) for c in candidates], indent=2)
    if not candidates:
        return "No claimable issues found. (silence is a valid result)"
    by_repo: dict[str, list[Candidate]] = {}
    for c in candidates:
        by_repo.setdefault(c.repo, []).append(c)
    lines = []
    for repo, items in by_repo.items():
        lines.append(f"{repo}: {len(items)} claimable")
        for c in items[:6]:
            lines.append(f"  #{c.number:<5} {c.why():<34} {c.title[:56]}")
            if c.labels:
                lines.append(f"         labels: {', '.join(c.labels[:4])}")
            lines.append(f"         {c.url}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="claimscout", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sc = sub.add_parser("scan", help="scan repos for claimable issues")
    sc.add_argument("--repos", help="comma-separated owner/repo list")
    sc.add_argument("--repos-file", help="file with one owner/repo per line")
    sc.add_argument(
        "--max-comments",
        type=int,
        default=1,
        help="skip issues with more than this many comments (default 1)",
    )
    sc.add_argument("--json", action="store_true", help="emit JSON")
    args = p.parse_args(argv)

    if args.cmd == "scan":
        repos: list[str] = []
        if args.repos:
            repos.extend(r.strip() for r in args.repos.split(",") if r.strip())
        if args.repos_file:
            with open(args.repos_file) as f:
                repos.extend(
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith("#")
                )
        if not repos:
            print("error: provide --repos or --repos-file", file=sys.stderr)
            return 1

        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            print(
                "note: no GH_TOKEN set — using anonymous access (60 req/hr).",
                file=sys.stderr,
            )
        candidates = scan(repos, args.max_comments, token)
        print(render(candidates, args.json))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
