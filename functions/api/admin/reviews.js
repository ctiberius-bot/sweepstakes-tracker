import { getAdminIdentity, jsonResponse, unauthorized } from "../../_shared/access.js";

const loadAssetJson = async (request, env, path, fallback) => {
  if (!env.ASSETS) return fallback;
  const url = new URL(path, request.url);
  const response = await env.ASSETS.fetch(new Request(url, request));
  return response.ok ? response.json() : fallback;
};

export async function onRequestGet({ request, env }) {
  const identity = await getAdminIdentity(request, env);
  if (!identity) return unauthorized();
  if (!env.ANALYTICS_DB) {
    return jsonResponse({ ok: false, error: "Admin review database unavailable." }, 503);
  }

  const [queue, removals, decisions] = await Promise.all([
    loadAssetJson(request, env, "/data/discovery_candidates.json", { candidates: [] }),
    loadAssetJson(request, env, "/data/removal_candidates.json", { candidates: [] }),
    env.ANALYTICS_DB.prepare(`
      SELECT candidate_id, review_type, decision, classification, notes,
             reviewer_email, decided_at, updated_at
      FROM admin_review_decisions
      ORDER BY updated_at DESC
    `).all(),
  ]);

  return jsonResponse({
    ok: true,
    reviewer: identity,
    generated_at: new Date().toISOString(),
    discovery_updated_at: queue.updated_at || "",
    removal_updated_at: removals.updated_at || "",
    discoveries: queue.candidates || [],
    removals: removals.candidates || [],
    decisions: decisions.results || [],
  });
}
