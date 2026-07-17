#!/usr/bin/env python3
"""
Simplified Sweepstakes Tracker Rebuilder
========================================
No internet required. Just regenerates a clean index.html
from the master site list using Jinja2.

Usage:
  python3 scraper_simple.py
"""

from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE = Path(__file__).parent
TEMPLATE_DIR = BASE / "templates"
OUTPUT_HTML = BASE / "index.html"

# ========== MASTER DATA ==========
MASTER_SITES = [
    {
        "rank": 1,
        "name": "Publishers Clearing House (PCH)",
        "score": 2,
        "theme": "legacy",
        "prizes": "$1M cash + Cadillac Escalade (major current); many cash, cars, vacations",
        "draw": "Variable by promotion; major winners often in-person Prize Patrol",
        "unsub": "Email footer unsubscribe link or contact PCH support",
        "redFlags": "Heavy impersonator scams (phone/texts asking for fees). Real PCH never asks for money.",
        "link": "https://www.pch.com/",
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
    },
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
    },
]

THEMES = [
    {
        "title": "1. Legacy Big-Brand Sweepstakes (PCH)",
        "pros": "Strong legitimacy, real big winners publicized, clear rules, decades of history.",
        "cons": "Extremely low odds on big prizes; massive impersonator scam problem targeting the brand."
    },
    {
        "title": "2. Daily Small-Cash Portals (Mondosweeps, Winstakes, Prizeloot, PrizeCraze...)",
        "pros": "Best realistic win opportunity via published daily small winners ($20–$250); verifiable; free entry.",
        "cons": "Aggressive daily emails; big jackpots remain lottery-like long shots."
    },
    {
        "title": "3. Rewards / Task-Based Platforms (Swagbucks, InboxDollars)",
        "pros": "Reliable small cash/gift cards for actual effort; highly established and trustworthy payout history.",
        "cons": "Time-consuming; not pure chance; earnings often modest."
    },
    {
        "title": "4. Globalizer Network Sweepstakes (Winloot, Prizeloot, PrizeCraze, etc.)",
        "pros": "Multiple daily entry chances; some guaranteed small daily cash; real small winners published on better properties.",
        "cons": "High marketing/spam volume; mixed fulfillment complaints; data practices."
    },
    {
        "title": "5. Free Samples / Goodies Portals (PINCHme, Daily Goodie Box, BlissXO...)",
        "pros": "Actual free products when they arrive; no purchase required on better ones; fun for product testing.",
        "cons": "Inconsistent delivery; data harvesting; qualification hurdles; low-value items; subscription-trap risks."
    },
    {
        "title": "6. Niche / Content-Driven Sweepstakes (RetireWhiz)",
        "pros": "Relevant content + themed prizes; often clearer rules.",
        "cons": "Niche marketing emails can be persistent; big prizes still long shots."
    },
    {
        "title": "7. Lead-Gen / Quiz Funnel Sites (SelectRewards etc.)",
        "pros": "Can feel engaging with quizzes/surveys at first.",
        "cons": "Often deceptive promised rewards; heavy data collection; high disqualification or no real payout."
    },
    {
        "title": "8. Fulfillment Partners & Misc (Million Dollar Media etc.)",
        "pros": "Real winner reports on brand campaigns for fulfillment partners.",
        "cons": "Quality depends entirely on the specific partner/promotion."
    },
]


def score_class(score):
    s = float(score)
    if s <= 2: return "score-1"
    if s <= 4: return "score-3"
    if s <= 6: return "score-5"
    if s <= 8: return "score-7"
    return "score-9"


