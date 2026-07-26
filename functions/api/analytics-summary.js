const HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "public, max-age=300",
  "x-content-type-options": "nosniff",
};

export async function onRequestGet({ env }) {
  if (!env.ANALYTICS_DB) {
    return new Response('{"ok":false,"error":"analytics unavailable"}', {
      status: 503,
      headers: HEADERS,
    });
  }

  const [totals, events, operators, daily] = await env.ANALYTICS_DB.batch([
    env.ANALYTICS_DB.prepare(`
      SELECT
        COALESCE(SUM(CASE WHEN received_at >= datetime('now', '-7 days') THEN 1 ELSE 0 END), 0) AS events_7d,
        COALESCE(SUM(CASE WHEN received_at >= datetime('now', '-30 days') THEN 1 ELSE 0 END), 0) AS events_30d,
        COALESCE(SUM(CASE WHEN event = 'page_view' AND received_at >= datetime('now', '-7 days') THEN 1 ELSE 0 END), 0) AS page_views_7d,
        COALESCE(SUM(CASE WHEN event = 'page_view' AND received_at >= datetime('now', '-30 days') THEN 1 ELSE 0 END), 0) AS page_views_30d,
        COALESCE(SUM(CASE WHEN event IN ('outbound_click', 'sweepstakes_entry_click') AND received_at >= datetime('now', '-7 days') THEN 1 ELSE 0 END), 0) AS outbound_clicks_7d,
        COALESCE(SUM(CASE WHEN event IN ('outbound_click', 'sweepstakes_entry_click') AND received_at >= datetime('now', '-30 days') THEN 1 ELSE 0 END), 0) AS outbound_clicks_30d
      FROM analytics_events
    `),
    env.ANALYTICS_DB.prepare(`
      SELECT event,
        SUM(CASE WHEN received_at >= datetime('now', '-7 days') THEN 1 ELSE 0 END) AS count_7d,
        COUNT(*) AS count_30d
      FROM analytics_events
      WHERE received_at >= datetime('now', '-30 days')
      GROUP BY event
      ORDER BY count_30d DESC, event
    `),
    env.ANALYTICS_DB.prepare(`
      SELECT site,
        SUM(CASE WHEN received_at >= datetime('now', '-7 days') THEN 1 ELSE 0 END) AS clicks_7d,
        COUNT(*) AS clicks_30d
      FROM analytics_events
      WHERE event IN ('outbound_click', 'sweepstakes_entry_click')
        AND received_at >= datetime('now', '-30 days')
        AND site != ''
      GROUP BY site
      ORDER BY clicks_30d DESC, site
      LIMIT 50
    `),
    env.ANALYTICS_DB.prepare(`
      SELECT date(received_at) AS date,
        SUM(CASE WHEN event = 'page_view' THEN 1 ELSE 0 END) AS page_views,
        SUM(CASE WHEN event IN ('outbound_click', 'sweepstakes_entry_click') THEN 1 ELSE 0 END) AS outbound_clicks,
        COUNT(*) AS events
      FROM analytics_events
      WHERE received_at >= datetime('now', '-30 days')
      GROUP BY date(received_at)
      ORDER BY date(received_at)
    `),
  ]);

  return new Response(JSON.stringify({
    ok: true,
    generated_at: new Date().toISOString(),
    baseline: totals.results[0] || {},
    events: events.results,
    operators: operators.results,
    daily: daily.results,
  }), { headers: HEADERS });
}
