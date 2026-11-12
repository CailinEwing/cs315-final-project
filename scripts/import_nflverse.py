"""Import an nflverse regular-season summary CSV into PostgreSQL/Supabase."""

from __future__ import annotations

import argparse
import csv
import io
import os
import urllib.request

import psycopg


URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "stats_player/stats_player_reg_{season}.csv"
)


def integer(row: dict[str, str], name: str) -> int:
    value = row.get(name, "")
    return int(float(value)) if value not in ("", "NA", "NaN") else 0


def decimal(row: dict[str, str], name: str) -> float | None:
    value = row.get(name, "")
    return float(value) if value not in ("", "NA", "NaN") else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("season", type=int, help="NFL season, for example 2024")
    parser.add_argument("--all-positions", action="store_true")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("Set DATABASE_URL to the Supabase direct or session-pooler URL")

    url = URL.format(season=args.season)
    print(f"Downloading {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "gridiron-analytics/1.0"})
    with urllib.request.urlopen(request) as response:
        text = response.read().decode("utf-8-sig")

    rows = list(csv.DictReader(io.StringIO(text)))
    if not args.all_positions:
        rows = [row for row in rows if row.get("position") == "QB"]

    player_sql = """
        insert into public.players
          (gsis_id, display_name, short_name, position, position_group, headshot_url)
        values (%s, %s, %s, %s, %s, %s)
        on conflict (gsis_id) do update set
          display_name = excluded.display_name,
          short_name = excluded.short_name,
          position = excluded.position,
          position_group = excluded.position_group,
          headshot_url = excluded.headshot_url,
          updated_at = now()
    """
    stats_sql = """
        insert into public.player_season_stats
          (player_id, season, season_type, team_abbreviation, games,
           completions, attempts, passing_yards, passing_tds,
           passing_interceptions, sacks_suffered, passing_first_downs,
           passing_epa, passing_cpoe, carries, rushing_yards, rushing_tds,
           targets, receptions, receiving_yards, receiving_tds)
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (player_id, season, season_type, team_abbreviation)
        do update set
          games = excluded.games, completions = excluded.completions,
          attempts = excluded.attempts, passing_yards = excluded.passing_yards,
          passing_tds = excluded.passing_tds,
          passing_interceptions = excluded.passing_interceptions,
          sacks_suffered = excluded.sacks_suffered,
          passing_first_downs = excluded.passing_first_downs,
          passing_epa = excluded.passing_epa, passing_cpoe = excluded.passing_cpoe,
          carries = excluded.carries, rushing_yards = excluded.rushing_yards,
          rushing_tds = excluded.rushing_tds, targets = excluded.targets,
          receptions = excluded.receptions,
          receiving_yards = excluded.receiving_yards,
          receiving_tds = excluded.receiving_tds, imported_at = now()
    """

    imported = 0
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            for row in rows:
                player_id = row.get("player_id")
                team = row.get("team")
                if not player_id or not team:
                    continue
                cursor.execute(player_sql, (
                    player_id, row.get("player_display_name") or row.get("player_name"),
                    row.get("player_name"), row.get("position") or "UNK",
                    row.get("position_group"), row.get("headshot_url"),
                ))
                cursor.execute(stats_sql, (
                    player_id, args.season, row.get("season_type") or "REG", team,
                    integer(row, "games"), integer(row, "completions"),
                    integer(row, "attempts"), integer(row, "passing_yards"),
                    integer(row, "passing_tds"), integer(row, "passing_interceptions"),
                    integer(row, "sacks_suffered"), integer(row, "passing_first_downs"),
                    decimal(row, "passing_epa"), decimal(row, "passing_cpoe"),
                    integer(row, "carries"), integer(row, "rushing_yards"),
                    integer(row, "rushing_tds"), integer(row, "targets"),
                    integer(row, "receptions"), integer(row, "receiving_yards"),
                    integer(row, "receiving_tds"),
                ))
                imported += 1

    print(f"Imported {imported} player-season rows for {args.season}")


if __name__ == "__main__":
    main()

