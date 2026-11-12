# Gridiron Analytics database setup

## Recommended data source

Use **nflverse Player Summary Stats** for the class project. Its season files
already contain the fields needed by the MVP: stable `player_id` (GSIS ID),
name, position, team, completions, attempts, passing yards, passing touchdowns,
interceptions, EPA, and CPOE. The source supports CSV/Parquet downloads and the
Python ecosystem, so the data can be imported without depending on a paid API
during the live demonstration.

Important: nflverse is a community dataset, not an official NFL API. Record its
attribution/license in the final report and keep a downloaded CSV as the demo
backup. Do not call the GitHub download from React; import server-side into
PostgreSQL.

Useful references:

- Player stats docs: https://nflreadr.nflverse.com/reference/load_player_stats
- Field dictionary: https://nflreadr.nflverse.com/articles/dictionary_player_stats.html
- Releases: https://github.com/nflverse/nflverse-data/releases/tag/stats_player
- Python loader project: https://github.com/nflverse/nflreadpy
- Supabase migration workflow: https://supabase.com/docs/guides/local-development/cli-workflows

## Create the hosted Supabase project

1. Create a project at https://database.new and save the database password in a
   password manager.
2. In the SQL Editor, open and run
   `supabase/migrations/202611020001_initial_gridiron_schema.sql`.
3. For sample data, run `supabase/seed.sql` in the SQL Editor.
4. Open Table Editor and confirm `players` has two rows. In SQL Editor run:

   ```sql
   select * from public.player_season_totals
   where season = 2023 and position = 'QB';
   ```

The schema enables Row Level Security. Anonymous clients can read these public
sports statistics but cannot insert, update, or delete them. Keep Supabase's
service-role key and database password on the Flask server only. The React app
should normally call Flask, matching the architecture in the proposal.

## Team-friendly CLI workflow (recommended)

Install Docker Desktop and the Supabase CLI, then from the repository root:

```powershell
supabase init
supabase start
supabase db reset
supabase link --project-ref YOUR_PROJECT_REF
supabase db push --remote
```

The migration and seed files should be committed. Real `.env` files and keys
must not be committed. Each future schema change should be a new migration:

```powershell
supabase migration new describe_the_change
supabase db reset
supabase db push --remote
```

## Import a real NFL season

Create and activate a virtual environment, install the importer dependency, and
set the database URL shown by Supabase under **Connect**. Prefer the direct URL
or session pooler for this short-lived import script.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-import.txt
$env:DATABASE_URL = 'YOUR_SUPABASE_POSTGRES_CONNECTION_STRING'
py scripts/import_nflverse.py 2024
```

By default only quarterbacks are imported, which keeps the MVP small. Add
`--all-positions` when the group is ready for RB/WR comparisons. Re-running the
command updates existing rows instead of duplicating them.

The nflverse season-summary CSV currently names the player's team column
`recent_team`. The importer also accepts the older `team` name for compatibility.

## Queries for the Flask API

List quarterbacks for a season:

```sql
select player_id, display_name, teams
from public.player_season_totals
where position = 'QB' and season = %s and season_type = 'REG'
order by display_name;
```

Compare two players:

```sql
select *
from public.player_season_totals
where season = %s
  and season_type = 'REG'
  and player_id = any(%s)
order by display_name;
```

Validate in Flask that the season is an integer and exactly two distinct player
IDs were supplied. Use SQL parameters as shown; never construct SQL by joining
request strings.

## Suggested API endpoints

- `GET /api/seasons`
- `GET /api/players?position=QB&season=2024`
- `GET /api/compare?season=2024&player_ids=ID1,ID2`
- `GET /api/health`

For the final demo, retain the 2023 seed data and a downloaded nflverse CSV.
That makes the comparison usable even if the external data host is unavailable.
