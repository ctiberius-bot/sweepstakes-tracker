(() => {
  const cards = [...document.querySelectorAll(".sweep-card")];
  if (!cards.length) return;
  const search = document.querySelector("#sweep-search");
  const category = document.querySelector("#sweep-category");
  const frequency = document.querySelector("#sweep-frequency");
  const deadline = document.querySelector("#sweep-deadline");
  const count = document.querySelector("#sweep-count");
  const empty = document.querySelector("#sweep-empty");
  let view = "all";
  const readSet = (key) => new Set(JSON.parse(localStorage.getItem(key) || "[]"));
  const writeSet = (key, set) => localStorage.setItem(key, JSON.stringify([...set]));
  let saved = readSet("safetracker_saved_sweeps");
  let entered = readSet("safetracker_entered_sweeps");

  function refreshButtons() {
    cards.forEach((card) => {
      const id = card.dataset.sweepId;
      const save = card.querySelector("[data-save]");
      const mark = card.querySelector("[data-entered]");
      const isSaved = saved.has(id);
      const isEntered = entered.has(id);
      save.textContent = isSaved ? "★ Saved" : "☆ Save";
      save.setAttribute("aria-pressed", String(isSaved));
      mark.textContent = isEntered ? "✓ Entered" : "○ Mark entered";
      mark.setAttribute("aria-pressed", String(isEntered));
    });
  }
  function apply() {
    const term = search.value.trim().toLowerCase();
    const days = Number(deadline.value || 0);
    const now = new Date();
    let visible = 0;
    cards.forEach((card) => {
      const close = new Date(`${card.dataset.closes}T23:59:59`);
      const remaining = Math.ceil((close - now) / 86400000);
      const id = card.dataset.sweepId;
      const match = (!term || card.dataset.search.toLowerCase().includes(term))
        && (!category.value || card.dataset.category === category.value)
        && (!frequency.value || card.dataset.frequency === frequency.value)
        && (!days || (remaining >= 0 && remaining <= days))
        && (view === "all" || (view === "saved" ? saved.has(id) : entered.has(id)));
      card.hidden = !match;
      if (match) visible += 1;
    });
    count.textContent = visible;
    empty.hidden = visible !== 0;
  }
  [search, category, frequency, deadline].forEach((control) => control.addEventListener("input", apply));
  document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => {
    view = button.dataset.view;
    document.querySelectorAll("[data-view]").forEach((item) => item.classList.toggle("is-active", item === button));
    apply();
  }));
  document.addEventListener("click", (event) => {
    const saveButton = event.target.closest("[data-save]");
    const enteredButton = event.target.closest("[data-entered]");
    if (!saveButton && !enteredButton) return;
    const key = saveButton ? "safetracker_saved_sweeps" : "safetracker_entered_sweeps";
    const set = saveButton ? saved : entered;
    const id = (saveButton || enteredButton).dataset[saveButton ? "save" : "entered"];
    set.has(id) ? set.delete(id) : set.add(id);
    writeSet(key, set);
    refreshButtons();
    apply();
  });
  refreshButtons();
  apply();
})();
