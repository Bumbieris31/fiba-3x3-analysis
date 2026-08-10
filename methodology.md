# Tagging methodology

The judgment calls behind our stats. The tools (`README.md`) define *how* to
tag; this file defines *what counts*. Consistency across games matters more
than any single call — when a new situation forces a decision, make it once,
add it here, and never bend it mid-season.

## Assists

The last pass before a made shot counts **if the scorer went up immediately
or within one dribble**. Nothing on misses. A pass that draws a shooting foul
with made free throws does **not** count as an assist.

## Rebounds — the control test

A rebound requires **control**: the player could land, hold the ball, and
make a normal play. Tips, bats, and mid-air saves are not rebounds.

- Saved a ball flying out of bounds and it ended up with the opponents:
  tag **nothing** — no control, so no rebound and no turnover.
- Caught it, landed, then lost it: **Off. rebound + Turnover**, both earned.

General principle: when in doubt about control, don't credit the touch.
Rebound requires control; turnover requires losing control you actually had.

## Turnovers — who gets charged

- Bad pass (intercepted, thrown away, out of bounds): the **passer**.
- Catchable pass fumbled or lost after the catch: the **receiver**.
- Travels, offensive fouls, 12-second violations, stepping out: the player
  **with the ball**.
- Genuinely fuzzy: charge the player who had the last reasonable chance to
  save the play.

## Held balls

There is no possession arrow in 3x3 — **the defense always wins a held ball**.

- Latvia tied up on offense: **Turnover** on the player who got trapped.
- Latvia's defender forces the tie-up: **Steal** on the forcer.

## Forced turnovers

A Latvia defender who causes an opponent turnover gets a **Steal** when the
cause is direct: *his hand touched the ball, or the opponent's error happened
because of his immediate pressure in that action* (picked pass, strip,
deflection — including one that goes out of bounds — forced tie-up).

"He was playing good defense nearby" does **not** qualify; an unforced
opponent error is tagged as nothing. This is the most subjective line in the
methodology — when unsure, lean toward *not* crediting the steal.

A drawn charge / offensive foul is **Foul drawn** on the defender, not a steal.

## Shot defense (Defended)

Credit the defender who **actually contested the shot** — not the nominal
matchup (assignments switch constantly; we track the shot, not the assignment).

- Opponent **makes**: always attach a defender (two taps, prefilled shot).
- Opponent **misses**: optional. Tagging them (shooter → miss, defender →
  Defended) unlocks FG%-allowed. Do it in games where the defensive question
  matters; skip it when it doesn't — but within one game, be consistent.
- Wide-open shot with no contest: no Defended tag (on a tagged miss, leave
  the defender off; that *is* the record of "nobody contested").

## Fouls

FIBA's prefilled foul rows are team-level (no player) and carry the team-foul
count and penalty timing. Our tags add the individuals:

- **Foul committed** on the Latvia player responsible (optional but cheap).
  This fills the player into the nearest unattributed prefilled foul row
  rather than adding a new row, so team-foul counts stay correct. (analyze.py
  also merges older exports where attribution created duplicate rows.)
- **Foul drawn** on the Latvia player the foul was committed **against** —
  recipient-based, not merit-based. An unnecessary opponent foul still counts;
  whether it was cleverly earned is interpretation, not tagging. No recipient
  (technical, delay of game) = no Foul drawn tag. Tag at roughly the same
  clock as the prefilled opponent foul.

## Lineups

Tracked by **who is resting** — one bench tap at the start and on every
change. The other three are on court by definition.

## Clock discipline

With a prefill loaded, keep the page clock roughly synced (resync at breaks;
±5s is fine). FIBA's table-official timestamps often lag the video by a few
seconds — that's harmless. Edit a prefilled timestamp (click it in the log)
only when it puts events in the wrong *order*, or when a misplaced time would
make an Assist/Defended attach to the wrong shot.

## What we deliberately don't tag

- Opponent misses (unless doing FG%-allowed), turnovers, and rebounds —
  opponent scoring arrives via the prefill and covers plus-minus and shot
  defense; the rest isn't worth doubling the workload.
- Standing defensive assignments (matchups) — replaced by per-shot Defended.
- Screens and contest quality — too subjective to keep consistent solo.
