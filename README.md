# SafeTracker: Sweepstakes

**Sweepstakes safety rankings and source-linked winner reports.**

We rank sites by legitimacy and realistic chance of winning small prizes — not by hype or big jackpot promises.

### What you’ll find here
- Clear spammy-ness scores (1 = best, 10 = worst)
- Specific prize examples and draw frequencies
- How to unsubscribe from each site
- Major red flags for every entry
- Pros & cons of the main types of sites

### Important Safety Notes
- **Never pay money** to enter or claim a prize.
- Real sweepstakes are free.
- Use a dedicated / burner email.
- If someone contacts you saying you won and asks for fees, taxes, or shipping costs — it is a scam.

### Affiliate Disclosure
Some links on this site may be affiliate links. If you sign up through them we may earn a small commission at no extra cost to you. This helps keep the tracker free and updated. Rankings are never paid for or influenced by commissions.

### Updates
ScamFactor scores are recalculated, reranked, and republished weekly. Editorial
criterion values are updated when new evidence is verified. Always double-check
the official rules on each site before entering.

Winner reports are gathered daily from the feeds in `data/winner_sources.json`.
SQLite is the canonical historical archive (`data/winners.sqlite`); a generated
JSON export powers the searchable `winners.html` page. New reports are sent
through the active Winner Signal provider only when the daily run finds
something new. Buttondown remains the production default until the dedicated
Kit account passes the documented cutover gates. Each edition
also includes two rotating safety tips and a rotating link and synopsis from
the SafeTracker guide library. The public `guides.html` page is the canonical
archive for all weekly and evergreen guides. Adding an article to
`data/editorial.json` automatically adds it to that archive, the sitemap, and
the newsletter spotlight rotation unless `newsletter_exclude` is set to true.
Successfully accepted Winner Signal editions are also snapshotted to the
first-party `newsletter/` archive and added to its rebuilt index and sitemap.
Signup placements share `assets/winner-signal-config.js`; changing that single
public configuration after Kit validation updates the homepage, winner archive,
and newsletter archive without leaving a hidden Buttondown form behind.

Version 1.1 also includes the separate Active Sweepstakes inventory framework.
Individual promotions will live there rather than in the platform rankings.

---

Built for people who want real information instead of aggressive marketing.
