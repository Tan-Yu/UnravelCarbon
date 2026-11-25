"""Checks the tools against numbers verified independently in NOTES.md ('Data observations so far')."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import emissions_tools as t


def test_totals():
    x = t.totals()
    assert x["scope1"]["tonnes"] == 1692.47 and x["scope2"]["tonnes"] == 2505.04
    assert abs(x["scope3"]["tonnes"] - 374485.5) < 0.1
    assert x["scope1"]["months"] == 3 and x["scope3"]["months"] == 12 and x["caveat"]


def test_recompute_all_rows_match():
    for s, n in ((1, 18), (2, 18), (3, 1000)):
        r = t.recompute(s); assert r["matched"] == n and not r["mismatches"]
    assert t.recompute(2)["mixed_scales"]          # kg and tonne factors mixed with no unit column


def test_scope2_steam_dominates():
    items = {i["name"]: i for i in t.scope2_breakdown("Energy_Type")["items"]}
    assert round(items["Steam"]["share_pct"], 1) == 84.5
    top = t.scope2_breakdown(["Facility", "Energy_Type"])["items"][0]
    assert top["name"] == "Manufacturing Plant / Steam" and round(top["share_pct"], 1) == 75.3


def test_scope3_top_category():
    top = t.scope3_top("Category", 1)["items"][0]
    assert top["name"] == "Category 3" and round(top["tonnes"]) == 31794


def test_scope1_shares():
    s = {i["name"]: i["share_pct"] for i in t.scope1_breakdown("Fuel_Type")["items"]}
    assert round(s["Coal"]) == 53 and round(s["Cement Production"]) == 41


def test_quality_findings_present_and_ordered():
    rep = t.quality_report()
    ids = {f["id"] for f in rep["findings"]}
    assert {"s2.steam_factor", "s2.dual_reporting", "s3.category_mapping", "x.period_mismatch"} <= ids
    statuses = [f["status"] for f in rep["findings"]]
    assert statuses == sorted(statuses, key=["gap", "verify", "unknown", "info", "pass"].index)
    assert next(f for f in rep["findings"] if f["id"] == "s2.dual_reporting")["status"] == "unknown"


def test_read_only_files_untouched():
    import hashlib
    before = {f: hashlib.md5(open(t.DATA_DIR / f, "rb").read()).hexdigest() for f in t.FILES.values()}
    t.quality_report(); t.supplier_priorities()
    assert before == {f: hashlib.md5(open(t.DATA_DIR / f, "rb").read()).hexdigest() for f in t.FILES.values()}
