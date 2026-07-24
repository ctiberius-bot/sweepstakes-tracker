# Automated profile updates and ScamFactor rescoring

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

## Manual run

Open the repository's **Actions** tab, choose **Weekly ScamFactor Rescore**, and
select **Run workflow**.

## Daily winner reports

The `Daily winner reports` workflow runs at 11:15 UTC. It checks the source
feeds in `data/winner_sources.json`, updates the public winners archive, and
sends one Buttondown edition only when new reports are found. It stores source
IDs in `data/winner_state.json` so reports are not repeated. The repository
secret `BUTTONDOWN_API_KEY` is required for sending.
