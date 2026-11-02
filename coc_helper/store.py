"""SQLite persistence."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .api import WarResult, normalize_tag
from .stats import member_stats

SCHEMA = """
CREATE TABLE IF NOT EXISTS clans (
    tag TEXT PRIMARY KEY,
    name TEXT,
    level INTEGER,
    members INTEGER,
    raw TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS wars (
    war_key TEXT NOT NULL,
    clan_tag TEXT NOT NULL,
    kind TEXT NOT NULL,
    our_side TEXT,
    war_tag TEXT,
    state TEXT,
    team_size INTEGER,
    attacks_per_member INTEGER,
    start_time TEXT,
    end_time TEXT,
    opponent_tag TEXT,
    opponent_name TEXT,
    our_stars INTEGER,
    our_destruction REAL,
    their_stars INTEGER,
    their_destruction REAL,
    raw TEXT,
    fetched_at TEXT,
    PRIMARY KEY (war_key, clan_tag)
);

CREATE TABLE IF NOT EXISTS war_members (
    war_key TEXT NOT NULL,
    clan_tag TEXT NOT NULL,
    side TEXT NOT NULL,
    player_tag TEXT NOT NULL,
    name TEXT,
    townhall INTEGER,
    map_position INTEGER,
    attacks_allowed INTEGER,
    attacks_used INTEGER,
    stars INTEGER,
    destruction REAL,
    three_star INTEGER,
    PRIMARY KEY (war_key, clan_tag, side, player_tag)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self._migrate()
        self.conn.commit()

    def _migrate(self) -> None:
        columns = {
            row["name"] for row in self.conn.execute("PRAGMA table_info(war_members)")
        }
        if "attacks_allowed" not in columns:
            self.conn.execute(
                "ALTER TABLE war_members ADD COLUMN attacks_allowed INTEGER"
            )

    def close(self) -> None:
        self.conn.close()

    def upsert_clan(self, clan: dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT INTO clans (tag, name, level, members, raw, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(tag) DO UPDATE SET
                name = excluded.name,
                level = excluded.level,
                members = excluded.members,
                raw = excluded.raw,
                updated_at = excluded.updated_at
            """,
            (
                clan.get("tag"),
                clan.get("name"),
                clan.get("clanLevel"),
                len(clan.get("memberList") or []),
                json.dumps(clan, ensure_ascii=False),
                _now(),
            ),
        )
        self.conn.commit()

    def upsert_war(self, clan_tag: str, result: WarResult) -> str:
        clan_tag = normalize_tag(clan_tag)
        war = result.war
        our = war.get(result.our_side) or {}
        their = war.get("opponent" if result.our_side == "clan" else "clan") or {}
        war_key = result.war_tag or f"regular:{war.get('startTime')}:{clan_tag}"

        self.conn.execute(
            """
            INSERT INTO wars (
                war_key, clan_tag, kind, our_side, war_tag, state, team_size, attacks_per_member,
                start_time, end_time, opponent_tag, opponent_name,
                our_stars, our_destruction, their_stars, their_destruction, raw, fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(war_key, clan_tag) DO UPDATE SET
                kind = excluded.kind,
                our_side = excluded.our_side,
                war_tag = excluded.war_tag,
                state = excluded.state,
                team_size = excluded.team_size,
                attacks_per_member = excluded.attacks_per_member,
                start_time = excluded.start_time,
                end_time = excluded.end_time,
                opponent_tag = excluded.opponent_tag,
                opponent_name = excluded.opponent_name,
                our_stars = excluded.our_stars,
                our_destruction = excluded.our_destruction,
                their_stars = excluded.their_stars,
                their_destruction = excluded.their_destruction,
                raw = excluded.raw,
                fetched_at = excluded.fetched_at
            """,
            (
                war_key,
                clan_tag,
                result.kind,
                result.our_side,
                result.war_tag,
                war.get("state"),
                war.get("teamSize"),
                war.get("attacksPerMember"),
                war.get("startTime"),
                war.get("endTime"),
                their.get("tag"),
                their.get("name"),
                our.get("stars"),
                our.get("destructionPercentage"),
                their.get("stars"),
                their.get("destructionPercentage"),
                json.dumps(war, ensure_ascii=False),
                _now(),
            ),
        )

        default_attacks = 1 if result.kind == "cwl" else 2
        for side in ("clan", "opponent"):
            for row in member_stats(war, side, default_attacks):
                self.conn.execute(
                    """
                    INSERT INTO war_members (
                        war_key, clan_tag, side, player_tag, name, townhall, map_position,
                        attacks_allowed, attacks_used, stars, destruction, three_star
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(war_key, clan_tag, side, player_tag) DO UPDATE SET
                        name = excluded.name,
                        townhall = excluded.townhall,
                        map_position = excluded.map_position,
                        attacks_allowed = excluded.attacks_allowed,
                        attacks_used = excluded.attacks_used,
                        stars = excluded.stars,
                        destruction = excluded.destruction,
                        three_star = excluded.three_star
                    """,
                    (
                        war_key,
                        clan_tag,
                        side,
                        row.tag,
                        row.name,
                        row.townhall,
                        row.map_position,
                        row.attacks_allowed,
                        row.attacks_used,
                        row.stars,
                        row.destruction,
                        row.three_star,
                    ),
                )

        self.conn.commit()
        return war_key

    def recent_wars(self, clan_tag: str, limit: int = 10) -> list[dict[str, Any]]:
        clan_tag = normalize_tag(clan_tag)
        rows = self.conn.execute(
            """
            SELECT war_key, kind, start_time, end_time, opponent_name,
                   our_stars, their_stars, our_destruction, their_destruction
            FROM wars
            WHERE clan_tag = ? AND state = 'warEnded'
            ORDER BY COALESCE(end_time, start_time, fetched_at) DESC
            LIMIT ?
            """,
            (clan_tag, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def member_history(
        self, clan_tag: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        clan_tag = normalize_tag(clan_tag)
        rows = self.conn.execute(
            """
            SELECT wm.player_tag,
                   MAX(wm.name) AS name,
                   COUNT(DISTINCT wm.war_key) AS wars,
                   SUM(COALESCE(wm.attacks_used, 0)) AS attacks_used,
                   SUM(COALESCE(wm.attacks_allowed, 0)) AS attacks_allowed,
                   SUM(COALESCE(wm.stars, 0)) AS stars,
                   SUM(COALESCE(wm.destruction, 0)) AS destruction,
                   SUM(COALESCE(wm.three_star, 0)) AS three_star
            FROM war_members wm
            JOIN (
                SELECT war_key, clan_tag, our_side
                FROM wars
                WHERE clan_tag = ? AND state = 'warEnded'
                ORDER BY COALESCE(end_time, start_time, fetched_at) DESC
                LIMIT ?
            ) w ON w.war_key = wm.war_key AND w.clan_tag = wm.clan_tag
            WHERE wm.clan_tag = ? AND wm.side = w.our_side
            GROUP BY wm.player_tag
            ORDER BY
                SUM(COALESCE(wm.three_star, 0)) * 1.0
                / NULLIF(SUM(COALESCE(wm.attacks_used, 0)), 0) DESC,
                SUM(COALESCE(wm.attacks_used, 0)) DESC
            """,
            (clan_tag, limit, clan_tag),
        ).fetchall()
        return [dict(row) for row in rows]
