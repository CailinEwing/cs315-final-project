-- Gridiron Analytics: initial PostgreSQL/Supabase schema
-- Apply with the Supabase CLI or paste this file into the Supabase SQL editor.

create extension if not exists pg_trgm;

create table public.teams (
  abbreviation text primary key check (abbreviation ~ '^[A-Z]{2,3}$'),
  name text not null unique,
  conference text check (conference in ('AFC', 'NFC')),
  division text check (division in ('East', 'North', 'South', 'West')),
  logo_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.players (
  -- nflverse calls this player_id; it is the NFL GSIS identifier.
  gsis_id text primary key,
  display_name text not null,
  short_name text,
  position text not null,
  position_group text,
  headshot_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index players_position_idx on public.players (position);
create index players_display_name_trgm_idx
  on public.players using gin (display_name gin_trgm_ops);

create table public.player_season_stats (
  id bigint generated always as identity primary key,
  player_id text not null references public.players(gsis_id) on delete cascade,
  season smallint not null check (season between 1999 and 2100),
  season_type text not null check (season_type in ('REG', 'POST')),
  team_abbreviation text not null,
  games integer not null default 0 check (games >= 0),

  completions integer not null default 0 check (completions >= 0),
  attempts integer not null default 0 check (attempts >= 0),
  passing_yards integer not null default 0,
  passing_tds integer not null default 0 check (passing_tds >= 0),
  passing_interceptions integer not null default 0 check (passing_interceptions >= 0),
  sacks_suffered integer not null default 0 check (sacks_suffered >= 0),
  passing_first_downs integer not null default 0 check (passing_first_downs >= 0),
  passing_epa numeric,
  passing_cpoe numeric,

  carries integer not null default 0 check (carries >= 0),
  rushing_yards integer not null default 0,
  rushing_tds integer not null default 0 check (rushing_tds >= 0),
  targets integer not null default 0 check (targets >= 0),
  receptions integer not null default 0 check (receptions >= 0),
  receiving_yards integer not null default 0,
  receiving_tds integer not null default 0 check (receiving_tds >= 0),

  source text not null default 'nflverse',
  imported_at timestamptz not null default now(),
  unique (player_id, season, season_type, team_abbreviation),
  check (completions <= attempts)
);

create index player_season_stats_lookup_idx
  on public.player_season_stats (season, season_type, player_id);

-- One comparison-ready row per player/season. This safely combines rows if a
-- player represented more than one team during a season.
create view public.player_season_totals
with (security_invoker = true) as
select
  p.gsis_id as player_id,
  p.display_name,
  p.position,
  p.headshot_url,
  s.season,
  s.season_type,
  string_agg(distinct s.team_abbreviation, '/' order by s.team_abbreviation) as teams,
  sum(s.games)::integer as games,
  sum(s.completions)::integer as completions,
  sum(s.attempts)::integer as attempts,
  case when sum(s.attempts) = 0 then 0
       else round(100.0 * sum(s.completions) / sum(s.attempts), 1)
  end as completion_percentage,
  sum(s.passing_yards)::integer as passing_yards,
  sum(s.passing_tds)::integer as passing_tds,
  sum(s.passing_interceptions)::integer as passing_interceptions,
  sum(s.sacks_suffered)::integer as sacks_suffered,
  sum(s.passing_first_downs)::integer as passing_first_downs,
  round(sum(s.passing_epa), 2) as passing_epa,
  round(avg(s.passing_cpoe), 2) as passing_cpoe,
  sum(s.carries)::integer as carries,
  sum(s.rushing_yards)::integer as rushing_yards,
  sum(s.rushing_tds)::integer as rushing_tds,
  sum(s.targets)::integer as targets,
  sum(s.receptions)::integer as receptions,
  sum(s.receiving_yards)::integer as receiving_yards,
  sum(s.receiving_tds)::integer as receiving_tds
from public.players p
join public.player_season_stats s on s.player_id = p.gsis_id
group by p.gsis_id, p.display_name, p.position, p.headshot_url,
         s.season, s.season_type;

alter table public.teams enable row level security;
alter table public.players enable row level security;
alter table public.player_season_stats enable row level security;

-- The dashboard is public and read-only. Imports go through the trusted Flask
-- backend/database connection; browsers never receive the service-role key.
create policy "Public can read teams" on public.teams
  for select to anon, authenticated using (true);
create policy "Public can read players" on public.players
  for select to anon, authenticated using (true);
create policy "Public can read player stats" on public.player_season_stats
  for select to anon, authenticated using (true);

grant select on public.teams, public.players, public.player_season_stats
  to anon, authenticated;
grant select on public.player_season_totals to anon, authenticated;

