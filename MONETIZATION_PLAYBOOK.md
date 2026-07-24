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

Events are emitted to `/api/events` and appear as structured `monetization_event` records in Cloudflare function logs. Add a durable analytics destination later if longitudinal reporting is needed.

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
