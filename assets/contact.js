(() => {
  const form = document.getElementById("contact-form");
  const submit = document.getElementById("contact-submit");
  const status = document.getElementById("contact-status");
  const startedAt = document.getElementById("form-started-at");
  let widgetId = null;

  if (!form || !submit || !status || !startedAt) return;
  startedAt.value = String(Date.now());

  const setStatus = (message, state = "") => {
    status.textContent = message;
    status.dataset.state = state;
  };

  async function configureTurnstile() {
    try {
      const response = await fetch("/api/contact", { headers: { Accept: "application/json" } });
      const config = await response.json();
      if (!response.ok || !config.siteKey) throw new Error("Contact verification is not configured.");
      if (!window.turnstile) {
        await new Promise((resolve, reject) => {
          let checks = 0;
          const timer = window.setInterval(() => {
            checks += 1;
            if (window.turnstile) {
              window.clearInterval(timer);
              resolve();
            } else if (checks > 50) {
              window.clearInterval(timer);
              reject(new Error("Verification could not load."));
            }
          }, 100);
        });
      }
      widgetId = window.turnstile.render("#turnstile-widget", {
        sitekey: config.siteKey,
        action: "contact",
        theme: "light",
        size: "flexible",
        callback: () => {
          submit.disabled = false;
          setStatus("Secure verification complete.", "success");
        },
        "expired-callback": () => {
          submit.disabled = true;
          setStatus("Verification expired. Please verify again.", "error");
        },
        "error-callback": () => {
          submit.disabled = true;
          setStatus("Verification could not load. Please refresh and try again.", "error");
        },
      });
      setStatus("Complete the secure verification to send your message.");
    } catch (error) {
      submit.disabled = true;
      setStatus("The protected contact form is temporarily unavailable. Please try again later.", "error");
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity() || submit.disabled) return;
    submit.disabled = true;
    setStatus("Sending your message…");

    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: { Accept: "application/json" },
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.message || "Your message could not be sent.");
      form.reset();
      startedAt.value = String(Date.now());
      setStatus("Message sent. Thank you—we’ll review it.", "success");
    } catch (error) {
      setStatus(error.message || "Your message could not be sent. Please try again.", "error");
    } finally {
      if (widgetId !== null && window.turnstile) window.turnstile.reset(widgetId);
    }
  });

  configureTurnstile();
})();
