#!/usr/bin/env python3
"""
Simplified Sweepstakes Tracker Rebuilder
========================================
No internet required. Just regenerates a clean index.html
from the master site list using Jinja2.
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
    # Add your other sites here (I kept a few for example)
    {
        "rank": 2,
        "name": "Swagbucks",
        "score": 2,
        "theme": "rewards",
        "prizes": "Ongoing raffles for cash/gift cards",
        "draw": "Ongoing raffles + daily earning opportunities",
        "unsub": "Account settings → Notifications",
        "redFlags": "Time-intensive for modest earnings",
        "link": "https://www.swagbucks.com/",
    },
    # ... add the rest of your sites here
]

THEMES = [
    # Your themes here (optional)
]

def main():
    TEMPLATE_DIR.mkdir(exist_ok=True)
    template_path = TEMPLATE_DIR / "tracker.html.j2"

    template_content = r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SweepSafe – Legit Sweepstakes & Free Samples Tracker</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <style>
    th { position:sticky; top:0; background:#134e4a; color:white; z-index:10; }
    tr:nth-child(even) { background:#f0fdfa; }
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
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-4 py-8">
    <!-- Safety -->
    <div class="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6 text-sm">
      <strong class="text-amber-800"><i class="fas fa-exclamation-triangle mr-1"></i> Never pay to claim a prize.</strong>
      Real sweepstakes are free. Use a burner email. We may earn a commission from some links.
    </div>

    <!-- Top CTAs -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
      <a href="https://www.swagbucks.com/" target="_blank" rel="noopener sponsored" class="bg-teal-600 hover:bg-teal-700 text-white rounded-xl p-4 text-center font-semibold shadow transition">
        Start with Swagbucks → Reliable Daily Earnings
      </a>
      <a href="https://www.mondosweeps.com/" target="_blank" rel="noopener" class="bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl p-4 text-center font-semibold shadow transition">
        Try Mondosweeps → Best Daily $25 Chance
      </a>
      <a href="https://www.pch.com/" target="_blank" rel="noopener" class="bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl p-4 text-center font-semibold shadow transition">
        Enter PCH → America’s Most Trusted Big Prizes
      </a>
    </div>

    <!-- Framework -->
    <div class="bg-white rounded-xl shadow-sm border p-5 mb-6">
      <h2 class="font-bold text-teal-800 mb-2 flex items-center gap-3">
        <img src="scamfactor-logo.jpg" alt="ScamFactor" width="180" height="48">
        <span class="text-xs bg-red-100 text-red-700 px-3 py-1 rounded-full font-normal">Higher = more red flags, hidden fees, aggressive spam</span>
      </h2>
      <div class="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs mt-4">
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
            <th class="px-3 py-3 text-center">ScamFactor</th>
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
              <span class="inline-flex items-center gap-1 bg-red-100 text-red-700 px-3 py-1 rounded-full text-sm font-bold">
                ScamFactor: {{ s.score }}
              </span>
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

    <footer class="text-center text-xs text-slate-500 py-6 border-t">
      Data last refreshed {{ last_updated }}. Always verify official rules on each site.<br>
      Some links may be affiliate links. Rankings are never paid.
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

    template = env.get_template("tracker.html.j2")
    html = template.render(
        sites=MASTER_SITES,
        last_updated=datetime.now().strftime("%B %d, %Y")
    )

    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"✓ Successfully rebuilt {OUTPUT_HTML}")

if __name__ == "__main__":
    main()