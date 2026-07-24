# Weekly ScamFactor Rescoring

The tracker is refreshed automatically by GitHub Actions every Monday at
10:15 UTC. The workflow can also be run manually from the repository's Actions
tab.

## How it works

1. `.github/workflows/weekly-rescore.yml` starts the scheduled job.
2. `rescore_sites.py --check-live` checks each official site, recomputes the
   weighted ScamFactor score, sorts from lowest to highest, and assigns ranks.
3. `scraper_simple.py` regenerates the homepage, site profiles, and sponsorship
   page from the updated data.
4. The workflow commits the source data and all generated pages.
5. Cloudflare Pages detects the commit and publishes it.

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
