(() => {
  function buildLayout() {
    const originalHeader = document.querySelector("body > header");
    const main = document.querySelector("main");
    const originalFooter = main?.querySelector("footer");
    if (!originalHeader || !main) return;

    const updatedText = cleanText(originalHeader.querySelector("p")?.textContent || "");
    const updated = updatedText.match(/Updated\s+(.+)$/i)?.[1] || "Recently";
    const rowCount = document.querySelectorAll("tbody tr").length;

    originalHeader.className = "site-header";
    originalHeader.innerHTML = `
      <div class="max-w-7xl mx-auto px-4">
        <div class="masthead">
          <div class="brand-lockup">
            <span class="brand-mark" aria-hidden="true"><span>ST</span></span>
            <div><div class="brand-name">SafeTracker: <em>Sweepstakes</em></div><div class="brand-network">Safety rankings & winner reports</div></div>
          </div>
          <nav class="main-nav" aria-label="Primary navigation">
            <a href="#rankings">Rankings</a>
            <a href="active-sweepstakes.html">Active Sweepstakes</a>
            <a href="winners.html">Winners</a>
            <a href="#methodology">How we score</a>
            <a href="#editor-picks">Editor picks</a>
            <a class="nav-disclosure" href="#disclosure">Affiliate disclosure</a>
          </nav>
        </div>
        <div class="hero">
          <div>
            <p class="eyebrow">SafeTracker: Sweepstakes</p>
            <h1>Find real sweepstakes. Spot the red flags.</h1>
            <p class="hero-copy">Compare sweepstakes and rewards sites by transparency, fulfillment history, entry traps, realistic win opportunity, and marketing pressure.</p>
          </div>
          <div class="hero-meta"><strong>${rowCount} sites reviewed</strong>ScamFactor-rated for fast comparison. Lower scores mean fewer red flags.</div>
        </div>
      </div>`;

    main.className = "content-shell";

    const trust = document.createElement("section");
    trust.className = "trust-grid";
    trust.setAttribute("aria-label", "Editorial standards");
    trust.innerHTML = `
      <a class="trust-item trust-link" href="sponsorships.html"><span class="trust-label">Featured placement</span><span class="trust-value">Sponsorships available →</span></a>
      <div class="trust-item"><span class="trust-label">Scoring</span><span class="trust-value">Five published criteria</span></div>
      <div class="trust-item"><span class="trust-label">Safety rule</span><span class="trust-value">Never pay to claim</span></div>
      <div class="trust-item"><span class="trust-label">Last reviewed</span><span class="trust-value">${updated}</span></div>`;
    main.prepend(trust);
    trust.insertAdjacentHTML("afterend", `
      <aside class="newsletter-strip" aria-label="Daily winners email">
        <span><strong>Daily winners</strong> · Source-linked reports when there is something new.</span>
        <form action="https://buttondown.com/api/emails/embed-subscribe/safetrackerhub" method="post">
          <label class="sr-only" for="strip-newsletter-email">Email address</label>
          <input id="strip-newsletter-email" type="email" name="email" autocomplete="email" placeholder="Email address" required>
          <input type="hidden" name="embed" value="1">
          <input type="hidden" name="tag" value="daily-winners">
          <button type="submit">Subscribe</button>
        </form>
      </aside>`);

    const safety = Array.from(main.children).find((element) => element.textContent.includes("Never pay to claim a prize"));
    if (safety) safety.className = "safety-note";

    const ctaGrid = Array.from(main.children).find((element) => element.querySelector?.('a[href*="swagbucks.com"]'));
    if (ctaGrid) {
      const picks = document.createElement("section");
      picks.id = "editor-picks";
      picks.className = "picks-section";
      picks.innerHTML = `
        <p class="section-kicker"><a class="sponsorship-link" href="sponsorships.html">Featured placements →</a></p>
        <h2 class="section-title">Three options for three different goals</h2>
        <p class="section-intro">Partners may pay for featured placement. Paid positions will be clearly labeled, and every listed site still displays its score. <a class="sponsorship-link" href="sponsorships.html">See sponsorship options →</a></p>
        <div class="pick-grid">
          <a class="pick-card" href="https://www.swagbucks.com/" target="_blank" rel="noopener sponsored"><span class="pick-label">Best for steady rewards</span><span class="pick-name">Swagbucks</span><span class="pick-reason">A long-running rewards platform with more realistic earning opportunities than jackpot-only sites.</span><span class="pick-action">View official site →</span></a>
          <a class="pick-card" href="https://www.mondosweeps.com/" target="_blank" rel="noopener sponsored"><span class="pick-label">Best daily cash chance</span><span class="pick-name">Mondosweeps</span><span class="pick-reason">Daily drawings with a guaranteed $25 winner, balanced against heavier promotional email volume.</span><span class="pick-action">View official site →</span></a>
          <a class="pick-card" href="https://www.pch.com/" target="_blank" rel="noopener sponsored"><span class="pick-label">Best established name</span><span class="pick-name">Publishers Clearing House</span><span class="pick-reason">The most recognizable big-prize operator here—plus a frequent target for impersonation scams.</span><span class="pick-action">View official site →</span></a>
        </div>`;
      ctaGrid.replaceWith(picks);
    }

    const method = Array.from(main.children).find((element) => element.querySelector?.(".scamfactor-badge"));
    if (method) {
      method.id = "methodology";
      method.className = "method-card method-bottom";
      const heading = method.querySelector("h2");
      const grid = Array.from(method.children).find((element) => element !== heading);
      if (grid) {
        grid.className = "method-grid";
        Array.from(grid.children).forEach((item) => {
          item.className = "method-item";
          const match = item.textContent.trim().match(/^(\d+%)(.*)$/);
          if (match) item.innerHTML = `<strong>${match[1]}</strong>${match[2]}`;
        });
      }
      const details = document.createElement("details");
      details.className = "method-disclosure";
      details.innerHTML = `
        <summary>
          <img class="method-summary-stamp" src="assets/scamfactor-stamp.png" alt="ScamFactor">
          <span class="method-summary-copy"><strong>How the ScamFactor score is calculated</strong><span>See the criteria, score bands, limitations, and sponsorship policy.</span></span>
        </summary>
        <div class="method-body">
          <p class="method-explanation">ScamFactor is a 1–10 consumer-risk and friction score—not a prediction of whether you will win. Lower scores indicate stronger transparency, clearer rules, more credible fulfillment history, fewer entry traps, and less aggressive follow-up marketing. We review the evidence available for each site and apply the weighted criteria below.</p>
        </div>`;
      const body = details.querySelector(".method-body");
      if (grid) body.append(grid);
      body.insertAdjacentHTML("beforeend", `
        <div class="score-bands" aria-label="ScamFactor score bands">
          <div class="score-band"><strong>1–2 · Low concern</strong>Established, transparent, and comparatively low-friction.</div>
          <div class="score-band"><strong>3–4 · Generally sound</strong>Legitimate-looking with manageable marketing or usability tradeoffs.</div>
          <div class="score-band"><strong>5–6 · Use caution</strong>Meaningful spam, data-sharing, proof, or fulfillment concerns.</div>
          <div class="score-band"><strong>7–8 · High friction</strong>Serious complaints, unclear practices, or poor value for the information requested.</div>
          <div class="score-band"><strong>9–10 · Major red flags</strong>Deceptive funnels, weak payout evidence, or conduct users should avoid.</div>
        </div>
        <p class="method-caveat"><strong>Important:</strong> Scores are editorial estimates based on available evidence and may change as sites change. A paid or sponsored placement can affect visibility, but it must be labeled and does not remove the displayed ScamFactor score.</p>`);
      method.innerHTML = "";
      method.append(details);
    }

    const table = main.querySelector("table");
    const tableWrap = table?.parentElement;
    if (table && tableWrap) {
      table.className = "tracker-table";
      tableWrap.className = "tracker-table-wrap";
      const rankings = document.createElement("section");
      rankings.id = "rankings";
      tableWrap.before(rankings);
      rankings.append(tableWrap);
      rankings.insertAdjacentHTML("afterbegin", `
        <div class="rankings-head">
          <div><p class="section-kicker">Complete tracker</p><h2 class="section-title">Sweepstakes rankings</h2></div>
          <div class="ranking-facts" aria-label="Ranking information">
            <span><small>Updated</small>${updated}</span>
            <span><small>ScamFactor</small>Lower score is better</span>
          </div>
        </div>
        <div class="controls" aria-label="Ranking controls">
          <label class="search-wrap"><span>Search the inventory</span><input id="tracker-search" class="control search-control" type="search" placeholder="Site name, prize, or red flag…" aria-label="Search tracker"></label>
          <select id="score-filter" class="control" aria-label="Filter by ScamFactor">
            <option value="0">All ScamFactor scores</option><option value="2">Excellent: 2 or lower</option><option value="4">Good: 4 or lower</option><option value="6">Moderate: 6 or lower</option>
          </select>
          <select id="sort-rankings" class="control" aria-label="Sort rankings">
            <option value="score-low">Sort: Lowest ScamFactor</option><option value="score-high">Sort: Highest ScamFactor</option><option value="name">Sort: Site name</option>
          </select>
        </div>
        <p id="results-count" class="results-count" aria-live="polite"></p>
        <div id="mobile-cards" class="mobile-cards"></div>`);
      if (method) rankings.after(method);
    }

    originalFooter?.remove();

    document.body.insertAdjacentHTML("beforeend", `
      <dialog id="review-dialog" class="review-dialog">
        <div class="dialog-inner"><div class="dialog-top"><div id="dialog-content"></div><button id="dialog-close" class="dialog-close" type="button" aria-label="Close review">×</button></div></div>
      </dialog>
      <footer id="disclosure" class="site-footer">
        <div class="max-w-7xl mx-auto px-4">
          <div class="footer-grid">
            <div><div class="footer-title">SafeTracker: Sweepstakes</div><p class="footer-copy">Plain-English safety rankings and source-linked winner reports for sweepstakes, giveaway, and rewards sites.</p></div>
            <div><div class="footer-title">Explore</div><div class="footer-links"><a href="#rankings">Rankings</a><a href="active-sweepstakes.html">Active Sweepstakes</a><a href="winners.html">Winners</a><a href="#editor-picks">Editor picks</a><a href="#methodology">Methodology</a></div></div>
            <div><div class="footer-title">Our standards</div><div class="footer-links"><a href="#methodology">Published scoring</a><a href="#disclosure">Affiliate policy</a><a href="#rankings">Review dates</a></div></div>
            <div><div class="footer-title">Disclosure</div><p class="footer-copy">Some links and featured placements may be paid. Sponsored positions will be labeled. ScamFactor scores summarize the risk signals shown in each review.</p></div>
          </div>
          <div class="footer-bottom"><span>Data last refreshed ${updated}. Always verify official rules before entering. Never pay to claim a prize.</span><span class="site-version">SafeTracker: Sweepstakes v1.1</span></div>
        </div>
      </footer>`);
  }

  function cleanText(value) {
    return value.replace(/\s+/g, " ").trim();
  }

  buildLayout();

  const table = document.querySelector(".tracker-table");
  if (!table) return;

  const tbody = table.tBodies[0];
  const rows = Array.from(tbody.rows);
  const search = document.querySelector("#tracker-search");
  const scoreFilter = document.querySelector("#score-filter");
  const sort = document.querySelector("#sort-rankings");
  const count = document.querySelector("#results-count");
  const cards = document.querySelector("#mobile-cards");
  const dialog = document.querySelector("#review-dialog");
  const closeDialog = document.querySelector("#dialog-close");
  const dialogContent = document.querySelector("#dialog-content");

  const clean = (value) => value.replace(/\s+/g, " ").trim();
  const initials = (name) => {
    const ignored = new Set(["and", "the", "of"]);
    const words = name
      .replace(/\([^)]*\)/g, " ")
      .split(/[^A-Za-z0-9]+/)
      .filter((word) => word && !ignored.has(word.toLowerCase()));
    return (words.length > 1 ? words.slice(0, 2).map((word) => word[0]) : [words[0]?.slice(0, 2)])
      .join("")
      .toUpperCase() || "?";
  };
  const markHue = (name) => [...name].reduce((total, char) => total + char.charCodeAt(0), 0) % 360;
  const makeSiteMark = (item) => {
    const mark = document.createElement("span");
    mark.className = "site-mark site-mark-small";
    mark.style.setProperty("--site-mark-hue", String(markHue(item.name)));
    mark.setAttribute("aria-hidden", "true");
    const fallback = document.createElement("span");
    fallback.className = "site-mark-fallback";
    fallback.textContent = initials(item.name);
    mark.append(fallback);
    if (item.link?.startsWith("http")) {
      const icon = document.createElement("img");
      icon.className = "site-mark-image";
      icon.alt = "";
      icon.width = 24;
      icon.height = 24;
      icon.loading = "lazy";
      icon.src = new URL("/favicon.ico", item.link).href;
      icon.addEventListener("error", () => icon.remove());
      mark.append(icon);
    }
    return mark;
  };
  const rowData = (row) => {
    const cells = row.cells;
    return {
      row,
      rank: Number(clean(cells[0].textContent)),
      name: clean(cells[1].textContent),
      category: clean(cells[2].textContent),
      score: Number(clean(cells[3].textContent)),
      prizes: clean(cells[4].textContent),
      frequency: clean(cells[5].textContent),
      unsubscribe: clean(cells[6].textContent),
      flags: clean(cells[7].textContent),
      link: cells[8].querySelector("a")?.href || "",
      verified: row.dataset.verified || "Not recorded",
      reviewUrl: row.dataset.reviewUrl || ""
    };
  };
  const items = rows.map(rowData);

  const badgeLabels = {
    1: "Best established name",
    2: "Best daily earner",
    3: "Best cash alternative"
  };

  items.forEach((item) => {
    const siteCell = item.row.cells[1];
    siteCell.classList.add("site-cell");
    const originalName = clean(siteCell.textContent);
    siteCell.innerHTML = "";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "site-name-button";
    button.append(makeSiteMark(item));
    const name = document.createElement("span");
    name.textContent = originalName;
    button.append(name);
    button.addEventListener("click", () => openReview(item));
    siteCell.append(button);
    if (item.reviewUrl) {
      const detailsLink = document.createElement("a");
      detailsLink.className = "more-detail-link";
      detailsLink.href = item.reviewUrl;
      detailsLink.textContent = "View details →";
      siteCell.append(document.createElement("br"), detailsLink);
    }
    if (badgeLabels[item.rank]) {
      const badge = document.createElement("span");
      badge.className = "editor-badge";
      badge.textContent = badgeLabels[item.rank];
      siteCell.append(document.createElement("br"), badge);
    }
    const link = item.row.cells[8].querySelector("a");
    if (link) {
      link.className = "visit-link";
      link.textContent = "Official site →";
      link.rel = "noopener sponsored";
    }
  });

  function scoreClass(score) {
    if (score <= 2) return "score-low";
    if (score <= 4) return "score-midlow";
    if (score <= 6) return "score-mid";
    if (score <= 8) return "score-high";
    return "score-danger";
  }

  function openReview(item) {
    dialogContent.innerHTML = `
      <p class="section-kicker">Quick details</p>
      <h2 class="dialog-title">${item.name}</h2>
      <dl class="dialog-grid">
        <dt><img class="inline-scamfactor-stamp" src="assets/scamfactor-stamp.png" alt="ScamFactor"></dt><dd><span class="score-pill ${scoreClass(item.score)}">${item.score}</span> / 10</dd>
        <dt>Site type</dt><dd>${item.category.replaceAll("-", " ")}</dd>
        <dt>Last verified</dt><dd>${item.verified}</dd>
        <dt>Prize examples</dt><dd>${item.prizes}</dd>
        <dt>Frequency</dt><dd>${item.frequency}</dd>
        <dt>Unsubscribe</dt><dd>${item.unsubscribe}</dd>
        <dt>Watch for</dt><dd>${item.flags}</dd>
      </dl>
      <div class="dialog-footer">
        <small>Placement may be sponsored; ScamFactor summarizes the site’s risk signals.</small>
        ${item.reviewUrl ? `<a class="review-button secondary" href="${item.reviewUrl}">View site profile →</a>` : ""}
        ${item.link ? `<a class="official-link" style="padding:.65rem .9rem;border-radius:.55rem" href="${item.link}" target="_blank" rel="noopener sponsored">Visit official site →</a>` : ""}
      </div>`;
    dialog.showModal();
  }

  function makeCard(item) {
    const card = document.createElement("article");
    card.className = "mobile-card";
    card.dataset.rank = String(item.rank);
    card.innerHTML = `
      <div class="mobile-card-head">
        <div><span class="mobile-rank">#${item.rank}</span><h3 class="mobile-site-name"><span>${item.name}</span></h3><a class="category-badge" href="site-types.html#${item.category}">${item.category}</a>${badgeLabels[item.rank] ? `<span class="editor-badge">${badgeLabels[item.rank]}</span>` : ""}</div>
        <span class="score-pill score-pill-featured ${scoreClass(item.score)}">${item.score}</span>
      </div>
      <dl>
        <div class="mobile-detail"><dt>Prizes</dt><dd>${item.prizes}</dd></div>
        <div class="mobile-detail"><dt>Draws</dt><dd>${item.frequency}</dd></div>
        <div class="mobile-detail"><dt>Watch for</dt><dd>${item.flags}</dd></div>
      </dl>
      <div class="mobile-actions">
        <button class="quick-review" type="button">Quick details</button>
        ${item.reviewUrl ? `<a class="official-link" href="${item.reviewUrl}">View details →</a>` : ""}
      </div>`;
    card.querySelector(".mobile-site-name").prepend(makeSiteMark(item));
    card.querySelector(".quick-review").addEventListener("click", () => openReview(item));
    return card;
  }

  items.forEach((item) => cards.append(makeCard(item)));

  function applyControls() {
    const term = clean(search.value).toLowerCase();
    const ceiling = Number(scoreFilter.value);
    const ordered = [...items].sort((a, b) => {
      if (sort.value === "score-low") return a.score - b.score || a.name.localeCompare(b.name);
      if (sort.value === "score-high") return b.score - a.score || a.rank - b.rank;
      if (sort.value === "name") return a.name.localeCompare(b.name);
      return a.score - b.score || a.name.localeCompare(b.name);
    });

    ordered.forEach((item) => tbody.append(item.row));
    cards.innerHTML = "";
    let visible = 0;
    ordered.forEach((item) => {
      const haystack = `${item.name} ${item.prizes} ${item.flags}`.toLowerCase();
      const show = (!term || haystack.includes(term)) && (!ceiling || item.score <= ceiling);
      item.row.hidden = !show;
      if (show) {
        visible += 1;
        cards.append(makeCard(item));
      }
    });
    count.textContent = `${visible} of ${items.length} sites shown`;
  }

  [search, scoreFilter, sort].forEach((control) => control.addEventListener("input", applyControls));
  closeDialog.addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  // Browsers may restore form values when a local preview reloads. Always open
  // the tracker in its complete, editorial-rank state.
  search.value = "";
  scoreFilter.value = "0";
  sort.value = "score-low";
  applyControls();
})();
