# How to Automate Daily Updates

This guide shows you the easiest free way to automatically rebuild and publish a fresh `index.html` every day.

## Recommended Method: GitHub Actions (Free)

GitHub Actions can run your scraper every day, rebuild the page, and automatically update your Cloudflare Pages site.

### Step-by-step Setup

#### 1. Put the full project on GitHub
You need **all** these files in one GitHub repository:

- `index.html`
- `scraper_simple.py`   ← currently the reliable one
- `templates/` folder (with `tracker.html.j2`)
- `.github/workflows/daily-update.yml`  ← the automation file I just created
- `robots.txt`
- `README.md`

(You can also include the other files if you want.)

#### 2. Connect the GitHub repo to Cloudflare Pages
If you haven’t already:

1. Cloudflare Dashboard → **Workers & Pages**
2. Create a new Pages project → **Connect to Git**
3. Select your GitHub repository
4. Build settings:
   - Framework preset: `None`
   - Build command: leave empty
   - Build output directory: leave empty (or `/`)
5. Save and Deploy

From now on, every time the `main` branch updates, Cloudflare will automatically redeploy the site.

#### 3. Enable the daily workflow
The file `.github/workflows/daily-update.yml` is already set to:

- Run every day at **10:00 UTC** (6:00 AM Eastern Time)
- Also allow manual runs

After you push the workflow file to GitHub:

1. Go to your GitHub repository
2. Click the **Actions** tab
3. You should see “Daily Sweepstakes Update”
4. You can click **Run workflow** to test it immediately

#### 4. How it works
1. GitHub Actions starts a free virtual machine
2. It installs Python + required packages
3. Runs `scraper_simple.py` (rebuilds `index.html`)
4. Commits the new `index.html` if anything changed
5. Pushes to GitHub
6. Cloudflare Pages detects the push and redeploys the live site automatically

---

## Alternative Options

| Method                    | Difficulty | Cost     | Notes                              |
|--------------------------|------------|----------|------------------------------------|
| **GitHub Actions**       | Easy       | Free     | Best overall choice                |
| Cloudflare Workers Cron  | Medium     | Free     | More complex for full HTML rebuild |
| Local computer + Task Scheduler | Easy | Free     | Only works when your PC is on      |
| PythonAnywhere / Railway | Medium     | Free tier| Good if you want the scraper online|
| Make.com / n8n           | Medium     | Free tier| No-code but limited for this use   |

---

## Important Notes

- The current reliable scraper is `scraper_simple.py` (it uses the curated list and does not need internet).
- When you later improve `scraper_v2.py` to successfully fetch live prize data, just change the workflow line to run `scraper_v2.py` instead.
- GitHub Actions free tier gives you plenty of minutes for a once-per-day job.
- Always keep a clear affiliate disclosure on the site.

---

Would you like me to also create a version of the workflow that tries the live scraper (`scraper_v2.py`) and falls back to the simple version if it fails?
