"""Flask API for Gridiron Analytics."""

from __future__ import annotations

import os
import re

import psycopg
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from psycopg.rows import dict_row


# Load the .env file from the repository root when running locally.
load_dotenv()

app = Flask(__name__)
CORS(app)


@app.get("/api/players")
def get_players():
    """Return players at a position who have statistics for a season."""
    position = request.args.get("position", "QB").strip().upper()
    season_text = request.args.get("season", "2024").strip()

    if not re.fullmatch(r"[A-Z]{1,3}", position):
        return jsonify({"error": "position must be 1-3 letters"}), 400

    try:
        season = int(season_text)
    except ValueError:
        return jsonify({"error": "season must be a number"}), 400

    if season < 1999 or season > 2100:
        return jsonify({"error": "season must be between 1999 and 2100"}), 400

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return jsonify({"error": "Server is missing DATABASE_URL"}), 500

    sql = """
        select
          player_id,
          display_name,
          position,
          teams,
          season
        from public.player_season_totals
        where position = %s
          and season = %s
          and season_type = 'REG'
        order by display_name
    """

    try:
        with psycopg.connect(database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, (position, season))
                players = cursor.fetchall()
    except psycopg.Error:
        # Do not expose database credentials or detailed server errors to clients.
        app.logger.exception("Database query failed")
        return jsonify({"error": "Could not query the database"}), 500

    return jsonify({
        "count": len(players),
        "position": position,
        "season": season,
        "players": players,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)

