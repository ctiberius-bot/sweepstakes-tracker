#!/usr/bin/env python3
"""SQLite storage and JSON export for the SafeTracker winner archive."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent
DB_FILE = BASE / "data" / "winners.sqlite"
EXPORT_FILE = BASE / "data" / "winners.json"

SCHEMA = """
PRAGMA journal_mode=DELETE;
CREATE TABLE IF NOT EXISTS winner_reports (
    id TEXT PRIMARY KEY,
    raw_title TEXT NOT NULL,
    winner_name TEXT NOT NULL DEFAULT '',
    privacy_label TEXT NOT NULL DEFAULT '',
    promotion_name TEXT NOT NULL DEFAULT '',
    prize TEXT NOT NULL DEFAULT '',
    operator TEXT NOT NULL DEFAULT '',
    drawing_date TEXT,
    reported_at TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'community_report',
    source_url TEXT NOT NULL,
    verification_level TEXT NOT NULL DEFAULT 'source_reported',
    author TEXT NOT NULL DEFAULT '',
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    sent_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_winner_reported_at ON winner_reports(reported_at DESC);
CREATE INDEX IF NOT EXISTS idx_winner_drawing_date ON winner_reports(drawing_date DESC);
CREATE INDEX IF NOT EXISTS idx_winner_operator ON winner_reports(operator);
CREATE INDEX IF NOT EXISTS idx_winner_source ON winner_reports(source_id);
CREATE VIRTUAL TABLE IF NOT EXISTS winner_reports_fts USING fts5(
    raw_title, winner_name, privacy_label, promotion_name, prize, operator,
    source_name, author, content='winner_reports', content_rowid='rowid'
);
CREATE TRIGGER IF NOT EXISTS winner_reports_ai AFTER INSERT ON winner_reports BEGIN
    INSERT INTO winner_reports_fts(rowid, raw_title, winner_name, privacy_label, promotion_name, prize, operator, source_name, author)
    VALUES (new.rowid, new.raw_title, new.winner_name, new.privacy_label, new.promotion_name, new.prize, new.operator, new.source_name, new.author);
END;
CREATE TRIGGER IF NOT EXISTS winner_reports_ad AFTER DELETE ON winner_reports BEGIN
    INSERT INTO winner_reports_fts(winner_reports_fts, rowid, raw_title, winner_name, privacy_label, promotion_name, prize, operator, source_name, author)
    VALUES ('delete', old.rowid, old.raw_title, old.winner_name, old.privacy_label, old.promotion_name, old.prize, old.operator, old.source_name, old.author);
END;
CREATE TRIGGER IF NOT EXISTS winner_reports_au AFTER UPDATE ON winner_reports BEGIN
    INSERT INTO winner_reports_fts(winner_reports_fts, rowid, raw_title, winner_name, privacy_label, promotion_name, prize, operator, source_name, author)
    VALUES ('delete', old.rowid, old.raw_title, old.winner_name, old.privacy_label, old.promotion_name, old.prize, old.operator, old.source_name, old.author);
    INSERT INTO winner_reports_fts(rowid, raw_title, winner_name, privacy_label, promotion_name, prize, operator, source_name, author)
    VALUES (new.rowid, new.raw_title, new.winner_name, new.privacy_label, new.promotion_name, new.prize, new.operator, new.source_name, new.author);
END;
"""


def connect():
    DB_FILE.parent.mkdir(exist_ok=True)
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    return connection


def upsert_reports(connection, reports):
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    for report in reports:
        connection.execute(
            """
            INSERT INTO winner_reports (
                id, raw_title, winner_name, privacy_label, promotion_name, prize,
                operator, drawing_date, reported_at, source_id, source_name,
                source_type, source_url, verification_level, author,
                first_seen_at, last_seen_at
            ) VALUES (
                :id, :title, :winner_name, :privacy_label, :promotion_name, :prize,
                :operator, :drawing_date, :published_at, :source_id, :source_name,
                :source_type, :url, :verification_level, :author, :now, :now
            )
            ON CONFLICT(id) DO UPDATE SET
                raw_title=excluded.raw_title,
                source_url=excluded.source_url,
                last_seen_at=excluded.last_seen_at
            """,
            {
                **report,
                "winner_name": report.get("winner_name", ""),
                "privacy_label": report.get("privacy_label", ""),
                "promotion_name": report.get("promotion_name", ""),
                "prize": report.get("prize", ""),
                "operator": report.get("operator", ""),
                "drawing_date": report.get("drawing_date"),
                "source_type": report.get("source_type", "community_report"),
                "verification_level": report.get("verification_level", "source_reported"),
                "author": report.get("author", ""),
                "now": now,
            },
        )
    connection.commit()


def export_json(connection):
    rows = connection.execute(
        """
        SELECT id, raw_title AS title, winner_name, privacy_label, promotion_name,
               prize, operator, drawing_date, reported_at AS published_at,
               source_id, source_name, source_type, source_url AS url,
               verification_level, author, first_seen_at, last_seen_at, sent_at
        FROM winner_reports
        ORDER BY reported_at DESC
        """
    ).fetchall()
    winners = []
    for row in rows:
        item = dict(row)
        try:
            date = datetime.fromisoformat(item["published_at"].replace("Z", "+00:00"))
            item["published_display"] = date.strftime("%B %d, %Y").replace(" 0", " ")
        except ValueError:
            item["published_display"] = item["published_at"]
        winners.append(item)
    payload = {
        "schema_version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "count": len(winners),
        "winners": winners,
    }
    EXPORT_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return winners


def unsent_reports(connection):
    return [
        dict(row) for row in connection.execute(
            "SELECT * FROM winner_reports WHERE sent_at IS NULL ORDER BY reported_at ASC"
        ).fetchall()
    ]


def mark_sent(connection, report_ids):
    if not report_ids:
        return
    sent_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    connection.executemany(
        "UPDATE winner_reports SET sent_at = ? WHERE id = ?",
        [(sent_at, report_id) for report_id in report_ids],
    )
    connection.commit()
    export_json(connection)


if __name__ == "__main__":
    with connect() as database:
        exported = export_json(database)
    print(f"Winner database ready: {len(exported)} records")
