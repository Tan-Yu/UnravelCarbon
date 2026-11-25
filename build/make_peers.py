"""Builds peers/peers.json: hand-curated peer facts, each verified against the extracted page text.
Every fact has a page and an exact 'check' string that must appear in that page's text, or the build fails."""
import json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
norm = lambda s: re.sub(r"\s+", " ", s)
PAGES = {n: {p["page"]: norm(p["text"]) for p in json.load(open(ROOT / f"build/peer{n}_emissions_report.json"))} for n in (1, 2)}

def F(metric, value, unit, page, check, note=""): return dict(metric=metric, value=value, unit=unit, page=page, check=check, note=note)

PEERS = [
 dict(id="docusign", name="Docusign", report="Docusign Impact Report FY25", pdf="peer1_emissions_report.pdf", file_no=1,
      period="FY25 (1 Feb 2024 - 31 Jan 2025)", boundary="Company-wide; Scope 1, 2 and specified Scope 3 categories (3.1-3.3, 3.5-3.8 shown); limited assurance by Apex (p.52)",
      facts=[
        F("scope1", 449, "tCO2e", 50, "Scope 1 449 tCO2e 449 tCO2e"),
        F("scope2_market", 3.1, "tCO2e", 49, "Energy indirect (scope 2) GHG emissions 3.1 tCO2e"),
        F("scope2_location", 8545, "tCO2e", 50, "8,545 tCO2e"),
        F("scope3_total", 132058, "tCO2e", 49, "Other indirect (scope 3) GHG emissions 132,058 tCO2e"),
        F("scope3_cat_3.1_purchased_goods_market", 101018, "tCO2e", 50, "101,018 tCO2e"),
        F("scope3_cat_3.6_business_travel", 16957, "tCO2e", 50, "3.6 business travel 16,957 tCO2e"),
        F("scope3_cat_3.7_employee_commuting", 7610, "tCO2e", 50, "3.7 employee commuting 7,610 tCO2e"),
        F("intensity", 45, "tCO2e per $1M revenue", 49, "GHG emissions intensity 45 tCO2e per $1M"),
        F("renewable_electricity_share", 100, "%", 49, "% renewable electricity 100%"),
        F("assurance", "limited assurance verification (Apex Companies)", "", 52, "limited assurance verification"),
        F("targets", "SBTi-approved near-term and net-zero targets; net zero by 2050", "", 28, "net-zero by 2050"),
      ]),
 dict(id="shopify", name="Shopify", report="Shopify 2024 Climate Report", pdf="peer2_emissions_report.pdf", file_no=2,
      period="Calendar year 2024", boundary="Operational emissions only: Scope 1 (building gas), Scope 2 (building electricity), Scope 3.6 business travel, Scope 3.7 employee home offices. No other Scope 3 categories reported (p.18)",
      facts=[
        F("scope1", 360, "tCO2e", 19, "360", "read from the p.19 waterfall chart label 'Scope 1 emissions (building natural gas)'"),
        F("scope2", 319, "tCO2e", 19, "319", "chart label 'Scope 2 emissions (building electricity)'"),
        F("scope3_cat_3.6_business_travel", 21959, "tCO2e", 19, "21,959", "chart label 'Scope 3.6 emissions (business travel)'"),
        F("scope3_cat_3.7_employee_home_office", 1663, "tCO2e", 19, "1,663", "chart label 'Scope 3.7 emissions (home office energy)'"),
        F("boundary_statement", "Scope 1, Scope 2, Scope 3.6 and Scope 3.7 are the operational emissions counted", "", 18, "Scope 1, Scope 2, Scope 3.6, and Scope 3.7—that we count as our operational emissions"),
        F("carbon_removal_retired", 22525, "tCO2e (8,072 durable + 14,453 nature-based)", 19, "14,453"),
        F("building_emissions_change", -72, "% year over year", 18, "decreased by 72 percent"),
      ]),
]
bad = []
for p in PEERS:
    for f in p["facts"]:
        if norm(f["check"]) not in PAGES[p["file_no"]][f["page"]]: bad.append((p["id"], f["metric"], f["page"], f["check"]))
assert not bad, f"unverified facts: {bad}"
(ROOT / "peers").mkdir(exist_ok=True)
json.dump(PEERS, open(ROOT / "peers/peers.json", "w"), indent=1)
print("peers.json written;", sum(len(p["facts"]) for p in PEERS), "facts verified")
