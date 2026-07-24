(() => {
  const form = document.getElementById("sponsor-form");
  const submit = document.getElementById("sponsor-submit");
  const status = document.getElementById("sponsor-status");
  const startedAt = document.getElementById("sponsor-form-started-at");
  const packageField = document.getElementById("sponsor-package");
  let widgetId = null;
  if (!form || !submit || !status || !startedAt || !packageField) return;

  startedAt.value = String(Date.now());
  const setStatus = (message, state = "") => {
    status.textContent = message;
    status.dataset.state = state;
  };

  document.querySelectorAll("[data-package]").forEach((link) => {
    link.addEventListener("click", () => {
      const selected = Array.from(packageField.options).find((option) => option.textContent.startsWith(link.dataset.package));
      if (selected) packageField.value = selected.value;
    });
  });

  async function configureTurnstile() {
    try {
      const response = await fetch("/api/contact", { headers: { Accept: "application/json" } });
      const config = await response.json();
      if (!response.ok || !config.siteKey) throw new Error("Verification is unavailable.");
      while (!window.turnstile) await new Promise((resolve) => window.setTimeout(resolve, 100));
      widgetId = window.turnstile.render("#sponsor-turnstile", {
        sitekey: config.siteKey, action: "contact", theme: "light", size: "flexible",
        callback: () => { submit.disabled = false; setStatus("Secure verification complete.", "success"); },
        "expired-callback": () => { submit.disabled = true; setStatus("Verification expired. Please verify again.", "error"); },
        "error-callback": () => { submit.disabled = true; setStatus("Verification could not load.", "error"); },
      });
      setStatus("Complete the secure verification to send your inquiry.");
    } catch {
      setStatus("The inquiry form is temporarily unavailable. Please use the main contact page.", "error");
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity() || submit.disabled) return;
    const values = new FormData(form);
    values.set("message", [
      "SPONSORSHIP INQUIRY",
      `Company: ${values.get("company")}`,
      `Package: ${values.get("package")}`,
      `Preferred dates: ${values.get("dates") || "Not specified"}`,
      `Budget: ${values.get("budget") || "Not specified"}`,
      `Notes: ${values.get("notes") || "None"}`,
    ].join("\n"));
    submit.disabled = true;
    setStatus("Sending your inquiry…");
    try {
      const response = await fetch(form.action, { method: "POST", body: values, headers: { Accept: "application/json" } });
      const result = await response.json();
      if (!response.ok) throw new Error(result.message || "The inquiry could not be sent.");
      window.SafeTrackerTrack?.("sponsor_lead", { package: values.get("package"), budget: values.get("budget") });
      form.reset();
      startedAt.value = String(Date.now());
      setStatus("Inquiry sent. We’ll reply with availability and next steps.", "success");
    } catch (error) {
      setStatus(error.message || "The inquiry could not be sent.", "error");
    } finally {
      if (widgetId !== null && window.turnstile) window.turnstile.reset(widgetId);
    }
  });

  configureTurnstile();
})();
