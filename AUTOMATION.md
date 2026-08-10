# Automated profile updates and ScamFactor rescoring

## Daily candidate discovery

`.github/workflows/daily-discovery.yml` runs at 09:30 UTC and can also be
started manually. It scans the public sources in
`data/discovery_sources.json`, extracts possible recurring sweepstakes and
limited promotions, removes known inventory URLs and tracking parameters,
classifies each candidate provisionally, and merges it into
`data/discovery_candidates.json`.

The job deliberately stops before publication. It does not edit `data.json`,
assign a ScamFactor score, rebuild the site, or deploy a candidate. Its only
outputs are the quarantine queue and `DISCOVERY_REVIEW.md`, which is also shown
in the GitHub Actions run summary.

Before approval, a reviewer must verify the official entry page, official
rules, sponsor, prize, eligibility, closing date or recurring schedule, free
entry method, entry limits, marketing consent, and evidence for all five
ScamFactor criteria. Change a candidate's `status` only after that review.
Promotion into the public inventory remains a separate, intentional step.

## Weekly controlled inventory review

`.github/workflows/weekly-inventory-review.yml` runs every Monday at 13:00 UTC.
It checks currently published operator URLs for removal signals, creates a
separate removal quarantine queue, and opens a dated GitHub review issue with a
link to the protected `/admin/` Review Desk.

The Review Desk records approve, reject, and defer decisions in the existing
Cloudflare D1 database with the reviewer identity and an append-only audit
record. Approval is not publication. No discovery or removal changes
`data.json`, generated pages, or production until a separate production
preparation and release is explicitly approved.

## Daily profile refresh

The tracker checks every public profile source daily at 12:45 UTC. The refresh
records source availability, redirects, content changes, and the last successful
check. Supported structured adapters update verified prize and winner details;
the MondoSweeps adapter currently rebuilds its complete public prize inventory.

If a site blocks automated requests or requires a member login, the job preserves
the last curated facts and labels the source status instead of guessing. Research
account credentials are never stored in this repository or GitHub Actions.

The generator then rebuilds all detail pages, the homepage, sitemap, and supporting
pages, even when only one source changed. Cloudflare Pages publishes the commit.

Run it manually from **Actions → Daily site profile refresh → Run workflow**.

## Weekly ScamFactor rescoring

The tracker is refreshed automatically by GitHub Actions every Monday at
10:15 UTC. The workflow can also be run manually from the repository's Actions
tab.

## How it works

1. `.github/workflows/weekly-rescore.yml` starts the scheduled job.
2. `refresh_site_details.py` refreshes public profile evidence and known prizes.
3. `rescore_sites.py --check-live` checks each official site, recomputes the
   weighted ScamFactor score, sorts from lowest to highest, and assigns ranks.
4. `scraper_simple.py` regenerates the homepage, every site profile, and sponsorship
   page from the updated data.
5. The workflow commits the source data and all generated pages.
6. Cloudflare Pages detects the commit and publishes it.

## Scoring inputs

Each `data.json` record has a `score_inputs` object with the five published
criteria:

- `transparency` — 30%
- `fulfillment` — 25%
- `entry_model` — 20%
- `win_realism` — 15%
- `marketing` — 10%

Values must be between 1 and 10. A site that is unreachable during the weekly
check receives a temporary 0.5-point operational-risk adjustment. Bot-protected
responses such as 401, 403, and 429 do not receive that adjustment.

The scheduled calculation keeps the inventory current and consistently ordered.
The editorial criterion values should still be updated whenever new evidence,
complaints, rules, fulfillment history, or marketing practices are verified.

## Signal Command approval publication

`.github/workflows/publish-approved.yml` polls the protected Signal Command
publication queue every five minutes. An approval enters this queue only after
the reviewer completes all public profile fields and evidence for all five
ScamFactor inputs. The Sweepstakes adapter validates the manifest again, updates
`data.json`, regenerates every inventory card and profile, runs the full generated
site validation, pushes the production source, and acknowledges the live profile
URL back to Signal Command.

The queue uses a versioned, tracker-neutral manifest. See
`TRACKER_PUBLICATION_ADAPTER.md` for the contract used by other SafeTracker
verticals. Approval is publication only when this evidence-complete workflow is
used; legacy review decisions without a publication manifest remain unpublished.

## Manual run

Open the repository's **Actions** tab, choose **Weekly ScamFactor Rescore**, and
select **Run workflow**.

## Daily winner reports

The `Daily winner reports` workflow runs at 11:15 UTC. It checks the source
feeds in `data/winner_sources.json`, updates the public winners archive, and
publishes one edition only when new reports are found. It stores source IDs in
`data/winner_state.json` so reports are not repeated. Buttondown remains the
production delivery provider unless the explicit Kit cutover gate below is
approved. This preserves daily delivery while the Kit account is reviewed.

After either provider accepts the edition, the job marks the reports delivered,
snapshots the edition to `data/newsletter_editions.json`, writes its permanent
page under `newsletter/`, rebuilds `newsletter/index.html`, and adds the public
archive URL to `sitemap.xml`. Marking happens before archive rendering so a
rendering failure cannot cause a duplicate email on the next daily run; the
workflow failure alert still makes an archive problem visible.

Delivery runs only when `WINNER_NEWSLETTER_ENABLED` is `true`. The workflow uses
Buttondown and `BUTTONDOWN_API_KEY` by default. It uses Kit and `KIT_API_KEY`
only when the repository variable `WINNER_NEWSLETTER_KIT_CUTOVER` is exactly
`approved`. Kit broadcasts are scheduled with `public: false`, so daily emails
are not published to Kit's public newsletter feed.

Do not set the Kit cutover variable until all of these are true:

1. Kit has removed the disabled-features banner and Support has approved the
   dedicated `sweepstakes-research@safetrackerhub.com` account.
2. `winners@safetrackerhub.com` is the verified default sender with the display
   name `Winner Signal by SafeTracker` and the Kit email template contains the
   required unsubscribe control and physical mailing address.
3. A V4 API key from that account is saved as the `KIT_API_KEY` repository
   secret, and a private draft proves broadcast creation works without a live
   send.
4. A Kit form named `Winner Signal` is published with confirmation email on,
   auto-confirm off, and subscriber-data forwarding off. Its immediate redirect
   is `https://sweeps.safetrackerhub.com/newsletter/thanks.html`; its
   post-confirmation redirect is
   `https://sweeps.safetrackerhub.com/newsletter/confirmed.html`.
5. The exact Kit JavaScript embed UID and source are entered in
   `assets/winner-signal-config.js`, the public signup `provider` is changed to
   `kit`, and an incognito walkthrough confirms the form, redirects, confirmed
   subscriber state, branding, analytics event, and unsubscribe footer.

Until those gates pass, keep the signup provider and delivery provider on
Buttondown. Do not remove `BUTTONDOWN_API_KEY`, subscribers, tags, or account
configuration during the overlap period.

The manual `Configure Winner Signal branding` workflow applies and reads back
the approved temporary Buttondown overlap settings using the encrypted
`BUTTONDOWN_API_KEY`. It does not create an email or change subscriber state.
It sets the newsletter and sender display names, brand color, time zone,
double-opt-in confirmation copy, and the first-party pre- and post-confirmation
redirects. Run it after deploying changes to `newsletter/thanks.html` or
`newsletter/confirmed.html`, never before those URLs are publicly reachable.
