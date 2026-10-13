# ClaimScout Demo — Audio Track Plan

The video generator (`tools/make_demo.py`) renders all visuals and encodes them with
ffmpeg. This file specifies the audio layer to lay over it: voiceover, music, and SFX,
beat by beat. Total runtime target: **85 seconds**.

You can record the VO yourself (recommended — it sounds human) or use a TTS voice, then
mux it onto the rendered video:

```bash
# after rendering demo.mp4 and recording voiceover.wav + music.mp3:
ffmpeg -i demo.mp4 -i voiceover.wav -i music.mp3 \
  -filter_complex "[1:a]volume=1.0[vo];[2:a]volume=0.25[mus];[vo][mus]amix=inputs=2:duration=first[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -shortest demo-final.mp4
```

---

## Voiceover script (word-for-word, ~85s at a brisk pace)

| Beat | Time | Line |
|---|---|---|
| 1 | 0:00 | "This is Kai. She's trying to land her first merged pull request." |
| 1 | 0:05 | "She's got the skills. What she doesn't have — is time." |
| 1 | 0:08 | "Forty open issues. Half are already claimed. The rest are epics, or ghosts nobody's touched in a year." |
| 1 | 0:13 | "What if a tool just told her which ones are actually hers to take?" |
| 2 | 0:15 | "This is ClaimScout. Point it at the repos you care about, and it hands back only the issues that are actually yours to take — unclaimed, bounded, and real." |
| 3 | 0:25 | "Watch. It strips out everything that's a dead end — assigned work, bots, epics." |
| 3 | 0:32 | "Issue 705: unclaimed, zero comments, labeled bug." |
| 3 | 0:38 | "And 682 — good first issue." |
| 3 | 0:43 | "Now the open-weight model ranks them against her skills…" |
| 3 | 0:47 | "…and 682 floats straight to the top. That's the one she takes." |
| 4 | 0:50 | "Under the hood, the fetching and filtering is plain code — no model in the loop, because small models can't sustain one." |
| 4 | 0:57 | "The model does one thing: a single call that ranks a clean shortlist. That's why it's cheap enough to run — and why it doesn't hallucinate." |
| 5 | 1:05 | "Scan any repo. Rank it on your skills. Pipe the JSON anywhere you want." |
| 6 | 1:15 | "Same night. Same Kai. But now she's not digging — she's shipping. Her PR is open… and merged." |
| 6 | 1:22 | "ClaimScout. Claim what's yours." |

**Pacing notes:** read it fast but unhurried; land "hers to take" (0:47) and "Claim what's
yours" (1:22) with a slight pause before them. Total spoken length ≈ 80s, leaving air at
the top and tail.

---

## Music

- **Style:** lo-fi / minimal electronic. One continuous bed, not songs per beat.
- **0:00–0:15 (Beat 1):** tense, low pulse, ~90 BPM, slightly muffled — friction.
- **0:15–0:25 (Beat 2):** pulse drops out, one confident sustained synth note — the reveal.
- **0:25–0:50 (Beat 3):** arpeggio builds underneath, energy rising to the aha at 0:47.
- **0:50–1:05 (Beat 4):** strip back to a clean minimal beat — "under the hood" clarity.
- **1:05–1:15 (Beat 5):** uptempo, driving, ~120 BPM — the montage.
- **1:15–1:25 (Beat 6):** resolve to a warm, triumphant final chord, then tail to silence.
- **Bed level:** ~-22 LUFS under the VO (music at ~25% volume so it never fights the voice).
- **Sources for royalty-free beds:** YouTube Audio Library, Uppbeat, Free Music Archive
  (filter to CC-BY or no-attribution).

---

## SFX cues

| Time | Cue |
|---|---|
| 0:06, 0:09, 0:12 | soft dull *thud* / downward blip on each dead-end issue |
| 0:14 | bass hit + record scratch on "Sound familiar?" |
| 0:16 | single keyboard clack as the command types |
| 0:20 | soft chime as the logo/tagline lands |
| 0:28–0:41 | light *tick* per result line; *whoosh* on each of the two callouts |
| 0:47 | rising chime as #682 hits #1 (the aha — the money moment) |
| 0:52, 1:00 | quick *whoosh* on each architecture zoom |
| 1:06, 1:09, 1:12 | hard-cut *whoosh* per montage caption |
| 1:19 | satisfying merge chime + soft confetti pop on the green badge |
| 1:22 | single clean hit on the logo card, then silence |

Keep SFX subtle and sparse — they punctuate, they don't decorate. The two that carry the
video are the **0:47 aha chime** and the **1:19 merge chime**; give those a touch more
presence than the rest.
