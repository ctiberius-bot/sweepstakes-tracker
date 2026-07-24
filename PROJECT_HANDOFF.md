# SafeTrackerHub Sweepstakes Tracker — Project Handoff

Last updated: July 23, 2026

## Start here

- Production: https://sweeps.safetrackerhub.com/
- GitHub: https://github.com/ctiberius-bot/sweepstakes-tracker
- Production branch: `main`
- Hosting: Cloudflare Pages, automatically deployed from GitHub
- Latest production redesign commit before this handoff: `4b4607e`

This file is the durable context for continuing the project from another computer or ChatGPT/Codex client. Read it before making changes.

## Product direction

SafeTrackerHub is intended to become a portfolio of comparison and inventory trackers for confusing or risky online categories. The first tracker covers sweepstakes, rewards, giveaway directories, and related sites.

The sweepstakes tracker should:

- Maintain a broad, useful inventory of active sites.
- Give each site a visible `ScamFactor` score.
- Help visitors compare prize types, drawing frequency, unsubscribe options, major concerns, and site type.
- Provide a detailed inventory-style profile for every site.
- Offer practical sweepstakes tips and scam warnings.
- Support aggressive monetization through clearly identified sponsorships, featured placements, affiliate links, and future advertising.
- Avoid presenting itself primarily as a conventional “review site.” Preferred language includes “inventory,” “tracker,” “site profile,” and “details.”

Likely future SafeTrackerHub categories include personal-loan sites, payday-loan apps, and games or apps that claim users can earn money.

## Current production experience

The production tracker currently includes:

- 29 tracked sites.
- A compact editorial header and safety warning.
- Featured-placement cards.
- Search, ScamFactor filtering, and sorting.
- A desktop comparison table and mobile card layout.
- Favicons beside site names when available.
- A separate visual type badge column.
- A single ScamFactor stamp in the rating-column header.
- Large, color-coded numeric ScamFactor scores.
- Direct unsubscribe or privacy opt-out links where a verified URL is known.
- “View details” links to individual site profiles.
- An expandable scoring-methodology section below the inventory.
- A sponsorship-information page at `/sponsorships.html`.
- Paid-placement language that says sponsored positions will be labeled while the displayed score remains visible.

## Important design decisions

- The large original hero was rejected because it consumed too much of the first screen. Keep the header compact.
- The ScamFactor asset is a transparent, distressed rubber-stamp image with a slight rotation.
- Do not repeat the ScamFactor stamp in every table row. One stamp in the column header is enough; the numeric scores should dominate.
- The ScamFactor column must remain wide enough for the header stamp to be readable.
- The site-name column should be generous, with highly legible titles and favicons.
- Site type belongs in its own column and should use a visual pill/badge rather than plain text.
- The unsubscribe column needs enough width and forced wrapping so content never overlaps the red-flags column.
- The scoring-methodology explanation belongs below the tracker, not above it.
- Individual pages are “site profiles,” not “full reviews.”
- A universal “unsubscribe from all” link is not currently possible because each operator has separate accounts, consent systems, and privacy processes.
- Sponsorships and featured positions are commercially available. Do not claim rankings can never be sold.
- Paid placements should be labeled. The site’s displayed ScamFactor score remains visible.

## ScamFactor scoring concept

ScamFactor is a 1–10 consumer-risk and friction score. Lower is better. It is not a prediction that a visitor will win.

Current weighted criteria:

- 30% Transparency and winner proof
- 25% Fulfillment history and complaints
- 20% Entry model and hidden requirements
- 15% Realism of the win opportunity
- 10% Marketing aggressiveness

Current score bands:

- 1–2: Low concern
- 3–4: Generally sound
- 5–6: Use caution
- 7–8: High friction
- 9–10: Major red flags

Scores are editorial estimates based on available evidence and should be revisited as sites change.

## Repository structure

- `data.json` — source inventory data for all sites.
- `scraper_simple.py` — static-site generator. Despite its name, it currently loads local JSON and renders templates; it is not a broad live web crawler.
- `templates/tracker.html.j2` — main tracker template.
- `templates/review.html.j2` — individual site-profile template.
- `templates/sponsorships.html.j2` — sponsorship page template.
- `assets/site.css` — primary redesign styles.
- `assets/tracker.js` — client-side layout enhancement, search, filters, sorting, mobile cards, favicons, and quick-details dialog.
- `assets/scamfactor-stamp.png` — transparent ScamFactor rubber-stamp artwork.
- `index.html` — generated production homepage.
- `reviews/*.html` — generated site-profile pages.
- `sponsorships.html` — generated sponsorship page.

Generated HTML files are committed because Cloudflare Pages serves the static repository output.

## Rebuilding the site

After changing `data.json` or a Jinja template, run:

```powershell
python scraper_simple.py
```

