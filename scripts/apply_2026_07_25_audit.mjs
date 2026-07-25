import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const dataPath = path.join(root, "data.json");
const promosPath = path.join(root, "data", "active_sweepstakes.json");
const data = JSON.parse(fs.readFileSync(dataPath, "utf8"));
const promos = JSON.parse(fs.readFileSync(promosPath, "utf8"));

const checked = "July 25, 2026";

const promotionSources = {
  "pepsi-captain-ds-family-cruise": {
    entry_url: "https://www.captainds.com/pepsi-alaska/",
    rules_url: "https://bit.ly/FAMILYCRUISE",
  },
  "gold-peak-golf-sweepstakes": {
    entry_url: "https://www.coca-cola.com/us/en/offerings/gold-peak-tea/gold-peak-tea-sweepstakes",
    rules_url: "https://www.coca-cola.com/us/en/legal/coca-cola-meals-summer-sweeps",
  },
  "mathnasium-little-learners-adventure": {
    entry_url: "https://www.mathnasium.com/",
    rules_url: "https://www.mathnasium.com/",
  },
  "richell-july-pet-gate": {
    entry_url: "https://www.richellusa.com/richell-july-sweepstakes-2026/",
    rules_url: "https://www.richellusa.com/richell-july-sweepstakes-2026/",
  },
  "texas-roadhouse-rib-fest-truck": {
    entry_url: "https://form.texasroadhouse.com/national-dodge-ram-giveaway-2026",
    rules_url: "https://form.texasroadhouse.com/national-dodge-ram-giveaway-2026",
  },
  "pottery-barn-kids-back-to-school": {
    entry_url: "https://www.potterybarnkids.com/pages/bts-sweepstakes/",
    rules_url: "https://www.potterybarnkids.com/customer-service/legal/exclusive-offers/",
  },
  "fabfitfun-summer-dream": {
    entry_url: "https://fabfitfun.com/magazine/fabfitfun-summer-dream-sweepstakes/",
    rules_url: "https://fabfitfun.com/magazine/fabfitfun-summer-dream-sweepstakes/",
  },
  "coca-cola-wanta-fanta-blizzcon": {
    entry_url: "https://www.coca-cola.com/us/en/offerings/fanta/wanta-fanta",
    rules_url: "https://www.coca-cola.com/us/en/offerings/fanta/wanta-fanta",
  },
  "hallmark-gold-crown-cruise": {
    entry_url: "https://www.hallmarkgoldcrownsweepstakes.com/",
    rules_url: "https://www.hallmarkgoldcrownsweepstakes.com/",
  },
  "bmw-summer-of-soccer": {
    entry_url: "https://2026dempseytrackday.eventsbmw.com/#rsvp",
    rules_url: "https://2026dempseytrackday.eventsbmw.com/",
  },
  "coors-light-soccer-cash": {
    entry_url: "https://www.coorslight.com/en-US/soccer",
    rules_url: "https://www.promorules.com/MK262618",
  },
  "kubota-hometown-proud": {
    entry_url: "https://www.kubotahometownproud.com/winandgivesweepstakes",
    rules_url: "https://www.kubotausa.com/docs/default-source/default-document-library/kubota-hometown-proud-sweepstakes-2026-official-rules.pdf",
  },
};

for (const promo of promos.promotions) {
  const verified = promotionSources[promo.slug];
  if (verified) {
    Object.assign(promo, verified);
    promo.source_url = verified.entry_url;
    promo.source_name = "Official sponsor promotion page";
  } else {
    promo.verification_note =
      `Checked ${checked}; an authoritative exact entry URL was not independently verified, so the dated third-party source remains visible.`;
  }
  promo.last_verified = checked;
  promo.logo_asset = `assets/logos/${promo.slug}.png`;
}
promos.updated_at = "2026-07-25";

const directorySlugs = new Set([
  "contest-girl", "sweepstakes-advantage", "online-sweepstakes-com",
  "sweepstake-com", "sweepstoday", "i-love-free-things-ilft",
  "i-love-giveaways", "sweepfeed", "esweeps", "localfreebie",
  "robin-giveaways", "winprizesonline", "sweetie-sweepstakes",
  "the-luck-foundry",
]);

for (const site of data.sites) {
  const candidateLogo = `assets/logos/${site.slug}.png`;
  site.logo_asset = fs.existsSync(path.join(root, candidateLogo))
    ? candidateLogo
    : (site.logo_asset || "");
  for (const prize of site.prize_items || []) {
    prize.status = `Verified as listed on ${checked}`;
    prize.last_verified = checked;
    if (!prize.entry_url && directorySlugs.has(site.slug) && site.link !== "#") {
      prize.entry_url = site.link;
      prize.link_note = "Official public listings page; individual promotions link onward to sponsor entry pages.";
    } else if (!prize.entry_url) {
      prize.verification_note =
        `No exact public prize-entry URL independently verified on ${checked}; no link supplied.`;
    }
  }
}

const mondo = data.sites.find((site) => site.slug === "mondosweeps");
if (mondo) {
  const mondoLinks = new Map([
    ["$10,000 Super Home Theater", "https://www.mondosweeps.com/Sweepstakes/sweepstakes-10000-Super-H"],
    ["$100 cash", "https://www.mondosweeps.com/Sweepstakes/mondosweeps-Visa-Gift-Car"],
  ]);
  for (const prize of mondo.prize_items || []) {
    if (!prize.entry_url && mondoLinks.has(prize.label)) {
      prize.entry_url = mondoLinks.get(prize.label);
      delete prize.verification_note;
    }
  }
}

for (const promo of promos.promotions) {
  const candidateLogo = `assets/logos/${promo.slug}.png`;
  promo.logo_asset = fs.existsSync(path.join(root, candidateLogo)) ? candidateLogo : "";
}

data.last_updated = "2026-07-25";
data.last_profile_refresh = "2026-07-25";
fs.writeFileSync(dataPath, `${JSON.stringify(data, null, 2)}\n`);
fs.writeFileSync(promosPath, `${JSON.stringify(promos, null, 2)}\n`);

console.log(`Updated ${data.sites.length} persistent records and ${promos.promotions.length} limited promotions.`);
