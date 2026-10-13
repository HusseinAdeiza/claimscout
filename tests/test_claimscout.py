#!/usr/bin/env python3
"""
ClaimScout test suite. Pure-stdlib unittest so it runs anywhere with no deps.

Covers:
  - the triage filter (assigned/bot/arch/contested/actionable logic)
  - the ranker's JSON parsing against messy model output
  - prompt construction

Run: python3 tests/test_claimscout.py
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import claimscout as cs  # noqa: E402
import claimscout_rank as rank  # noqa: E402


def issue(number, *, labels=None, comments=0, assignees=None, user="human", title="t"):
    return {
        "number": number,
        "title": title,
        "comments": comments,
        "assignees": assignees or [],
        "user": {"login": user},
        "created_at": "2026-10-01T00:00:00Z",
        "html_url": f"https://github.com/o/r/issues/{number}",
        "labels": [{"name": l} for l in (labels or [])],
    }


def pr(number):
    d = issue(number)
    d["pull_request"] = {"url": "..."}
    return d


class TestTriage(unittest.TestCase):
    def test_skips_pull_requests(self):
        out = cs.triage([pr(1), issue(2, labels=["bug"])], "o/r", 1)
        self.assertEqual([c.number for c in out], [2])

    def test_skips_assigned(self):
        out = cs.triage([issue(1, assignees=[{"login": "x"}], labels=["bug"])], "o/r", 1)
        self.assertEqual(out, [])

    def test_skips_bots(self):
        out = cs.triage([issue(1, user="dependabot[bot]", labels=["bug"])], "o/r", 1)
        self.assertEqual(out, [])

    def test_skips_contested(self):
        out = cs.triage([issue(1, comments=5, labels=["bug"])], "o/r", 1)
        self.assertEqual(out, [])

    def test_skips_architecture_labels(self):
        out = cs.triage([issue(1, labels=["epic"])], "o/r", 1)
        self.assertEqual(out, [])

    def test_keeps_bounded_bug(self):
        out = cs.triage([issue(7, labels=["bug", "good first issue"])], "o/r", 1)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].number, 7)

    def test_keeps_unlabelled_recent(self):
        out = cs.triage([issue(8, labels=[])], "o/r", 1)
        self.assertEqual(len(out), 1)

    def test_noise_label_dropped_when_not_actionable(self):
        # "refactoring" alone is real work but not a claimable first contribution.
        out = cs.triage([issue(9, labels=["refactoring"])], "o/r", 1)
        self.assertEqual(out, [])

    def test_max_comments_boundary(self):
        # comments == max_comments is allowed (only strictly greater is skipped).
        out = cs.triage([issue(3, comments=1, labels=["bug"])], "o/r", 1)
        self.assertEqual(len(out), 1)


class TestRankParsing(unittest.TestCase):
    def test_plain_array(self):
        self.assertEqual(len(rank.parse_ranking('[{"number": 1}]')), 1)

    def test_object_wrapping_array(self):
        text = '{"ranking": [{"number": 2, "score": 90}]}'
        self.assertEqual(rank.parse_ranking(text)[0]["number"], 2)

    def test_prose_wrapped_array(self):
        text = 'Sure! Here you go:\n[{"number": 3}]\nHope that helps.'
        self.assertEqual(rank.parse_ranking(text)[0]["number"], 3)

    def test_garbage_returns_empty(self):
        self.assertEqual(rank.parse_ranking("no json here at all"), [])

    def test_strips_json_code_fence(self):
        text = '```json\n[{"number": 6, "score": 80}]\n```'
        self.assertEqual(rank.parse_ranking(text)[0]["number"], 6)

    def test_strips_plain_code_fence(self):
        text = '```\n[{"number": 7}]\n```'
        self.assertEqual(rank.parse_ranking(text)[0]["number"], 7)

    def test_drops_non_dict_entries(self):
        text = '[{"number": 4}, "junk", 5]'
        out = rank.parse_ranking(text)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["number"], 4)


class TestPrompt(unittest.TestCase):
    def test_prompt_includes_profile_and_slims_fields(self):
        cands = [{
            "number": 705, "repo": "o/r", "title": "bug",
            "labels": ["bug"], "comments": 0,
            # url/created must be stripped to keep the prompt small
            "url": "https://x", "created": "2026-10-12",
        }]
        prompt = rank.build_prompt(cands, "rust,anchor")
        self.assertIn("rust,anchor", prompt)
        self.assertIn("705", prompt)
        self.assertNotIn("https://x", prompt)  # url stripped


class TestRender(unittest.TestCase):
    def test_json_render(self):
        c = cs.Candidate("o/r", 1, "t", 0, "2026-10-01", ["bug"], "u")
        self.assertEqual(json.loads(cs.render([c], True))[0]["number"], 1)

    def test_empty_render(self):
        self.assertIn("silence", cs.render([], False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
