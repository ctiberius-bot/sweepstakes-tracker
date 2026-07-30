const state = {
  records: [],
  decisions: new Map(),
  filtered: [],
  page: 1,
  pageSize: 30,
  selected: null,
};

const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[character]));
const displayDate = (value) => {
  if (!value) return "Not recorded";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
};
const decisionKey = (record) => `${record.review_type}:${record.id}`;

async function loadReviews() {
  $("#refresh").disabled = true;
  try {
    const response = await fetch("/api/admin/reviews", { credentials: "same-origin" });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || "Unable to load review queue.");
    state.decisions = new Map(data.decisions.map((item) => [`${item.review_type}:${item.candidate_id}`, item]));
    const discoveries = data.discoveries.map((item) => ({ ...item, review_type: "discovery" }));
    const removals = data.removals.map((item) => ({ ...item, review_type: "removal", candidate_type: "removal" }));
    state.records = [...removals, ...discoveries];
    $("#identity").textContent = data.reviewer.email;
    $("#freshness").textContent = `Discovery queue refreshed ${displayDate(data.discovery_updated_at)} · Removal check ${displayDate(data.removal_updated_at)}`;
    state.page = 1;
    applyFilters();
  } catch (error) {
    $("#review-list").innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
    $("#freshness").textContent = "The protected review feed could not be loaded.";
  } finally {
    $("#refresh").disabled = false;
  }
}

function normalizedType(record) {
  if (record.review_type === "removal") return "removal";
  if (record.candidate_type === "recurring") return "persistent";
  return record.candidate_type || "needs_classification";
}

function applyFilters() {
  const query = $("#search").value.trim().toLowerCase();
  const queue = $("#queue-filter").value;
  const type = $("#type-filter").value;
  const decisionFilter = $("#decision-filter").value;
  state.filtered = state.records.filter((record) => {
    const decision = state.decisions.get(decisionKey(record));
    const haystack = [record.title, record.name, record.discovered_domain, record.source_name, record.id, record.url, record.link].join(" ").toLowerCase();
    if (query && !haystack.includes(query)) return false;
    if (queue !== "all" && record.review_type !== queue) return false;
    if (type !== "all" && normalizedType(record) !== type) return false;
    if (decisionFilter === "pending" && decision) return false;
    if (!["all", "pending"].includes(decisionFilter) && decision?.decision !== decisionFilter) return false;
    return true;
  });
  state.filtered.sort((a, b) => {
    if (a.review_type !== b.review_type) return a.review_type === "removal" ? -1 : 1;
    return String(b.first_seen || b.last_checked || "").localeCompare(String(a.first_seen || a.last_checked || ""));
  });
  const maxPage = Math.max(1, Math.ceil(state.filtered.length / state.pageSize));
  state.page = Math.min(state.page, maxPage);
  updateSummary();
  render();
}

function updateSummary() {
  const decisions = [...state.decisions.values()];
  $("#count-pending").textContent = Math.max(0, state.records.length - decisions.length);
  $("#count-approved").textContent = decisions.filter((item) => item.decision === "approve").length;
  $("#count-deferred").textContent = decisions.filter((item) => item.decision === "defer").length;
  $("#count-rejected").textContent = decisions.filter((item) => item.decision === "reject").length;
  $("#count-removals").textContent = state.records.filter((item) => item.review_type === "removal" && !state.decisions.has(decisionKey(item))).length;
}

