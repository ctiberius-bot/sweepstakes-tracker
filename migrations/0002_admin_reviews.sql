CREATE TABLE IF NOT EXISTS admin_review_decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  candidate_id TEXT NOT NULL,
  review_type TEXT NOT NULL CHECK (review_type IN ('discovery', 'removal')),
  decision TEXT NOT NULL CHECK (decision IN ('approve', 'reject', 'defer')),
  classification TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT '',
  reviewer_email TEXT NOT NULL,
  decided_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(candidate_id, review_type)
);

CREATE INDEX IF NOT EXISTS idx_admin_review_decisions_state
  ON admin_review_decisions(review_type, decision, updated_at);

CREATE TABLE IF NOT EXISTS admin_review_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  candidate_id TEXT NOT NULL,
  review_type TEXT NOT NULL,
  action TEXT NOT NULL,
  classification TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT '',
  reviewer_email TEXT NOT NULL,
  occurred_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_admin_review_audit_candidate
  ON admin_review_audit(candidate_id, review_type, occurred_at);
