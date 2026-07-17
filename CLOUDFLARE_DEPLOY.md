# Exact Cloudflare Pages Deploy Steps (2026)

These steps take ~10–15 minutes and give you a free, ultra-fast, unlimited-bandwidth site with free SSL.

## Prerequisites
- Free Cloudflare account → https://dash.cloudflare.com/sign-up
- Free GitHub account
- The `sweepstakes-scraper` folder (contains `index.html`)

---

## Step-by-Step

### 1. Put the site in a GitHub repo
```bash
cd /path/to/sweepstakes-scraper
git init
git add index.html scraper_v2.py data.json templates/ README.md
git commit -m "Initial SweepSafe tracker"
# Create a new empty repo on GitHub called e.g. sweepsafe-tracker
git remote add origin https://github.com/YOUR_USERNAME/sweepsafe-tracker.git
git branch -M main
git push -u origin main
```

### 2. Connect to Cloudflare Pages
1. Log into Cloudflare Dashboard
2. Left sidebar → **Workers & Pages**
3. Click **Create application** → **Pages** → **Connect to Git**
4. Authorize Cloudflare to access your GitHub
5. Select the `sweepsafe-tracker` repository
6. Click **Begin setup**

### 3. Build settings (very important)
- **Project name**: `sweepsafe` (or whatever you like – this becomes `sweepsafe.pages.dev`)
- **Production branch**: `main`
- **Framework preset**: `None` (or `Hugo` / leave blank)
- **Build command**: leave **empty**
- **Build output directory**: `/`   (or leave blank if index.html is at root)
- **Root directory** (if asked): `/` or empty

Click **Save and Deploy**.

Cloudflare will build and give you a live URL like:
`https://sweepsafe.pages.dev`

### 4. Custom Domain (highly recommended)
1. Buy a domain (Cloudflare Registrar is cheapest + seamless)
   Recommended: SweepSafe.com, DailyWinList.com, FreeLootTracker.com, etc.
2. In the Pages project → **Custom domains** → **Set up a custom domain**
3. Enter your domain → Cloudflare automatically adds the correct DNS records
4. Wait 1–5 minutes for free SSL to provision
5. Done – your site is now live on the custom domain with HTTPS

### 5. Automatic deploys
Every time you `git push` to `main`, Cloudflare rebuilds and deploys automatically (free).

### 6. Optional: Add a simple form for email list
Use Cloudflare Turnstile (free captcha) + a free form service, or Netlify Forms if you prefer Netlify.

---

## Alternative 1-Click Options

**Netlify** (even simpler for beginners)
1. Go to https://app.netlify.com
2. Drag & drop the entire `sweepstakes-scraper` folder (or just index.html)
3. Instant live URL + free custom domain support

**Vercel**
```bash
npx vercel
# follow prompts, choose the folder
```

---

## After Deploy Checklist
- [ ] Test all external links
- [ ] Add Google Analytics or Plausible (privacy-friendly)
- [ ] Submit sitemap to Google Search Console
- [ ] Add clear affiliate disclosure footer
- [ ] Share in freebie groups with value-first posts

You’re live! 🚀