function render() {
  const start = (state.page - 1) * state.pageSize;
  const records = state.filtered.slice(start, start + state.pageSize);
  $("#result-count").textContent = `${state.filtered.length.toLocaleString()} record${state.filtered.length === 1 ? "" : "s"}`;
  $("#page-label").textContent = `Page ${state.page} of ${Math.max(1, Math.ceil(state.filtered.length / state.pageSize))}`;
  $("#previous-page").disabled = state.page === 1;
  $("#next-page").disabled = start + state.pageSize >= state.filtered.length;
  if (!records.length) {
    $("#review-list").innerHTML = '<div class="empty">No records match these filters.</div>';
    return;
  }
  $("#review-list").innerHTML = records.map((record) => {
    const decision = state.decisions.get(decisionKey(record));
    const kind = normalizedType(record);
    const title = record.title || record.name || record.url || record.id;
    const url = record.discovered_url || record.link || record.url || "#";
    const source = record.source_name || record.reason || record.last_result || "Inventory monitor";
    const date = record.first_seen || record.last_checked;
    return `
      <article class="review-row">
        <span class="badge ${escapeHtml(kind)}">${escapeHtml(kind.replaceAll("_", " "))}</span>
        <div class="record-title">
          <strong><a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(title)}</a></strong>
          <small>${escapeHtml(record.discovered_domain || record.domain || record.id)} · ${escapeHtml(displayDate(date))}</small>
        </div>
        <div class="record-source">${escapeHtml(source)}</div>
        <span class="decision ${escapeHtml(decision?.decision || "")}">${escapeHtml(decision?.decision || "Pending")}</span>
        <button class="review-button" type="button" data-key="${escapeHtml(decisionKey(record))}">${decision ? "Edit" : "Review"}</button>
      </article>`;
  }).join("");
}

function openDecision(key) {
  const record = state.records.find((item) => decisionKey(item) === key);
  if (!record) return;
  state.selected = record;
  const decision = state.decisions.get(key);
  $("#dialog-kind").textContent = record.review_type === "removal" ? "Possible removal" : "New discovery";
  $("#dialog-title").textContent = record.title || record.name || "Review decision";
  $("#dialog-source").textContent = `${record.source_name || record.reason || "Inventory monitor"} · ${record.discovered_url || record.link || record.url || ""}`;
  $("#dialog-id").value = record.id;
  $("#dialog-review-type").value = record.review_type;
  $("#dialog-classification").value = decision?.classification || (record.review_type === "removal" ? "remove" : normalizedType(record));
  $("#dialog-notes").value = decision?.notes || "";
  $("#save-status").textContent = decision ? `Last saved by ${decision.reviewer_email} on ${displayDate(decision.updated_at)}.` : "";
  $("#decision-dialog").showModal();
}

async function saveDecision(decision) {
  if (!state.selected) return;
  $("#save-status").textContent = "Saving decision…";
  document.querySelectorAll("[data-decision]").forEach((button) => { button.disabled = true; });
  try {
    const payload = {
      candidate_id: state.selected.id,
      review_type: state.selected.review_type,
      decision,
      classification: $("#dialog-classification").value,
      notes: $("#dialog-notes").value,
    };
    const response = await fetch("/api/admin/decision", {
      method: "POST",
      headers: { "content-type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || "Unable to save decision.");
    state.decisions.set(decisionKey(state.selected), {
      candidate_id: state.selected.id,
      review_type: state.selected.review_type,
      decision,
      classification: payload.classification,
      notes: payload.notes,
      reviewer_email: data.reviewer_email,
      updated_at: new Date().toISOString(),
    });
    $("#decision-dialog").close();
    applyFilters();
  } catch (error) {
    $("#save-status").textContent = error.message;
  } finally {
    document.querySelectorAll("[data-decision]").forEach((button) => { button.disabled = false; });
  }
}

["search", "queue-filter", "type-filter", "decision-filter"].forEach((id) => {
  $(`#${id}`).addEventListener(id === "search" ? "input" : "change", () => {
    state.page = 1;
    applyFilters();
  });
});
$("#review-list").addEventListener("click", (event) => {
  const button = event.target.closest("[data-key]");
  if (button) openDecision(button.dataset.key);
});
$("#previous-page").addEventListener("click", () => { state.page -= 1; render(); });
$("#next-page").addEventListener("click", () => { state.page += 1; render(); });
$("#refresh").addEventListener("click", loadReviews);
document.querySelectorAll("[data-decision]").forEach((button) => {
  button.addEventListener("click", () => saveDecision(button.dataset.decision));
});
loadReviews();