def main():
    TEMPLATE_DIR.mkdir(exist_ok=True)
    template_path = TEMPLATE_DIR / "tracker.html.j2"

    # Always write a clean, self-contained template
    template_content = r'''<!DOCTYPE html>
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
    th { position:sticky; top:0; background:#134e4a; color:white; z-index:10; }
    tr:nth-child(even) { background:#f0fdfa; }
    .filter-active { background:#0f766e !important; color:white !important; }
  </style>
</head>
<body class="bg-slate-50 text-slate-800 min-h-screen">
  <header class="bg-gradient-to-r from-teal-800 to-teal-600 text-white shadow-lg">
    <div class="max-w-7xl mx-auto px-4 py-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div>
        <h1 class="text-2xl md:text-3xl font-bold flex items-center gap-2">
          <i class="fas fa-shield-alt"></i> SweepSafe Tracker
        </h1>
        <p class="text-teal-100 text-sm mt-1">Ranked by legitimacy + realistic win opportunity • Updated {{ last_updated }}</p>
      </div>
      <div class="text-right text-sm opacity-90">
        <div>Last refresh</div>
        <div class="font-semibold text-lg">{{ last_updated }}</div>
      </div>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-4 py-8">
    <!-- Safety -->
    <div class="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6 text-sm">
      <strong class="text-amber-800"><i class="fas fa-exclamation-triangle mr-1"></i> Never pay to claim a prize.</strong>
      Real sweepstakes are free. Use a burner email. We may earn a commission from some links (clearly disclosed).
    </div>

    <!-- Top CTAs -->
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

    <!-- Framework -->
    <div class="bg-white rounded-xl shadow-sm border p-5 mb-6">
      <h2 class="font-bold text-teal-800 mb-2">Spammy-ness Score (1 = Best, 10 = Worst)</h2>
      <div class="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
        <div class="bg-teal-50 p-2 rounded">30% Transparency & Winner Proof</div>
        <div class="bg-teal-50 p-2 rounded">25% Fulfillment & Complaints</div>
        <div class="bg-teal-50 p-2 rounded">20% Entry Model & Gotchas</div>
        <div class="bg-teal-50 p-2 rounded">15% Win Opportunity Realism</div>
        <div class="bg-teal-50 p-2 rounded">10% Marketing Aggressiveness</div>
      </div>
    </div>

    <!-- Table -->
    <div class="bg-white rounded-xl shadow border overflow-x-auto mb-10">
      <table class="w-full text-sm">
        <thead>
          <tr>
            <th class="px-3 py-3 text-left">#</th>
            <th class="px-3 py-3 text-left">Site</th>
            <th class="px-3 py-3 text-center">Score</th>
            <th class="px-3 py-3 text-left">Prizes (examples)</th>
            <th class="px-3 py-3 text-left">Draw Frequency</th>
            <th class="px-3 py-3 text-left">Unsubscribe</th>
            <th class="px-3 py-3 text-left">Major Red Flags</th>
            <th class="px-3 py-3 text-center">Link</th>
          </tr>
        </thead>
        <tbody>
          {% for s in sites %}
          <tr class="border-b border-slate-100 hover:bg-teal-50/50">
            <td class="px-3 py-3 font-semibold text-slate-500">{{ s.rank }}</td>
            <td class="px-3 py-3 font-medium">{{ s.name }}</td>
            <td class="px-3 py-3 text-center">
              <span class="score-badge {{ score_class(s.score) }}">{{ s.score }}</span>
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

    <footer class="text-center text-xs text-slate-500 py-6 border-t">
      Data last refreshed {{ last_updated }}. Always verify official rules on each site.<br>
      Some links may be affiliate links. We may earn a commission at no extra cost to you. Rankings are never paid.
    </footer>
  </main>
</body>
</html>
'''

    template_path.write_text(template_content, encoding="utf-8")

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"])
    )
    env.globals["score_class"] = score_class

    template = env.get_template("tracker.html.j2")
    html = template.render(
        sites=MASTER_SITES,
        themes=THEMES,
        last_updated=datetime.now().strftime("%B %d, %Y")
    )

    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"✓ Successfully rebuilt {OUTPUT_HTML}")
    print(f"  → {len(MASTER_SITES)} sites included")
    print(f"  → Open the file in your browser or deploy it to Cloudflare Pages")


if __name__ == "__main__":
    main()
