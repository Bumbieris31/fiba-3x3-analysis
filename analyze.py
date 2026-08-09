#!/usr/bin/env python3
"""Analyze tagged 3x3 game event logs.

Usage:
    python3 analyze.py data/*.csv
    python3 analyze.py data/           # all .csv files in a directory

Input format (one row per event, exported by tagger.html or typed manually):

    game,opponent,round,clock,team,player,event,result,related

    game     - short id, e.g. "S6-F" (groups rows into games)
    opponent - opponent team name (repeated on every row)
    round    - Pool / Final / SF ...
    clock    - game clock remaining, mm:ss (10:00 counts down to 0:00).
               OPTIONAL - leave blank and everything still works except
               minutes played and the possession/shot-clock section.
    team     - LAT or OPP
    player   - who did it (opponent player name for OPP rows; may be blank)
    event    - shot1 | shot2 | ft | to | oreb | dreb | blk | stl |
               foul | fould | bench | matchup
               (legacy sub_in / sub_out rows are still understood)
    result   - make | miss   (shots and free throws only)
    related  - assisting player on made LAT shots;
               opponent player name for matchup rows

Conventions:
    * Rows must be in chronological order (the tagger guarantees this) -
      all order-based stats use row order, not the clock.
    * A bench row means: from here on, `player` is the one resting and the
      other three are on court. Tag one at game start, then on every change.
    * A matchup row means: from here on, `player` (LAT) is the primary
      defender on `related` (OPP player). Re-tag on switches.
    * Tag every LAT event you can see. For OPP, scores are required for
      plus-minus, misses/TOs are optional but improve possession stats.
"""
import csv, sys, os
from collections import defaultdict, Counter

PTS = {'shot1': 1, 'shot2': 2, 'ft': 1}
GAME_SECONDS = 600

def clock_to_elapsed(clock):
    """mm:ss remaining -> seconds elapsed since start (None if blank/invalid)."""
    try:
        m, s = clock.strip().split(':')
        return GAME_SECONDS - (int(m) * 60 + int(s))
    except Exception:
        return None

