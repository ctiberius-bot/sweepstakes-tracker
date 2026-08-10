(() => {
  const config = window.WinnerSignalSignupConfig;

  function buttondownForm(container) {
    const compact = container.dataset.variant === "strip";
    container.innerHTML = `
      <form class="newsletter-form" action="${config.buttondown.action}" method="post" data-track-form="newsletter_signup">
        <div class="newsletter-fields">
          <label class="sr-only" for="${container.id}-email">Email address</label>
          <input id="${container.id}-email" type="email" name="email" autocomplete="email" placeholder="${compact ? "Email address" : "you@example.com"}" required>
          <input type="hidden" name="embed" value="1">
          <input type="hidden" name="tag" value="${config.buttondown.tag}">
          <button type="submit">${compact ? "Send me winner updates" : "Send me updates"}</button>
        </div>
      </form>`;
  }

  function kitForm(container) {
    if (!config.kit.formUid || !config.kit.scriptSrc) {
      container.innerHTML = '<p class="newsletter-unavailable" role="status">Winner Signal signup is temporarily unavailable.</p>';
      return;
    }
    const script = document.createElement("script");
    script.async = true;
    script.dataset.uid = config.kit.formUid;
    script.src = config.kit.scriptSrc;
    script.addEventListener("error", () => {
      container.innerHTML = '<p class="newsletter-unavailable" role="status">Winner Signal signup could not load. Please try again later.</p>';
    });
    container.replaceChildren(script);
  }

  function mount(container) {
    if (container.dataset.signupMounted === "true" || !config) return;
    container.dataset.signupMounted = "true";
    if (config.provider === "kit") kitForm(container);
    else if (config.provider === "buttondown") buttondownForm(container);
    else container.innerHTML = '<p class="newsletter-unavailable" role="status">Winner Signal signup is temporarily unavailable.</p>';
  }

  function mountAll() {
    document.querySelectorAll("[data-winner-signal-signup]").forEach(mount);
  }

  window.WinnerSignalSignup = Object.freeze({ mountAll });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mountAll);
  else mountAll();
})();
