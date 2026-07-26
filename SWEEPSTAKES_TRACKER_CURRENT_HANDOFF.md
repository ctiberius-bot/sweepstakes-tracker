# SafeTracker: Sweepstakes — Current Work Handoff

Last synchronized: July 25, 2026

## Start here

This is the current source-of-truth handoff for continuing the SafeTracker: Sweepstakes work from another ChatGPT/Codex client or phone.

- Production: https://sweeps.safetrackerhub.com/
- GitHub: https://github.com/ctiberius-bot/sweepstakes-tracker
- Production branch: `main`
- Hosting: Cloudflare Pages, triggered by pushes to GitHub
- Local repository: `C:\Users\ctibe\Documents\Codex\2026-07-23\new\sweepstakes-tracker`
- Release in this handoff: `v1.4`
- Release date: July 26, 2026

## Core product decision

The tracker is an inventory for helping users evaluate the risk of being scammed by sweepstakes opportunities. It is not primarily a company-review site.

Persistent sweepstakes platforms such as MondoSweeps and individual time-limited promotions such as Valvoline For the Driven belong in one unified inventory. Their difference is represented by type:

- persistent platforms continually publish new contests;
- limited promotions run for a defined period and end.

The older separate Active Sweepstakes concept was rejected because users did not understand why those entries were separate. The current local preview merges 16 limited promotions into the main inventory for a total of 45 entries.

## Current local preview

- Main unified inventory: http://127.0.0.1:4176/?preview=type-filter
- The local server has been running on port 4176.

## Version 1.3 release

### Unified inventory

- Merged 16 time-limited promotions into the main rankings inventory.
- Current generated inventory: 45 entries and 45 detail pages.
- Preserved the persistent-versus-limited distinction through the Type field.
- Generated detail pages for all limited promotions.

### Main-page type filter

- Added an `All site types` dropdown beside the search field.
- It combines correctly with search, ScamFactor filtering, and sorting.
- Verified counts:
  - Daily: 3
  - Directory: 10
  - Limited: 16
  - All types: 45

### Detail-page Site Type consistency

- The Site Type inside every detail-page Inventory Record now uses the styled pill treatment.
- Validation confirmed the pill on all 45 detail pages.

### Winstakes correction

- Downloaded and stored the actual Winstakes logo at `assets/logos/winstakes.png`.
- Added 15 current public prize records.
- Added direct official `Enter here` links for all 15 prizes.
- Added entry frequency, login requirements, dated public winner information where available, next-drawing guidance, and explicit verification dates.
- Winstakes profile status is browser-verified as of July 25, 2026.
- Removed the nonsensical `Known when last verified` wording from Winstakes.
- Added a template safeguard so old records containing that phrase render as a dated `Verified as listed on ...` statement.
- Updated the refresh adapter so Winstakes can use the browser-backed public-prize refresh path.

### Validation

The generator and validation currently pass:

- 45 merged inventory detail pages
- 16 active promotion source pages and inventory cards

## Audit and validation status

- 45 unified inventory detail pages are generated.
- 44 entries use stored logo assets; the BMW limited-promotion profile retains its safe fallback treatment.
- Recorded prize links were added wherever an exact public destination was verified.
- Prize records without a verified direct URL say so explicitly and include the date checked.
- The detail-page responsive layout keeps the compact ScamFactor card beside the logo/title at tablet widths and stacks only on narrower screens.
- The known-prizes layout uses available width without introducing horizontal scrolling.
- Validation passes for all 45 merged inventory pages and all 16 active promotion pages/cards.

## Version 1.4 traffic-growth release

- Added 10 indexable safety, strategy, comparison, and site-specific editorial guides.
- Added a homepage guide hub, contextual guide links on all 45 profiles, guide-to-profile links, and guide-to-guide navigation.
- Added four high-intent pages covering PrizeGrab legitimacy, PCH winner-notification scams, Sweepstakes Advantage alternatives, and daily-entry site comparisons.
- Added all guide routes to the sitemap and extended generated-site validation to cover guide output and internal links.
- Added IndexNow ownership verification and a GitHub workflow that notifies participating search engines after every production push.
- Google Search Console is connected, but its Performance report was still processing and showed no query data on July 26, 2026. Use impressions, clicks, CTR, queries, and pages once data appears to drive the next editorial cycle.

## Production authorization status

The user explicitly authorized the v1.4 production release on July 26, 2026.

## Important repository state

The worktree has many modified generated pages plus source/template changes and new limited-promotion detail pages. Preserve all of it.

Key modified source files include:

- `data.json`
- `scraper_simple.py`
- `refresh_site_details.py`
- `validate_generated.py`
- `templates/tracker.html.j2`
- `templates/review.html.j2`
- `assets/tracker.js`
- `assets/site.css`
- `assets/logos/winstakes.png`

Generated output is also modified across `index.html`, `reviews/`, category pages, sitemap, and promotion pages.

## Discovery automation

Commit `b2e9dd3` added a quarantined discovery workflow intended to find possible new sweepstakes opportunities up to human review. Discovery does not mean automatic publication. Candidates must be verified before entering the inventory.

## Editorial requirements

- The purpose is scam avoidance and risk transparency.
- ScamFactor runs from 1 to 10; lower is better.
- Profiles are inventory cards, not conventional affiliate reviews.
- Use official logos where practical.
- Use direct official prize-entry links where public.
- Use real dates for verification and winner evidence.
- Keep Site Type presentation consistent using the pill visual.
- Paid placement may be sold, but sponsorship must not silently alter the displayed risk score.
- Do not make unsourced scam claims.
- Never publish credentials or private login information.

## Safe continuation sequence

1. Read this handoff completely.
2. Inspect `git status` before touching the repository.
3. Open the current local unified-inventory preview.
4. Continue the 45-page logo and prize-link enrichment audit.
5. Rebuild with `scraper_simple.py`.
6. Run `validate_generated.py`.
7. Update this handoff and its Drive copy.
8. Commit intentionally, push `main`, wait for Cloudflare Pages, and verify production.
