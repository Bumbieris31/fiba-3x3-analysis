#!/usr/bin/env python3
"""Prefill a tagging CSV from FIBA's official play-by-play feed.

Downloads the scorekeeper feed for a game and converts it to the tagger's CSV
format, so made shots, free throws and team fouls (all with clock times) are
already filled in. You then import the CSV into tagger.html and only tag the
rest from video: misses, rebounds, assists, turnovers, blocks/steals, bench,
and foul attribution.

Usage:
    python3 prefill.py <game url or game id> [-o data/S1-G1.csv]
                       [--game S1-G1] [--round Pool]

    The game URL is any page of the game on nationsleague.fiba3x3.com, e.g.
    https://nationsleague.fiba3x3.com/2026/europe-2-stop-1/games/<id>/play-by-play

What lands in the CSV:
    * every made field goal: player, 1pt/2pt, clock
    * free throws: makes attributed to the shooter; a missed FT is attributed
      via its trip (same award -> same shooter) when possible, else left
      unattributed (blank player - fix it while tagging if you care)
    * team fouls for both sides with clock (player left blank - FIBA doesn't
      record who committed it; add `fould`/edit rows from video if you want
      the individual foul ledger)
Not in the feed, still yours to tag: FG misses, rebounds, assists, turnovers,
blocks, steals, bench changes, matchups.
"""
import json, re, sys, argparse, urllib.request

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/140.0 Safari/537.36')

def fetch(game_id):
    url = f'https://nationsleague.fiba3x3.com/api/v2/game/{game_id}/playbyplay/scoring'
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req) as r:
        return json.load(r)

def clock(ms):
    s = round(ms / 1000)
    return f'{s // 60}:{s % 60:02d}'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('game', help='game page URL or game id')
    ap.add_argument('-o', '--out', help='output CSV path (default: stdout)')
    ap.add_argument('--game-label', default=None, help='game id column value, e.g. S1-G1')
    ap.add_argument('--round', default='Pool', help='round column value (default Pool)')
    ap.add_argument('--team', default='Latvia', help='which teamName is "ours" (default Latvia)')
    args = ap.parse_args()

    m = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', args.game)
    if not m:
        sys.exit('Could not find a game id in the argument.')
    feed = fetch(m.group(0))

    if feed['homeTeam']['teamName'] == args.team:
        us, them = feed['homeTeam'], feed['awayTeam']
    elif feed['awayTeam']['teamName'] == args.team:
        us, them = feed['awayTeam'], feed['homeTeam']
    else:
        sys.exit(f'Neither team is "{args.team}" in this game '
                 f"({feed['homeTeam']['teamName']} vs {feed['awayTeam']['teamName']}).")
    names = {p['id']: p['lastName'] for p in feed['players']}
    jerseys = {p['id']: (p.get('jerseyNumber') or '') for p in feed['players']}
    label = args.game_label or 'G-' + m.group(0)[:8]
    side = lambda tid: 'LAT' if tid == us['teamId'] else 'OPP'

    # attribute missed FTs via their trip: consecutive FT actions at the same
    # remainingTime belong to one shooter
    actions = feed['actions']
    trip_shooter = {}
    for a in actions:
        if a['isFreeThrow'] and a.get('playerId'):
            trip_shooter[a['remainingTime']] = a['playerId']

    rows = []
    for a in actions:
        t = a['type']
        if t == 'ScoreAction':
            pid = a.get('playerId') or trip_shooter.get(a['remainingTime'])
            player = names.get(pid, '')
            jersey = jerseys.get(pid, '')
            if a['isFreeThrow']:
                rows.append((a['remainingTime'], side(a['teamId']), player, 'ft',
                             'make' if a['points'] else 'miss', '', jersey))
            else:
                ev = 'shot2' if a['points'] == 2 else 'shot1'
                rows.append((a['remainingTime'], side(a['teamId']), player, ev, 'make', '', jersey))
        elif t == 'FoulAction':
            rows.append((a['remainingTime'], side(a['teamId']), '', 'foul', '', '', ''))

    out = ['game,opponent,round,clock,team,player,event,result,related,jersey']
    for ms, team, player, ev, res, rel, jer in rows:
        out.append(','.join([label, them['teamName'], args.round, clock(ms), team, player, ev, res, rel, jer]))
    text = '\n'.join(out) + '\n'
    if args.out:
        open(args.out, 'w', encoding='utf-8').write(text)
        made = sum(1 for r in rows if r[4] == 'make')
        print(f'{args.out}: {len(rows)} prefilled events ({made} makes) — '
              f'{us["teamName"]} vs {them["teamName"]}')
    else:
        print(text, end='')

if __name__ == '__main__':
    main()
