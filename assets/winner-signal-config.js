window.WinnerSignalSignupConfig = Object.freeze({
  // Keep Buttondown active until the Kit account, form, and confirmation flow
  // pass validation. Cutover changes only this public, non-secret configuration.
  provider: "buttondown",
  buttondown: Object.freeze({
    action: "https://buttondown.com/api/emails/embed-subscribe/safetrackerhub",
    tag: "daily-winners",
  }),
  kit: Object.freeze({
    formUid: "",
    scriptSrc: "",
  }),
});
