CREATE TABLE IF NOT EXISTS analytics_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event TEXT NOT NULL,
  path TEXT NOT NULL DEFAULT '',
  site TEXT NOT NULL DEFAULT '',
  placement TEXT NOT NULL DEFAULT '',
  referrer TEXT NOT NULL DEFAULT '',
  country TEXT NOT NULL DEFAULT '',
  occurred_at TEXT NOT NULL,
  received_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_analytics_events_received_at
  ON analytics_events(received_at);
CREATE INDEX IF NOT EXISTS idx_analytics_events_event_received
  ON analytics_events(event, received_at);
CREATE INDEX IF NOT EXISTS idx_analytics_events_site_received
  ON analytics_events(site, received_at);
