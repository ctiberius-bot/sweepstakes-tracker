(() => {
  const allowed = /^[a-z0-9_-]{1,60}$/i;
  function track(event, details = {}) {
    if (!allowed.test(event)) return;
    const payload = JSON.stringify({
      event,
      path: location.pathname,
      site: String(details.site || "").slice(0, 80),
      placement: String(details.placement || details.package || "").slice(0, 100),
      referrer: document.referrer ? new URL(document.referrer).hostname : "",
      occurred_at: new Date().toISOString(),
    });
    if (navigator.sendBeacon) {
      navigator.sendBeacon("/api/events", new Blob([payload], { type: "application/json" }));
    } else {
      fetch("/api/events", { method: "POST", headers: { "content-type": "application/json" }, body: payload, keepalive: true }).catch(() => {});
    }
  }
  window.SafeTrackerTrack = track;
  document.addEventListener("click", (event) => {
    const link = event.target.closest("[data-track]");
    if (!link) return;
    track(link.dataset.track, { site: link.dataset.site, placement: link.dataset.placement });
  });
  document.addEventListener("submit", (event) => {
    const form = event.target.closest("form");
    if (!form) return;
    const tracked = form.closest("[data-track-form]");
    const newsletter = form.closest("[data-winner-signal-signup]") || /(?:kit|convertkit)\.com\/forms\//i.test(form.action);
    if (tracked) track(tracked.dataset.trackForm, { placement: form.getAttribute("action") });
    else if (newsletter) track("newsletter_signup", { placement: form.getAttribute("action") });
  });
  const campaign = new URLSearchParams(location.search);
  const source = campaign.get("utm_source") || "";
  const medium = campaign.get("utm_medium") || "";
  const name = campaign.get("utm_campaign") || "";
  track("page_view", {
    site: medium,
    placement: [source, name].filter(Boolean).join(":"),
  });
})();
