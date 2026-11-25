"""Peer comparison tool. Peer facts are hand-curated and page-verified (build/make_peers.py -> peers/peers.json).
The tool never converts or normalises silently: it returns both sides plus the comparability caveats."""
import json
from pathlib import Path
import emissions_tools as et

PEERS = json.load(open(Path(__file__).resolve().parent / "peers/peers.json"))


def compare_with_peers() -> dict:
    t = et.totals()
    co = {k: dict(tonnes=v["tonnes"], months=v["months"], period=v["period"]) for k, v in t.items() if k.startswith("scope")}
    for k, v in co.items():   # naive annualisation, shown separately and labelled
        v["annualised_tonnes_if_flat"] = round(v["tonnes"] * 12 / v["months"], 1) if v["months"] < 12 else None
    items = []
    for p in PEERS:
        for f in p["facts"]:
            items.append(dict(peer=p["name"], period=p["period"], metric=f["metric"], value=f["value"], unit=f["unit"],
                              page=f["page"], report=p["report"], note=f["note"]))
    caveats = [
        "Different boundaries: Shopify reports operational emissions only (Scope 1, 2, 3.6, 3.7); Docusign reports Scope 1, 2 and specified Scope 3 categories. Company Scope 3 spans many more categories.",
        "Docusign Scope 2 is shown both market-based (3.1) and location-based (8,545); the company's Scope 2 method is unknown (dual reporting not verified).",
        "Periods differ: company Scope 1 and 2 cover 3 months; use 'annualised_tonnes_if_flat' only as a rough guide (assumes flat seasonality).",
        "No revenue in the company data, so emissions intensity (tCO2e per $1M) cannot be computed to compare with Docusign's 45.",
        "Only two peers, both software/e-commerce companies; the company's Scope 1 profile (coal, cement process emissions) is industrial, so size gaps are not like-for-like performance gaps.",
        "Shopify figures were read from a chart on p.19 (labels checked against the page image), not from a table.",
    ]
    return dict(company=co, peer_facts=items, peers=[dict(name=p["name"], report=p["report"], period=p["period"], boundary=p["boundary"]) for p in PEERS],
                items=items, caveats=caveats)
