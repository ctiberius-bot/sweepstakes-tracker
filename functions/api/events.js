const HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "x-content-type-options": "nosniff",
};

const clean = (value, max) => String(value || "").replace(/[^\w./:@ -]/g, "").slice(0, max);

export async function onRequestPost({ request, env }) {
  const length = Number(request.headers.get("content-length") || "0");
  if (length > 4000) return new Response('{"ok":false}', { status: 413, headers: HEADERS });
  try {
    const body = await request.json();
    const event = clean(body.event, 60);
    if (!/^[a-z0-9_-]{1,60}$/i.test(event)) throw new Error("invalid event");
    const record = {
      type: "monetization_event",
      event,
      path: clean(body.path, 180),
      site: clean(body.site, 80),
      placement: clean(body.placement, 100),
      referrer: clean(body.referrer, 100),
      occurred_at: clean(body.occurred_at, 40),
      country: clean(request.cf?.country, 4),
    };
    console.log(JSON.stringify(record));
    if (!env.ANALYTICS_DB) throw new Error("analytics database unavailable");
    await env.ANALYTICS_DB.prepare(
      `INSERT INTO analytics_events
        (event, path, site, placement, referrer, country, occurred_at)
       VALUES (?, ?, ?, ?, ?, ?, ?)`
    ).bind(
      record.event,
      record.path,
      record.site,
      record.placement,
      record.referrer,
      record.country,
      record.occurred_at || new Date().toISOString()
    ).run();
    return new Response('{"ok":true}', { status: 202, headers: HEADERS });
  } catch (error) {
    console.error(JSON.stringify({
      type: "monetization_event_error",
      message: clean(error?.message, 160),
    }));
    return new Response('{"ok":false}', { status: 400, headers: HEADERS });
  }
}
