(() => {
  const config = window.WinnerSignalSignupConfig;

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
    else container.innerHTML = '<p class="newsletter-unavailable" role="status">Winner Signal signup is temporarily unavailable.</p>';
  }

  function mountAll() {
    document.querySelectorAll("[data-winner-signal-signup]").forEach(mount);
  }

  window.WinnerSignalSignup = Object.freeze({ mountAll });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mountAll);
  else mountAll();
})();
