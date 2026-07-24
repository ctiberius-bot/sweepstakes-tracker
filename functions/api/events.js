const HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "x-content-type-options": "nosniff",
};

const clean = (value, max) => String(value || "").replace(/[^\w./:@ -]/g, "").slice(0, max);

export async function onRequestPost({ request }) {
  const length = Number(request.headers.get("content-length") || "0");
  if (length > 4000) return new Response('{"ok":false}', { status: 413, headers: HEADERS });
  try {
    const body = await request.json();
    const event = clean(body.event, 60);
    if (!/^[a-z0-9_-]{1,60}$/i.test(event)) throw new Error("invalid event");
    console.log(JSON.stringify({
      type: "monetization_event",
      event,
      path: clean(body.path, 180),
      site: clean(body.site, 80),
      placement: clean(body.placement, 100),
      referrer: clean(body.referrer, 100),
      occurred_at: clean(body.occurred_at, 40),
      country: clean(request.cf?.country, 4),
    }));
    return new Response('{"ok":true}', { status: 202, headers: HEADERS });
  } catch {
    return new Response('{"ok":false}', { status: 400, headers: HEADERS });
  }
}
