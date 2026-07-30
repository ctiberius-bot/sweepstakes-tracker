const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "x-content-type-options": "nosniff",
};

const decodePart = (value) => {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "="));
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
};

const decodeJson = (value) =>
  JSON.parse(new TextDecoder().decode(decodePart(value)));

const teamOrigin = (value) => {
  const clean = String(value || "").trim().replace(/\/+$/, "");
  return clean.startsWith("https://") ? clean : `https://${clean}`;
};

export async function getAdminIdentity(request, env) {
  const token = request.headers.get("cf-access-jwt-assertion");
  const audience = String(env.CF_ACCESS_AUD || "").trim();
  const teamDomain = String(env.CF_ACCESS_TEAM_DOMAIN || "").trim();
  if (!token || !audience || !teamDomain) return null;

  try {
    const [encodedHeader, encodedPayload, encodedSignature] = token.split(".");
    if (!encodedHeader || !encodedPayload || !encodedSignature) return null;
    const header = decodeJson(encodedHeader);
    const payload = decodeJson(encodedPayload);
    if (header.alg !== "RS256" || !header.kid) return null;

    const certResponse = await fetch(`${teamOrigin(teamDomain)}/cdn-cgi/access/certs`, {
      cf: { cacheTtl: 300, cacheEverything: true },
    });
    if (!certResponse.ok) return null;
    const certs = await certResponse.json();
    const key = certs.keys?.find((candidate) => candidate.kid === header.kid);
    if (!key) return null;

    const cryptoKey = await crypto.subtle.importKey(
      "jwk",
      key,
      { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
      false,
      ["verify"],
    );
    const verified = await crypto.subtle.verify(
      "RSASSA-PKCS1-v1_5",
      cryptoKey,
      decodePart(encodedSignature),
      new TextEncoder().encode(`${encodedHeader}.${encodedPayload}`),
    );
    if (!verified) return null;

    const now = Math.floor(Date.now() / 1000);
    const audiences = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
    if (!audiences.includes(audience) || Number(payload.exp || 0) <= now) return null;

    const email = String(payload.email || "").trim().toLowerCase();
    const allowed = String(env.ADMIN_EMAILS || "")
      .split(",")
      .map((item) => item.trim().toLowerCase())
      .filter(Boolean);
    if (!email || (allowed.length && !allowed.includes(email))) return null;
    return { email, name: String(payload.name || email) };
  } catch {
    return null;
  }
}

export const unauthorized = () =>
  new Response(JSON.stringify({ ok: false, error: "Admin authentication required." }), {
    status: 401,
    headers: JSON_HEADERS,
  });

export const jsonResponse = (body, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: JSON_HEADERS });