def load(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            files += [os.path.join(p, f) for f in sorted(os.listdir(p)) if f.endswith('.csv')]
        else:
            files.append(p)
    rows = []
    for f in files:
        with open(f, newline='', encoding='utf-8-sig') as fh:
            for r in csv.DictReader(fh):
                r = {k.strip(): (v or '').strip() for k, v in r.items() if k}
                if r.get('event'):
                    r['elapsed'] = clock_to_elapsed(r.get('clock', ''))
                    rows.append(r)
    return rows

def fmt_pct(made, att):
    return f"{made}/{att} ({made/att*100:.0f}%)" if att else "-"

def header(title):
    print(f"\n{'=' * 64}\n{title}\n{'=' * 64}")

def main(paths):
    rows = load(paths)
    if not rows:
        sys.exit("No event rows found. Pass CSV files or a directory.")
    games = sorted({r['game'] for r in rows})

    # Merge foul attributions: a player-named LAT foul row tagged within 20s of
    # a team-level (blank-player) foul row is the same foul recorded twice -
    # one from FIBA's prefill, one from the tagger. Keep the named row, drop
    # the blank twin, so team-foul counts aren't doubled. (Current tagger
    # versions attach the player in place; this handles older exports.)
    drop = set()
    for g in games:
        fouls = [(i, r) for i, r in enumerate(rows)
                 if r['game'] == g and r['team'] == 'LAT' and r['event'] == 'foul']
        blanks = [(i, r) for i, r in fouls if not r['player']]
        for i, r in fouls:
            if r['player'] and r['elapsed'] is not None:
                best = None
                for j, b in blanks:
                    if j in drop or b['elapsed'] is None:
                        continue
                    d = abs(b['elapsed'] - r['elapsed'])
                    if d <= 20 and (best is None or d < best[1]):
                        best = (j, d)
                if best:
                    drop.add(best[0])
    if drop:
        rows = [r for i, r in enumerate(rows) if i not in drop]
        print(f'(merged {len(drop)} team-level foul rows with their player attributions)')

    lat = [r for r in rows if r['team'] == 'LAT']
    opp = [r for r in rows if r['team'] == 'OPP']
    players = sorted({r['player'] for r in lat if r['player'] and r['event'] not in ('matchup',)})

    def game_rows(g):
        """Rows of one game in tagged (chronological) order."""
        return [r for r in rows if r['game'] == g]

    print(f"Loaded {len(rows)} events from {len(games)} game(s): {', '.join(games)}")

    # ---------------- scoring & efficiency ----------------
    header('SCORING & EFFICIENCY (per player)')
    print(f"{'player':24}{'PTS':>4}{'1PT':>13}{'2PT':>13}{'FT':>13}{'TO':>4}{'usage':>7}{'pts/use':>8}")
    for p in players:
        pr = [r for r in lat if r['player'] == p]
        pts = sum(PTS[r['event']] for r in pr if r['event'] in PTS and r['result'] == 'make')
        s1m = sum(1 for r in pr if r['event'] == 'shot1' and r['result'] == 'make')
        s1a = sum(1 for r in pr if r['event'] == 'shot1' and r['result'] in ('make', 'miss'))
        s2m = sum(1 for r in pr if r['event'] == 'shot2' and r['result'] == 'make')
        s2a = sum(1 for r in pr if r['event'] == 'shot2' and r['result'] in ('make', 'miss'))
        ftm = sum(1 for r in pr if r['event'] == 'ft' and r['result'] == 'make')
        fta = sum(1 for r in pr if r['event'] == 'ft' and r['result'] in ('make', 'miss'))
        to = sum(1 for r in pr if r['event'] == 'to')
        usage = s1a + s2a + to               # possessions this player ended
        ppu = f"{pts/usage:.2f}" if usage else '-'
        print(f"{p:24}{pts:>4}{fmt_pct(s1m,s1a):>13}{fmt_pct(s2m,s2a):>13}{fmt_pct(ftm,fta):>13}{to:>4}{usage:>7}{ppu:>8}")

    # ---------------- creation / assists ----------------
    header('CREATION (assists & pair matrix)')
    made = [r for r in lat if r['event'] in ('shot1', 'shot2') and r['result'] == 'make']
    ast = Counter(); created = Counter(); pairs = Counter()
    for r in made:
        if r['related']:
            ast[r['related']] += 1
            created[r['related']] += PTS[r['event']]
            pairs[(r['related'], r['player'])] += PTS[r['event']]
    print(f"{'player':24}{'AST':>5}{'pts created':>13}{'assisted makes':>16}")
    for p in players:
        rec = sum(1 for r in made if r['player'] == p and r['related'])
        tot = sum(1 for r in made if r['player'] == p)
        print(f"{p:24}{ast[p]:>5}{created[p]:>13}{f'{rec}/{tot}':>16}")
    if pairs:
        print("\nTop passer -> scorer pairs (by points created):")
        for (a, b), v in pairs.most_common(8):
            print(f"  {a} -> {b}: {v} pts")
    # assisted vs unassisted conversion needs misses w/ potential assist unknown; report share instead
    a_m = sum(1 for r in made if r['related']); print(f"\nAssisted share of made field goals: {fmt_pct(a_m, len(made))}")

    # ---------------- rebounding ----------------
    header('REBOUNDING')
    print(f"{'player':24}{'OREB':>6}{'DREB':>6}{'total':>7}")
    for p in players:
        o = sum(1 for r in lat if r['player'] == p and r['event'] == 'oreb')
        d = sum(1 for r in lat if r['player'] == p and r['event'] == 'dreb')
        print(f"{p:24}{o:>6}{d:>6}{o+d:>7}")

    # ---------------- defense ----------------
    header('DEFENSE (blocks, steals, shot defense)')
    print(f"{'player':24}{'BLK':>5}{'STL':>5}")
    for p in players:
        b = sum(1 for r in lat if r['player'] == p and r['event'] == 'blk')
        s = sum(1 for r in lat if r['player'] == p and r['event'] == 'stl')
        print(f"{p:24}{b:>5}{s:>5}")
    # shot-level defense: OPP field-goal rows whose `related` names the Latvia
    # defender who contested the shot (tagged via the Defended button)
    d_shots = Counter(); d_makes = Counter(); d_pts = Counter(); d_vs = Counter()
    for r in opp:
        if r['event'] in ('shot1', 'shot2') and r['related']:
            d = r['related']
            d_shots[d] += 1
            if r['result'] == 'make':
                d_makes[d] += 1; d_pts[d] += PTS[r['event']]
                d_vs[(d, r['player'] or '?')] += PTS[r['event']]
    if d_shots:
        misses_tagged = any(d_shots[d] > d_makes[d] for d in d_shots)
        print("\nShot defense (contested opponent field goals):")
        hdr = f"{'defender':24}{'contested':>10}{'makes':>7}{'pts':>5}"
        print(hdr + (f"{'FG% allowed':>13}" if misses_tagged else ''))
        for d in sorted(d_shots, key=lambda x: d_pts[x]):
            line = f"{d:24}{d_shots[d]:>10}{d_makes[d]:>7}{d_pts[d]:>5}"
            if misses_tagged:
                line += f"{d_makes[d]/d_shots[d]*100:>12.0f}%"
            print(line)
        if not misses_tagged:
            print("  (only makes carry defenders - tag Defended on opponent misses too for FG% allowed)")
        print("\nPoints allowed (defender <- opponent):")
        for (d, o), v in sorted(d_vs.items(), key=lambda x: -x[1]):
            print(f"  {d} <- {o}: {v} pts")
    # legacy assignment-based matchup rows still work
    mu_pts = Counter()
    for g in games:
        assign = {}                                    # opp player -> lat defender
        for r in game_rows(g):
            if r['event'] == 'matchup' and r['team'] == 'LAT' and r['related']:
                assign[r['related']] = r['player']
            if (r['team'] == 'OPP' and r['event'] in PTS and r['result'] == 'make'
                    and not r['related'] and r['player'] in assign):
                mu_pts[(assign[r['player']], r['player'])] += PTS[r['event']]
    if mu_pts:
        print("\nPoints allowed by standing assignment (matchup rows):")
        for (d, o), v in sorted(mu_pts.items(), key=lambda x: -x[1]):
            print(f"  {d} <- {o}: {v} pts")
    if not d_shots and not mu_pts:
        print("\n(no Defended or matchup rows tagged yet)")

    # ---------------- fouls ----------------
    header('FOUL LEDGER')
    print(f"{'player':24}{'committed':>10}{'drawn':>7}")
    for p in players:
        c = sum(1 for r in lat if r['player'] == p and r['event'] == 'foul')
        d = sum(1 for r in lat if r['player'] == p and r['event'] == 'fould')
        print(f"{p:24}{c:>10}{d:>7}")
    for g in games:
        fl = [r for r in game_rows(g) if r['team'] == 'LAT' and r['event'] == 'foul']
        if len(fl) >= 7:
            r7 = fl[6]
            when = f" at {r7['clock']} on the clock" if r7['elapsed'] is not None else ''
            print(f"  {g}: entered penalty (7th team foul){when}, committed by {r7['player'] or '(unattributed)'}")

    # ---------------- possessions & clock ----------------
    header('POSSESSIONS & SHOT-CLOCK PROXY')
    # A LAT possession starts on: dreb, oreb (12s reset), steal, or any OPP score.
    # It ends on: a LAT shot attempt, turnover, or free-throw trip.
    # Possession COUNTS need only event order; possession LENGTHS need clocks.
    # Lengths >13s mean the start wasn't tagged precisely; they're excluded from
    # the shot-clock proxy but still counted as possessions.
    for g in games:
        lat_poss, lengths, start, prev = 0, [], None, None
        for r in game_rows(g):
            if (r['event'] == 'ft' and prev and prev['event'] == 'ft'
                    and prev['player'] == r['player'] and prev['clock'] == r['clock']):
                prev = r
                continue                            # same free-throw trip, count once
            prev = r
            if r['team'] == 'LAT' and (r['event'] == 'to' or
                    (r['event'] in ('shot1', 'shot2', 'ft') and r['result'] in ('make', 'miss'))):
                if start is not None and r['elapsed'] is not None:
                    lengths.append(max(0, r['elapsed'] - start))
                lat_poss += 1
                start = None                        # ball dead or with OPP (oreb re-arms below)
            if r['team'] == 'LAT' and r['event'] in ('dreb', 'oreb', 'stl'):
                start = r['elapsed']
            if r['team'] == 'OPP' and r['event'] in PTS and r['result'] == 'make':
                start = r['elapsed']                # LAT ball after OPP score
        pts = sum(PTS[r['event']] for r in game_rows(g)
                  if r['team'] == 'LAT' and r['event'] in PTS and r['result'] == 'make')
        timed = [l for l in lengths if l <= 13]
        late = sum(1 for l in timed if l >= 9)
        if timed:
            print(f"{g}: ~{lat_poss} LAT possessions ended, {pts} pts | avg timed possession "
                  f"{sum(timed)/len(timed):.1f}s, late-clock (9-13s): {late}/{len(timed)}")
        else:
            print(f"{g}: ~{lat_poss} LAT possessions ended, {pts} pts"
                  f" ({pts/lat_poss:.2f}/poss) | no clock data, lengths skipped" if lat_poss else
                  f"{g}: no possessions found")

    # ---------------- on/off plus-minus ----------------
    # Lineups come from bench rows ("this player now rests, other three play")
    # or legacy sub_in/sub_out pairs. Plus-minus itself needs only event ORDER;
    # minutes are added when the lineup-change rows carry clock times.
    header('ON/OFF PLUS-MINUS (needs bench rows + OPP scores)')
    onoff = defaultdict(lambda: [0, 0, 0])            # player -> [pts for, pts against, seconds on]
    any_lineup = False
    for g in games:
        on, last_t, game_timed = set(), 0, False
        def credit_time(now):
            nonlocal last_t, game_timed
            if now is not None:
                for p in on: onoff[p][2] += max(0, now - last_t)
                last_t = now
                game_timed = True
        for r in game_rows(g):
            if r['team'] == 'LAT' and r['event'] == 'bench':
                credit_time(r['elapsed'])
                on = {p for p in players if p != r['player']}
                any_lineup = True
            elif r['team'] == 'LAT' and r['event'] == 'sub_in':
                credit_time(r['elapsed'])
                on.add(r['player']); any_lineup = True
            elif r['team'] == 'LAT' and r['event'] == 'sub_out':
                credit_time(r['elapsed'])
                on.discard(r['player'])
            elif r['event'] in PTS and r['result'] == 'make':
                v = PTS[r['event']]
                for p in on:
                    onoff[p][0 if r['team'] == 'LAT' else 1] += v
        if game_timed:
            credit_time(GAME_SECONDS)
    if any_lineup:
        timed = any(v[2] for v in onoff.values())
        print(f"{'player':24}{'+':>5}{'-':>5}{'net':>6}" + (f"{'min':>7}{'net/10min':>11}" if timed else ''))
        for p in players:
            f_, a_, sec = onoff[p]
            line = f"{p:24}{f_:>5}{a_:>5}{f_-a_:>6}"
            if timed and sec:
                line += f"{sec/60:>7.1f}{(f_-a_)/sec*600:>+11.1f}"
            print(line)
        if not timed:
            print("(no clock on lineup rows - minutes and rate columns skipped)")
    else:
        print("(no bench rows tagged yet)")

if __name__ == '__main__':
    main(sys.argv[1:] or ['data'])
