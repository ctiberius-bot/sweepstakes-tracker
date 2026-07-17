#!/usr/bin/env python3
"""
Sweepstakes Tracker Scraper v2
==============================
Improved version with:
- Better extraction
- Full HTML regeneration via Jinja2 template
- data.json as single source of truth
- Ready for Cloudflare Pages / Netlify / Vercel

Install:
  pip install requests beautifulsoup4 lxml jinja2 schedule

Usage:
  python scraper_v2.py                  # scrape + rebuild
  python scraper_v2.py --rebuild-only   # just rebuild HTML from data.json
  python scraper_v2.py --schedule       # daily at 06:00
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

try:
    import requests
    from bs4 import BeautifulSoup
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError as e:
    print("Missing dependency:", e)
    print("Run: pip install requests beautifulsoup4 lxml jinja2 schedule")
    raise

# ========== PATHS ==========
BASE = Path(__file__).parent
DATA_FILE = BASE / "data.json"
TEMPLATE_DIR = BASE / "templates"
TEMPLATE_FILE = "tracker.html.j2"
OUTPUT_HTML = BASE / "index.html"
USER_AGENT = "Mozilla/5.0 (compatible; SweepSafeBot/1.1; +https://yourdomain.com/bot-info)"
HEADERS = {"User-Agent": USER_AGENT}
TIMEOUT = 12

# ========== CORE SITE DATA (edit this as the master list) ==========
# This is the source of truth. Scraper only tries to refresh prize snippets.
MASTER_SITES = [
    {
        "rank": 1,
        "name": "Publishers Clearing House (PCH)",
        "score": 2,
        "theme": "legacy",
        "prizes": "$1M cash + Cadillac Escalade (major current); many cash, cars, vacations",
        "draw": "Variable by promotion; major winners often in-person Prize Patrol",
        "unsub": "Email footer unsubscribe link or contact PCH support",
        "redFlags": "Heavy impersonator scams (phone/texts asking for fees to claim). Real PCH never asks for money.",
        "link": "https://www.pch.com/",
        "affiliate_note": "Check FlexOffers / Impact for PCH campaigns",
        "scrape_url": "https://www.pch.com/"
    },
    {
        "rank": 2,
        "name": "Swagbucks",
        "score": 2,
        "theme": "rewards",
        "prizes": "Ongoing raffles for cash/gift cards (hundreds of millions paid historically)",
        "draw": "Ongoing raffles + daily earning opportunities via tasks",
        "unsub": "Account settings → Notifications, or email unsubscribe links",
        "redFlags": "Time-intensive for modest earnings; survey disqualifications common",
        "link": "https://www.swagbucks.com/",
        "affiliate_note": "Prodege / Impact / FlexOffers – typically $1–$3+ per verified signup",
        "scrape_url": "https://www.swagbucks.com/"
    },
    {
        "rank": 3,
        "name": "InboxDollars",
        "score": 3,
        "theme": "rewards",
        "prizes": "Cash & gift cards via activities + occasional sweepstakes/raffles",
        "draw": "Ongoing tasks + variable raffles",
        "unsub": "Account settings or email footer unsubscribe",
        "redFlags": "Modest payouts relative to time invested",
        "link": "https://www.inboxdollars.com/",
        "affiliate_note": "Impact / MaxBounty / Prodege – CPA around $2–$3 + residual %",
        "scrape_url": "https://www.inboxdollars.com/"
    },
    {
        "rank": 4,
        "name": "Mondosweeps",
        "score": 3,
        "theme": "daily",
        "prizes": "$1,548,705 lump sum; $500k Dream Home; $300k/$125k cash; $88k Dream Car; $25 Daily Cash (guaranteed one winner/day); $100 cash; $750/$1k GCs",
        "draw": "Daily drawings (entries by midnight ET; winners notified next day)",
        "unsub": "Email footer unsubscribe link or account preferences",
        "redFlags": "Aggressive daily marketing emails; big jackpots still long shots",
        "link": "https://www.mondosweeps.com/",
        "affiliate_note": "Check if they have partner program (often network-driven)",
        "scrape_url": "https://www.mondosweeps.com/"
    },
    {
        "rank": 5,
        "name": "Winstakes",
        "score": 3.5,
        "theme": "daily",
        "prizes": "Up to ~$1,542,625 lump sum cash; $25 Daily Cash; $50, $100, $750, $1,000 cash examples",
        "draw": "Daily ($25 Daily Cash guaranteed); some weekly",
        "unsub": "Email footer or dedicated unsubscribe page",
        "redFlags": "Similar spam volume to Mondosweeps",
        "link": "https://www.winstakes.com/",
        "affiliate_note": "Similar to Mondosweeps – look for network offers",
        "scrape_url": "https://www.winstakes.com/"
    },
    {
        "rank": 6,
        "name": "Prizegrab",
        "score": 3.5,
        "theme": "daily",
        "prizes": "$10k cash examples; $300 Shell GC; $25 Dunkin' GC; other gift cards & merchandise",
        "draw": "Daily winners guaranteed; ongoing promotions",
        "unsub": "Dedicated page: prizegrab.com/unsubscribe (or email footer)",
        "redFlags": "Data selling / spam calls after signup common complaint",
        "link": "https://prizegrab.com/",
        "affiliate_note": "Search affiliate networks for Prizegrab offers",
        "scrape_url": "https://prizegrab.com/"
    },
    {
        "rank": 7,
        "name": "Prizeloot",
        "score": 5.5,
        "theme": "globalizer",
        "prizes": "$499,999 cash; $77,777.77; $3,333 cash (multiple recent named winners); $200/$100/$20 Daily Cash; iPad, 50\" TV, drone, Stanley tumbler",
        "draw": "Daily entries & daily drawings/awards (resets midnight ET)",
        "unsub": "Email footer unsubscribe link",
        "redFlags": "Globalizer-style marketing volume; inconsistent big prize independent proof",
        "link": "https://www.prizeloot.com/",
        "affiliate_note": "Globalizer network – often have CPA offers",
        "scrape_url": "https://www.prizeloot.com/"
    },
    {
        "rank": 8,
        "name": "Million Dollar Media",
        "score": 3.5,
        "theme": "other",
        "prizes": "Brand-partnered cash, cars, merchandise (real user reports e.g. SodaStream)",
        "draw": "Varies by partnered campaign",
        "unsub": "Varies by specific promotion / email",
        "redFlags": "Depends entirely on the partner brand; some campaigns feel sales-driven",
        "link": "https://www.instagram.com/milliondollarmedia/",
        "affiliate_note": "Contact for brand campaign partnerships",
        "scrape_url": None
    },
    {
        "rank": 9,
        "name": "RetireWhiz",
        "score": 4,
        "theme": "niche",
        "prizes": "$250 cash; $5M Retirement Sweepstakes; $33k giveaway; ~$125k motorhome",
        "draw": "Daily or periodic (check specific rules for end dates)",
        "unsub": "Email preferences or contact support",
        "redFlags": "Retirement-niche marketing emails can be persistent",
        "link": "https://www.retirewhiz.com/",
        "affiliate_note": "Content site – check for partner links",
        "scrape_url": "https://www.retirewhiz.com/"
    },
    {
        "rank": 10,
        "name": "PINCHme (Free Samples)",
        "score": 5,
        "theme": "samples",
        "prizes": "Free product samples / full-size items (build box of 4 via quizzes + coins for free shipping)",
        "draw": "Ongoing daily samples; qualification-based (not pure chance)",
        "unsub": "Account settings or email unsubscribe",
        "redFlags": "Low-quality samples for many users; qualification frustration; site glitches reported",
        "link": "https://www.pinchme.com/",
        "affiliate_note": "Influencer / referral style – check their partner page",
        "scrape_url": "https://www.pinchme.com/"
    },
    {
        "rank": 11,
        "name": "PrizeCraze (Globalizer)",
        "score": 5.5,
        "theme": "globalizer",
        "prizes": "$25 Daily Cash (guaranteed one winner/day); bigger cash jackpots; Craze Coins for extra entries",
        "draw": "Daily drawings; one $25 guaranteed daily",
        "unsub": "Email footer or account preferences",
        "redFlags": "Network marketing volume; typical Globalizer spam",
        "link": "https://www.prizecraze.com/",
        "affiliate_note": "Globalizer network CPA",
        "scrape_url": "https://www.prizecraze.com/"
    },
    {
        "rank": 12,
        "name": "BlissXO",
        "score": 5,
        "theme": "samples",
        "prizes": "$125k instant win; $80k+ in cash prizes; free samples & deals focus",
        "draw": "Instant win + periodic drawings",
        "unsub": "Email preferences / footer link",
        "redFlags": "Spam association noted; freebie marketing intensity",
        "link": "https://blissxo.com/",
        "affiliate_note": "Check for partner/affiliate page",
        "scrape_url": "https://blissxo.com/"
    },
    {
        "rank": 13,
        "name": "Winloot (Globalizer)",
        "score": 5.5,
        "theme": "globalizer",
        "prizes": "$5M / $1M / $100k+ cash; $250 Daily Cash (guaranteed); $5k instant wins; many small cash/GCs/electronics",
        "draw": "Daily + instant wins (multiple entries/day possible)",
        "unsub": "Dedicated: sweepstakes.winloot.com/winloot-unsubscribe or email footer",
        "redFlags": "Highest complaint volume in network (non-payment claims + spam); mixed fulfillment reports",
        "link": "https://www.winloot.com/",
        "affiliate_note": "Globalizer – strong CPA potential",
        "scrape_url": "https://www.winloot.com/"
    },
    {
        "rank": 14,
        "name": "Daily Goodie Box",
        "score": 8.5,
        "theme": "samples",
        "prizes": "Free samples / full-size products in 'goodie boxes' (not guaranteed; based on brand campaigns & availability)",
        "draw": "Ongoing campaigns; receipt not guaranteed",
        "unsub": "Contact admin@dailygoodiebox.com or cancel account via site",
        "redFlags": "Many users report never receiving anything; impersonator messages; some similar 'box' reports of unexpected charges",
        "link": "https://dailygoodiebox.com/",
        "affiliate_note": "Avoid promoting heavily – high risk",
        "scrape_url": "https://dailygoodiebox.com/"
    },
    # ... remaining lower-ranked sites can be added the same way
    {
        "rank": 15,
        "name": "SelectRewards",
        "score": 9,
        "theme": "leadgen",
        "prizes": "Promised big gift cards (e.g. $750) via quizzes — user reports often low/no payout",
        "draw": "Funnel / quiz-based",
        "unsub": "Email unsubscribe if reachable",
        "redFlags": "Deceptive marketing; frequent reports of little to no real payout",
        "link": "#",
        "affiliate_note": "Do not promote",
        "scrape_url": None
    }
]

THEMES = [
    {
        "id": "legacy",
        "title": "1. Legacy Big-Brand Sweepstakes (PCH)",
        "pros": "Strong legitimacy, real big winners publicized, clear rules, decades of history.",
        "cons": "Extremely low odds on big prizes; massive impersonator scam problem targeting the brand."
    },
    {
        "id": "daily",
        "title": "2. Daily Small-Cash Portals (Mondosweeps, Winstakes, Prizeloot, PrizeCraze...)",
        "pros": "Best realistic win opportunity via published daily small winners ($20–$250); verifiable; free entry.",
        "cons": "Aggressive daily emails; big jackpots remain lottery-like long shots."
    },
    {
        "id": "rewards",
        "title": "3. Rewards / Task-Based Platforms (Swagbucks, InboxDollars)",
        "pros": "Reliable small cash/gift cards for actual effort; highly established and trustworthy payout history.",
        "cons": "Time-consuming; not pure chance; earnings often modest."
    },
    {
        "id": "globalizer",
        "title": "4. Globalizer Network Sweepstakes (Winloot, Prizeloot, PrizeCraze, etc.)",
        "pros": "Multiple daily entry chances; some guaranteed small daily cash; real small winners published on better properties.",
        "cons": "High marketing/spam volume; mixed fulfillment complaints; data practices."
    },
    {
        "id": "samples",
        "title": "5. Free Samples / Goodies Portals (PINCHme, Daily Goodie Box, BlissXO...)",
        "pros": "Actual free products when they arrive; no purchase required on better ones; fun for product testing.",
        "cons": "Inconsistent delivery; data harvesting; qualification hurdles; low-value items; subscription-trap risks in the category."
    },
    {
        "id": "niche",
        "title": "6. Niche / Content-Driven Sweepstakes (RetireWhiz, H2Tab)",
        "pros": "Relevant content + themed prizes; often clearer rules.",
        "cons": "Niche marketing emails can be persistent; big prizes still long shots."
    },
    {
        "id": "leadgen",
        "title": "7. Lead-Gen / Quiz Funnel Sites (SelectRewards, TheAmericanSurvey, Anytrivia)",
        "pros": "Can feel engaging with quizzes/surveys at first.",
        "cons": "Often deceptive promised rewards; heavy data collection; high disqualification or no real payout."
    },
    {
        "id": "other",
        "title": "8. Fulfillment Partners & Misc (Million Dollar Media, Lucky Sweeps...)",
        "pros": "Real winner reports on brand campaigns for fulfillment partners.",
        "cons": "Quality depends entirely on the specific partner/promotion; some versions confusing or casino-adjacent."
    }
]


def load_data() -> Dict:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_updated": None, "sites": MASTER_SITES, "live_snippets": {}}


def save_data(data: Dict):
    data["last_updated"] = datetime.utcnow().isoformat() + "Z"
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved {DATA_FILE}")


def fetch(url: str) -> str | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  ⚠ Failed {url}: {e}")
        return None


def extract_snippets(html: str, keywords: List[str]) -> List[str]:
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    results = []
    for tag in soup.find_all(["h1", "h2", "h3", "p", "li", "span", "div", "a"]):
        text = tag.get_text(" ", strip=True)
        if 20 < len(text) < 280 and any(k.lower() in text.lower() for k in keywords):
            # clean a bit
            text = re.sub(r"\s+", " ", text)
            results.append(text)
    # unique while preserving order
    seen = set()
    unique = []
    for t in results:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique[:12]


def scrape_live_data() -> Dict[str, Any]:
    print("Starting live scrape...")
    live = {}
    for site in MASTER_SITES:
        url = site.get("scrape_url")
        if not url:
            continue
        print(f"  → {site['name']}")
        html = fetch(url)
        if html:
            prizes = extract_snippets(html, ["$", "cash", "prize", "win", "giveaway", "daily", "guaranteed"])
            winners = extract_snippets(html, ["winner", "won", "congrats", "selected", "lucky"])
            live[site["name"]] = {
                "scraped_at": datetime.utcnow().isoformat() + "Z",
                "prize_snippets": prizes[:8],
                "winner_snippets": winners[:6]
            }
        time.sleep(1.8)  # be polite
    return live


def rebuild_html(data: Dict):
    """Full regeneration using Jinja2."""
    TEMPLATE_DIR.mkdir(exist_ok=True)
    # For simplicity we write a self-contained template that embeds the data
    # (in production you can load the previous HTML and inject, or keep a clean template)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"])
    )

    # If the template doesn't exist yet, we create a minimal one that still works
    template_path = TEMPLATE_DIR / TEMPLATE_FILE
    if not template_path.exists():
        print("Creating initial Jinja template...")
        create_initial_template(template_path)

    template = env.get_template(TEMPLATE_FILE)

    html = template.render(
        sites=data.get("sites", MASTER_SITES),
        themes=THEMES,
        last_updated=datetime.now().strftime("%B %d, %Y"),
        live_snippets=data.get("live_snippets", {}),
        generated_at=datetime.utcnow().isoformat() + "Z"
    )

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✓ Regenerated {OUTPUT_HTML}")


def create_initial_template(path: Path):
    """Create a clean Jinja2 template based on the original design."""
    # We keep it reasonably compact. You can expand styling later.
    content = r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SweepSafe – Legit Sweepstakes & Free Samples Tracker</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <style>
    .score-badge { font-weight:700; border-radius:9999px; padding:0.15rem 0.6rem; font-size:0.75rem; }
    .score-1,.score-2 { background:#dcfce7; color:#166534; }
    .score-3,.score-4 { background:#dbeafe; color:#1e40af; }
    .score-5,.score-6 { background:#fef3c7; color:#92400e; }
    .score-7,.score-8 { background:#ffedd5; color:#9a3412; }
    .score-9,.score-10 { background:#fee2e2; color:#991b1b; }
    th { position:sticky; top:0; background:#134e4a; color:white; }
    tr:nth-child(even) { background:#f0fdfa; }
  </style>
</head>
<body class="bg-slate-50 text-slate-800">
  <header class="bg-gradient-to-r from-teal-800 to-teal-600 text-white shadow-lg">
    <div class="max-w-7xl mx-auto px-4 py-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div>
        <h1 class="text-2xl md:text-3xl font-bold"><i class="fas fa-shield-alt mr-2"></i>SweepSafe Tracker</h1>
        <p class="text-teal-100 text-sm mt-1">Ranked by legitimacy + realistic win opportunity • Updated {{ last_updated }}</p>
      </div>
      <div class="text-right text-sm">
        <div>Last refresh: <strong>{{ last_updated }}</strong></div>
        <div class="opacity-80 text-xs mt-1">Generated {{ generated_at }}</div>
      </div>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-4 py-8">
    <!-- Safety Banner -->
    <div class="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6 text-sm">
      <strong class="text-amber-800"><i class="fas fa-exclamation-triangle mr-1"></i> Never pay to claim a prize.</strong>
      Real sweepstakes are free. Use a burner email. We may earn commissions from some links (disclosed).
    </div>

    <!-- Quick CTAs -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
      <a href="https://www.swagbucks.com/" target="_blank" rel="noopener sponsored"
         class="bg-teal-600 hover:bg-teal-700 text-white rounded-xl p-4 text-center font-semibold shadow transition">
        Start with Swagbucks → Reliable Daily Earnings
      </a>
      <a href="https://www.mondosweeps.com/" target="_blank" rel="noopener"
         class="bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl p-4 text-center font-semibold shadow transition">
        Try Mondosweeps → Best Daily $25 Chance
      </a>
      <a href="https://www.pch.com/" target="_blank" rel="noopener"
         class="bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl p-4 text-center font-semibold shadow transition">
        Enter PCH → America’s Most Trusted Big Prizes
      </a>
    </div>

    <!-- Table -->
    <div class="bg-white rounded-xl shadow border overflow-x-auto mb-10">
      <table class="w-full text-sm">
        <thead>
          <tr>
            <th class="px-3 py-3 text-left">#</th>
            <th class="px-3 py-3 text-left">Site</th>
            <th class="px-3 py-3 text-center">Score</th>
            <th class="px-3 py-3 text-left">Prizes</th>
            <th class="px-3 py-3 text-left">Draw / Frequency</th>
            <th class="px-3 py-3 text-left">Unsubscribe</th>
            <th class="px-3 py-3 text-left">Red Flags</th>
            <th class="px-3 py-3 text-center">Go</th>
          </tr>
        </thead>
        <tbody>
          {% for s in sites %}
          <tr class="border-b border-slate-100 hover:bg-teal-50/40">
            <td class="px-3 py-3 font-semibold text-slate-500">{{ s.rank }}</td>
            <td class="px-3 py-3 font-medium">{{ s.name }}</td>
            <td class="px-3 py-3 text-center">
              <span class="score-badge score-{{ s.score|int }}">{{ s.score }}</span>
            </td>
            <td class="px-3 py-3 text-xs max-w-xs">{{ s.prizes }}</td>
            <td class="px-3 py-3 text-xs">{{ s.draw }}</td>
            <td class="px-3 py-3 text-xs text-teal-700">{{ s.unsub }}</td>
            <td class="px-3 py-3 text-xs text-red-700">{{ s.redFlags }}</td>
            <td class="px-3 py-3 text-center">
              {% if s.link != "#" %}
              <a href="{{ s.link }}" target="_blank" rel="noopener" class="text-teal-600 hover:underline font-medium">Visit</a>
              {% else %}
              <span class="text-slate-400">—</span>
              {% endif %}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>

    <!-- Themes -->
    <h2 class="text-xl font-bold text-teal-800 mb-4">Major Themes – Pros & Cons</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-10">
      {% for t in themes %}
      <div class="bg-white rounded-xl border p-4 shadow-sm">
        <h3 class="font-bold text-teal-800 mb-2">{{ t.title }}</h3>
        <p class="text-sm mb-1"><span class="text-green-700 font-semibold">Pros:</span> {{ t.pros }}</p>
        <p class="text-sm"><span class="text-red-700 font-semibold">Cons:</span> {{ t.cons }}</p>
      </div>
      {% endfor %}
    </div>

    <footer class="text-center text-xs text-slate-500 py-6">
      Data last refreshed {{ last_updated }}. Always verify official rules. 
      We may earn a commission if you sign up through certain links.
    </footer>
  </main>
</body>
</html>
'''
    path.write_text(content, encoding="utf-8")
    print(f"✓ Created template {path}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild-only", action="store_true")
    parser.add_argument("--schedule", action="store_true")
    args = parser.parse_args()

    data = load_data()
    # Always keep master list as base
    data["sites"] = MASTER_SITES

    if not args.rebuild_only:
        live = scrape_live_data()
        data["live_snippets"] = live
        save_data(data)

    rebuild_html(data)

    if args.schedule:
        try:
            import schedule
            def job():
                d = load_data()
                d["sites"] = MASTER_SITES
                d["live_snippets"] = scrape_live_data()
                save_data(d)
                rebuild_html(d)
            schedule.every().day.at("06:00").do(job)
            print("Scheduled daily 06:00. Ctrl+C to stop.")
            while True:
                schedule.run_pending()
                time.sleep(30)
        except ImportError:
            print("pip install schedule for daily runs")


if __name__ == "__main__":
    main()
