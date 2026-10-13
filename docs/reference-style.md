# Reference Style Notes (Elitr / BNB Hack launch video)

Studied from the reference video the user provided
(`x.com/encrypt_wizard/status/2108955432035262951`). The key finding, which
shaped the ClaimScout demo rework:

## It is NOT glossy/cinematic — it's restrained and typographic

The polish comes from **restraint + hierarchy**, not glow, gradients, or 3D.

### The recipe
- **Background:** true flat black (`#000`). No gradient, no texture.
- **One accent color:** a single warm yellow (`#FACC15`-ish), used sparingly —
  a top border rule, a status dot, an active-tab highlight, a hero number.
- **Typography:**
  - Big bold numerals/phrases are the hero (e.g. `+1.1%`, `134`, `MERGED`).
  - Small uppercase monospace for metadata in the corners (agent IDs, dates, repo).
  - Clean sans for supporting copy, muted grey.
- **Layout:** left-aligned core content with generous negative space; a real
  product screenshot or clean diagram as the right-hand or central element.
- **Motion:** elements ease/spring in; nothing floats or drips. Cuts are crisp.
- **Chrome:** a thin accent rule across the very top edge; a small brand lockup
  (◆ logo) bottom-right; corner metadata top-left / top-right.

### What "luxurious" meant here
Confident hierarchy: one enormous focal element per frame, everything else quiet
and small. The absence of decoration *is* the polish.

## Applied to ClaimScout
- `BG = (0,0,0)`, `ACCENT = (250,204,21)` — flat black + one yellow.
- `ref_chrome()`: top accent rule + uppercase mono corner metadata + optional ticker.
- `brandmark()`: `◆ CLAIMSCOUT` bottom-right.
- Beats use big hero numbers (`#682` at 64px, `MERGED` at 76px), spring easing
  (`ease_out_back`), left-aligned content, muted mono metadata.
- Panels are flat `PANEL` fill with a 3px accent top-edge — no outlines, no glow.