The Python environment needs Jinja2. The generator:

1. Loads `data.json`.
2. Ensures every site has a stable slug.
3. Updates the last-updated timestamp.
4. Rebuilds `index.html`.
5. Rebuilds all files under `reviews/`.
6. Rebuilds `sponsorships.html`.
7. Removes template-only trailing whitespace from generated HTML.

After rebuilding, validate the JavaScript and generated diff before committing.

## Deployment workflow

Cloudflare Pages deploys from the public GitHub repository.

Normal production workflow:

1. Pull the current `main`.
2. Make source changes.
3. Regenerate static pages when data or templates change.
4. Preview locally.
5. Validate all 29+ rows and generated profile pages.
6. Commit both source and generated files.
7. Push `main` to GitHub when the update is approved for production.
8. Verify the production homepage and any newly added route after Cloudflare finishes.

Do not push partially generated output or template changes without their corresponding generated HTML.

## History of work completed in the original Codex task

1. The existing GitHub repository was cloned locally and inspected.
2. A transparent distressed ScamFactor rubber-stamp graphic was generated and added.
3. The oversized ScamFactor banner treatment was reduced.
4. The stamp was added to the table header, then refined after several visual iterations.
5. The original Grok-generated appearance was replaced with a more polished SafeTrackerHub editorial design.
6. An overly tall first redesign header was reduced after feedback.
7. A temporary one-row display problem caused by restored local search state was fixed; the tracker now resets to the complete inventory on load.
8. Monetization language was revised to allow sponsorships and paid featured placement.
9. The inventory expanded from 15 to 29 sites, including established sweepstakes directories and giveaway discovery services.
10. The ScamFactor column was widened so its stamp header was readable.
11. Favicons were added beside site names with graceful failure handling.
12. The scoring-methodology explanation was expanded and moved below the tracker.
13. Verified direct unsubscribe and privacy links were added where known.
14. A universal unsubscribe-all option was rejected as technically inaccurate.
15. Additional data concepts were planned for individual site pages rather than overloading the main table.
16. A generated profile page was created for every tracked site.
17. “Full review” terminology was replaced with inventory-oriented “site profile” and “View details” language.
18. The site-name column was widened and title typography improved.
19. Site type was moved into its own column.
20. A sponsorship-information page was created and linked from featured-placement language.
21. Repeated ScamFactor logos in every score row were removed because they created visual noise.
22. Numeric score badges were enlarged so the rating is the dominant signal.
23. Type pills were restored as visual badges.
24. The unsubscribe column was widened and long content was forced to wrap.
25. The finished redesign, all 29 profiles, sponsorship page, assets, generator changes, and generated output were committed and pushed to production.

## Known verified unsubscribe/privacy links

The data currently contains direct actions for a limited set of operators, including:

- Mondosweeps privacy-rights request
- Prizegrab unsubscribe
- Prizeloot consumer opt-out
- PrizeCraze consumer opt-out
- Winloot unsubscribe

Do not invent unsubscribe URLs. Verify operator-owned links before adding them.

## Content and data caveats

- The current 29-site list is broader than the original version but should not be treated as permanently exhaustive.
- Some entries are sweepstakes operators; others are directories, rewards platforms, sample programs, or giveaway-discovery services. Keep type labels accurate.
- Do not guess missing eligibility, winner evidence, data-sharing, or account requirements. Site profiles intentionally identify unverified fields.
- Recheck official rules, current status, privacy links, and prize claims before presenting them as current facts.
- Sweepstakes casinos and one-off brand promotions were intentionally excluded from this tracker’s initial scope.

## Recommended next work

1. Add a real sponsorship contact method and lead form.
2. Add analytics and conversion-event tracking.
3. Add explicit sponsored labels and placement metadata to `data.json`.
4. Add affiliate-link fields, click tracking, and network-specific disclosure handling.
5. Establish an evidence/source model per data field instead of one general verification link.
6. Add automated stale-data checks and last-verified dates per site.
7. Expand the inventory systematically by category and geography.
8. Add SEO metadata, structured data, canonical URLs, sitemap, robots file, and social-preview imagery.
9. Add editorial pages for scam warnings, entry strategy, dedicated-email setup, tax considerations, and winner verification.
10. Define a reusable SafeTrackerHub data model and design system before launching loan, payday-app, and money-making-game trackers.

## Instructions for another ChatGPT/Codex client

When continuing this project:

1. Read this entire file.
2. Inspect the current `main` branch before editing.
3. Treat `data.json` and the Jinja templates as source files.
4. Regenerate all static output after relevant source changes.
5. Preserve the approved design decisions above unless the user explicitly changes direction.
6. Preview locally before pushing.
7. Do not push to production until the user approves the preview, unless the user directly requests an immediate production change.

