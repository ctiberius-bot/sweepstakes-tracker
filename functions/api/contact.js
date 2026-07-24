const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "x-content-type-options": "nosniff",
};

const TOPICS = new Set([
  "correction",
  "site-suggestion",
  "winner-report",
  "privacy",
  "business",
  "other",
]);

function json(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: JSON_HEADERS });
}

function clean(value, maxLength) {
  return String(value || "").replace(/\0/g, "").trim().slice(0, maxLength);
}

function isEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) && value.length <= 254;
}

function isPublicHttpUrl(value) {
  if (!value) return true;
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol);
  } catch {
    return false;
  }
}

async function rateLimit(env, ip) {
  if (!env.CONTACT_RATE_LIMIT) throw new Error("Rate-limit storage is unavailable.");
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(ip));
  const key = `contact:${Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
  const count = Number(await env.CONTACT_RATE_LIMIT.get(key) || "0");
  if (count >= 3) return false;
  await env.CONTACT_RATE_LIMIT.put(key, String(count + 1), { expirationTtl: 600 });
  return true;
}

async function verifyTurnstile(env, token, ip, hostname) {
  const response = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      secret: env.TURNSTILE_SECRET_KEY,
      response: token,
      remoteip: ip,
      idempotency_key: crypto.randomUUID(),
    }),
  });
  const result = await response.json();
  return Boolean(
    result.success &&
    result.action === "contact" &&
    (!result.hostname || result.hostname === hostname)
  );
}

async function sendMessage(env, submission) {
  const subject = `[SafeTracker contact] ${submission.topic}: ${submission.name}`;
  const response = await fetch("https://api.web3forms.com/submit", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      accept: "application/json",
    },
    body: JSON.stringify({
      access_key: env.WEB3FORMS_ACCESS_KEY,
      subject,
      from_name: "SafeTracker contact form",
      name: submission.name,
      email: submission.email,
      topic: submission.topic,
      source_url: submission.sourceUrl || "Not supplied",
      message: submission.message,
    }),
  });
  const result = await response.json();
  if (!response.ok || !result.success) {
    console.error("Contact delivery failed", response.status);
    throw new Error("Delivery failed.");
  }
}

export async function onRequestGet(context) {
  if (!context.env.TURNSTILE_SITE_KEY) return json({ message: "Contact form is not configured." }, 503);
  return json({ siteKey: context.env.TURNSTILE_SITE_KEY });
}

export async function onRequestPost(context) {
  const { request, env } = context;
  const requestUrl = new URL(request.url);
  const origin = request.headers.get("origin");
  try {
    if (origin && new URL(origin).host !== requestUrl.host) return json({ message: "Invalid request origin." }, 403);
  } catch {
    return json({ message: "Invalid request origin." }, 403);
  }

  const contentLength = Number(request.headers.get("content-length") || "0");
  if (contentLength > 20_000) return json({ message: "Message is too large." }, 413);

  let form;
  try {
    form = await request.formData();
  } catch {
    return json({ message: "Invalid form submission." }, 400);
  }

  // Honeypot: return an ordinary success response so automated senders do not adapt.
  if (clean(form.get("company_url"), 200)) return json({ ok: true });

  const startedAt = Number(form.get("form_started_at"));
  const elapsed = Date.now() - startedAt;
  if (!Number.isFinite(startedAt) || elapsed < 3000 || elapsed > 7_200_000) {
    return json({ message: "Please refresh the page and try again." }, 400);
  }

  const submission = {
    name: clean(form.get("name"), 100),
    email: clean(form.get("email"), 254),
    topic: clean(form.get("topic"), 40),
    sourceUrl: clean(form.get("source_url"), 500),
    message: clean(form.get("message"), 5000),
  };
  if (
    submission.name.length < 2 ||
    !isEmail(submission.email) ||
    !TOPICS.has(submission.topic) ||
    !isPublicHttpUrl(submission.sourceUrl) ||
    submission.message.length < 20
  ) {
    return json({ message: "Please check the form fields and try again." }, 400);
  }

  const required = ["TURNSTILE_SECRET_KEY", "WEB3FORMS_ACCESS_KEY"];
  if (required.some((key) => !env[key])) {
    console.error("Contact form configuration is incomplete.");
    return json({ message: "The contact form is temporarily unavailable." }, 503);
  }

  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  if (!(await rateLimit(env, ip))) {
    return json({ message: "Too many messages. Please try again in ten minutes." }, 429);
  }

  const token = clean(form.get("cf-turnstile-response"), 2048);
  if (!token || !(await verifyTurnstile(env, token, ip, requestUrl.hostname))) {
    return json({ message: "Human verification failed. Please try again." }, 400);
  }

  try {
    await sendMessage(env, submission);
    return json({ ok: true });
  } catch {
    return json({ message: "Your message could not be delivered. Please try again later." }, 502);
  }
}
