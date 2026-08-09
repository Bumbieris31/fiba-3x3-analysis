# Latvia 3x3 — game tagging & analysis

Tools for tracking what FIBA's reduced box scores leave out (attempts, assists,
rebounds, turnovers, fouls, blocks/steals, substitutions, defensive matchups)
for Latvia's Nations League team, and turning the tags into reports.

Season dashboard (official scoring data, all 6 Europe-2 stops):
https://claude.ai/code/artifact/161aa244-9183-4671-aeda-89efcda4aec3

## Workflow

0. **Prefill from FIBA (optional but recommended)** — FIBA's play-by-play feed
   already has every made shot, free throw and team foul with clock times.
   `python3 prefill.py <game page url> --game-label S1-P1 -o data/prefills/x.csv`
   converts it to our format; in the tagger choose **Import prefill CSV** and
   you only tag what FIBA doesn't record: FG misses, rebounds, assists,
   turnovers, blocks/steals, bench changes, defenders on opponent shots,
   foul attribution.
   All 18 games of the 2026 season are already generated in `data/prefills/`.
   With a prefill loaded, keep the page clock roughly synced — your new tags
   are slotted into the timeline by clock time.
   (Don't run analyze.py on bare prefills: they contain only makes, so
   shooting percentages would read 100%.)
1. **Tag a game** — open `tagger.html` in a browser (double-click, works
   offline). Enter game id / opponent / roster, then tag while watching video:
   pick the player, pick the event, answer the follow-up where one appears.
   Progress autosaves to the browser; "Resume saved game" recovers after an
   accidental close.

   The game clock is **optional**. Everything except minutes-played and the
   possession-length section works from event order alone. If you do want
   time data, start/pause the page clock in sync with the game and hit Set
   to resync when it drifts — even ±30s accuracy is enough for minutes.

   Tagging conventions:
   - Lineups are tracked by **who is resting**: tap the resting player's name
     in the "Resting" row at the start and on every change. The other three
     are on court by definition.
   - Assists on **prefilled** makes: tap the passer, then **Assist** — it
     attaches to the most recent made Latvia shot at/before the current clock
     (Undo reverts the attachment). Manually tagged makes ask for the assister
     directly.
   - **Assist rule** (keep it strict and constant): last pass before a made
     shot counts if the scorer went up immediately or within one dribble.
     Nothing on misses. Decide once whether a pass drawing made FTs counts —
     currently: it does not.
   - **Defended**: after an opponent shot, tap the Latvia defender who
     contested it, then Defended - it attaches to the most recent opponent
     field goal (made or missed) at/before the current clock. Tagging it on
     makes gives points-allowed per defender; also tagging opponent misses
     (opponent -> 1PT/2PT miss, then defender -> Defended) adds FG% allowed.
   - Tag opponent **scores** always (needed for plus-minus); opponent misses
     and turnovers are optional but improve possession stats.
2. **Export CSV** and save it into `data/` (one file per game is fine).
3. **Run the report**: `python3 analyze.py data/` (no dependencies).

## What the report gives you

- Scoring efficiency: real shooting percentages, turnovers, usage, points per
  possession used
- Creation: assists, points created, passer→scorer pair matrix, assisted share
- Rebounding: OREB/DREB per player
- Defense: blocks, steals, and shot defense per defender (contested shots,
  points allowed, FG% allowed when misses are tagged)
- Foul ledger: committed vs drawn per player, when the team entered the penalty
- Possession counts and points per possession (order-based); with clock data
  also time-to-shot / late-clock frequency (no visible shot clock needed)
- On/off plus-minus per player (from bench rows + opponent scores); minutes
  and net-per-10-min appear when lineup rows carry clock times

## Files

- `methodology.md` — the counting rules and judgment calls (what qualifies as
  a steal, the rebound control test, held balls, …); update it whenever a new
  situation forces a decision
- `tagger.html` — offline tagging UI, exports the event-log CSV
- `prefill.py` — pulls FIBA's play-by-play for a game into a starter CSV
- `data/prefills/` — starter CSVs for all 18 games of the 2026 season
- `analyze.py` — turns event-log CSVs into the report (stdlib only)
- `data/SAMPLE-game.csv` — fabricated demo game showing the format; delete once
  real games exist (or keep for reference — just don't pass it to analyze.py
  together with real data)

## CSV format

`game,opponent,round,clock,team,player,event,result,related[,jersey]` — one
row per event, in chronological order. The optional `jersey` column is
display-only: the tagger uses it to show numbers on buttons ("3 · Skreivers");
analyze.py ignores it. In the tagger's roster field you can prefix numbers
("3 Skreivers, 2 Zviedris") to get numbered buttons in manual games too.
Events: `shot1 shot2 ft` (+ result `make|miss`; on LAT makes `related` = the
assister, on OPP shots `related` = the Latvia defender who contested it),
`to oreb dreb blk stl foul fould`, and `bench` (player = who is now resting).
Legacy `sub_in`/`sub_out` and `matchup` rows still parse. Clock is game time remaining counting
down from 10:00, and may be left blank. The same format can be typed by hand
in any spreadsheet and exported as CSV.
