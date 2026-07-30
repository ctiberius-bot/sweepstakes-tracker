import { getAdminIdentity, jsonResponse, unauthorized } from "../../_shared/access.js";

const clean = (value, max) => String(value || "").trim().slice(0, max);
const allowedDecision = new Set(["approve", "reject", "defer", "clear"]);
const allowedClassification = new Set(["persistent", "limited", "needs_classification", "remove", "keep", ""]);

export async function onRequestPost({ request, env }) {
  const identity = await getAdminIdentity(request, env);
  if (!identity) return unauthorized();
  if (!env.ANALYTICS_DB) {
    return jsonResponse({ ok: false, error: "Admin review database unavailable." }, 503);
  }

  try {
    const body = await request.json();
    const candidateId = clean(body.candidate_id, 80);
    const reviewType = clean(body.review_type, 20);
    const decision = clean(body.decision, 20);
    const classification = clean(body.classification, 40);
    const notes = clean(body.notes, 2000);
    if (!candidateId || !["discovery", "removal"].includes(reviewType)) {
      return jsonResponse({ ok: false, error: "Invalid review record." }, 400);
    }
    if (!allowedDecision.has(decision) || !allowedClassification.has(classification)) {
      return jsonResponse({ ok: false, error: "Invalid decision." }, 400);
    }

    if (decision === "clear") {
      await env.ANALYTICS_DB.prepare(
        "DELETE FROM admin_review_decisions WHERE candidate_id = ? AND review_type = ?",
      ).bind(candidateId, reviewType).run();
    } else {
      await env.ANALYTICS_DB.prepare(`
        INSERT INTO admin_review_decisions
          (candidate_id, review_type, decision, classification, notes,
           reviewer_email, decided_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        ON CONFLICT(candidate_id, review_type) DO UPDATE SET
          decision = excluded.decision,
          classification = excluded.classification,
          notes = excluded.notes,
          reviewer_email = excluded.reviewer_email,
          updated_at = datetime('now')
      `).bind(
        candidateId,
        reviewType,
        decision,
        classification,
        notes,
        identity.email,
      ).run();
    }

    await env.ANALYTICS_DB.prepare(`
      INSERT INTO admin_review_audit
        (candidate_id, review_type, action, classification, notes, reviewer_email)
      VALUES (?, ?, ?, ?, ?, ?)
    `).bind(
      candidateId,
      reviewType,
      decision,
      classification,
      notes,
      identity.email,
    ).run();

    return jsonResponse({
      ok: true,
      candidate_id: candidateId,
      review_type: reviewType,
      decision,
      classification,
      reviewer_email: identity.email,
    });
  } catch (error) {
    return jsonResponse({ ok: false, error: clean(error?.message || "Unable to save decision.", 180) }, 400);
  }
}
