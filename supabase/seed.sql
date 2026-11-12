-- Small deterministic dataset for local development and the first demo.
insert into public.players
  (gsis_id, display_name, short_name, position, position_group)
values
  ('00-0033873', 'Patrick Mahomes', 'P.Mahomes', 'QB', 'QB'),
  ('00-0034857', 'Josh Allen', 'J.Allen', 'QB', 'QB')
on conflict (gsis_id) do update set
  display_name = excluded.display_name,
  short_name = excluded.short_name,
  position = excluded.position,
  position_group = excluded.position_group;

insert into public.player_season_stats
  (player_id, season, season_type, team_abbreviation, games, completions,
   attempts, passing_yards, passing_tds, passing_interceptions)
values
  ('00-0033873', 2023, 'REG', 'KC', 16, 401, 597, 4183, 27, 14),
  ('00-0034857', 2023, 'REG', 'BUF', 17, 385, 579, 4306, 29, 18)
on conflict (player_id, season, season_type, team_abbreviation) do update set
  games = excluded.games,
  completions = excluded.completions,
  attempts = excluded.attempts,
  passing_yards = excluded.passing_yards,
  passing_tds = excluded.passing_tds,
  passing_interceptions = excluded.passing_interceptions,
  imported_at = now();

