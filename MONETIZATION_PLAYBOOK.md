# SafeTracker Sweepstakes Monetization Playbook

## Revenue stack

1. Direct, labeled sponsorship packages sold from `/sponsorships`.
2. Affiliate commissions on approved outbound links.
3. Weekly email sponsorships and affiliate placements.
4. Display advertising only after traffic is large enough to justify the visual cost.

## Going live

- Sponsor inquiries use the existing protected contact delivery.
- Pricing is introductory and can be changed in `data/monetization.json` and the sponsorship template.
- Add approved affiliate URLs to `data/monetization.json`. Empty values automatically use the official non-affiliate URL.
- Never paste network passwords, API keys, account credentials, or private contracts into the repository.
- When the payment platform is ready, add a payment link only after confirming the package, availability, business name, refund/cancellation language, and tax treatment.

## Placement policy

- Paid visibility must display “Sponsored,” “Featured partner,” or equivalent language.
- A paid placement may change visibility but does not hide the displayed ScamFactor score.
- A sponsor does not receive editorial approval over unrelated records.
- Reject deceptive prize claims, hidden charges, impersonation, malware, and unlawful campaigns.

## Events currently recorded

- `page_view`
- `outbound_click`
- `sponsor_interest`
- `sponsor_package`
- `sponsor_lead`
- `newsletter_signup`

Events are emitted to `/api/events`, stored in the `safetracker-analytics` Cloudflare D1 database through the `ANALYTICS_DB` production binding, and also appear as structured `monetization_event` records in Cloudflare function logs. Rolling 7-day and 30-day aggregates are available from `/api/analytics-summary`.

## Search visibility submissions

- Google Search Console domain property `safetrackerhub.com` is verified through Cloudflare DNS.
- `https://sweeps.safetrackerhub.com/sitemap.xml` was accepted by Google with 73 discovered pages.
- Bing Webmaster Tools imported `https://safetrackerhub.com/` from Google Search Console.
- The production sitemap was submitted separately to Bing and accepted for processing.
- A 100-page Bing Site Scan for `https://sweeps.safetrackerhub.com/` was queued on July 25, 2026.
- The sweepstakes-directory submission URLs in `DISCOVERY_REVIEW.md` are for submitting individual promotions, not for listing SafeTrackerHub itself. Do not submit the tracker as though it were a sweepstakes.

## Affiliate launch order

1. Prodege: Swagbucks and InboxDollars.
2. Direct outreach: MondoSweeps, PrizeGrab, PrizeLoot, Winloot, and directory operators.
3. FlexOffers and Impact inventory after publisher approval.
4. Replace only the matching blank URL in `data/monetization.json`; regenerate and verify the link before publishing.

## Payment-platform handoff

The sponsorship form is intentionally an inquiry rather than a checkout. Once the LLC and payment platform exist, add:

- Legal business name.
- Payment link or invoice workflow.
- Cancellation and refund terms.
- Tax address and required disclosures.
- A campaign start condition: payment cleared and creative approved.
