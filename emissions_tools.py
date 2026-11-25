"""Deterministic emissions tools (read-only). No arithmetic is left to the LLM.

Every public function returns a plain dict (JSON-serialisable) so it can be exposed as an LLM tool.
Findings use one schema:  {id, status, severity, title, evidence, rule_query, label_hint}
  status      pass | verify | gap | info | unknown
  rule_query  question to run against the GHG Protocol index to get the cited rule (RAG supplies rules;
              this module only measures the data)
  label_hint  'protocol' if a rule is expected in the PDF, 'best_practice' otherwise (never claim a
              Protocol requirement without a retrieved citation)
The module never edits the CSVs: it only suggests.
"""
from __future__ import annotations
import math
from pathlib import Path
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent
FILES = {1: "scope1.csv", 2: "scope2.csv", 3: "scope3.csv"}
ROUND_TOL = 0.0051          # reported values are rounded to 2 decimals (tonnes)
SCALES = [1e-6, 1e-3, 1.0, 1e3]
_cache: dict[int, pd.DataFrame] = {}


def load(scope: int) -> pd.DataFrame:
    if scope not in _cache:
        df = pd.read_csv(DATA_DIR / FILES[scope])
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        _cache[scope] = df
    return _cache[scope].copy()


def _qty_col(scope: int) -> str:
    return "Spend_Amount" if scope == 3 else "Consumption_Amount"


def _f(x, nd=2):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), nd)


def _finding(id, status, severity, title, evidence, rule_query=None, label_hint="best_practice"):
    return dict(id=id, status=status, severity=severity, title=title, evidence=evidence,
                rule_query=rule_query, label_hint=label_hint)


# --------------------------------------------------------------------------- recompute
def recompute(scope: int) -> dict:
    """Recompute CO2e = quantity x factor x scale for every row and compare with the reported value.
    There is no unit column for the factor, so the scale is inferred per row (ratio reported/raw) and
    snapped to a known scale (1e-6, 1e-3, 1, 1e3). Rows whose ratio matches no scale are flagged."""
    df = load(scope)
    raw = df[_qty_col(scope)] * df["Emission_Factor"]
    rows, bad = [], []
    for i, (r, rep) in enumerate(zip(raw, df["CO2e_Tonnes"])):
        ratio = rep / r if r else float("nan")
        scale = min(SCALES, key=lambda s: abs(math.log10(ratio / s))) if ratio and ratio > 0 else None
        ok = scale is not None and abs(r * scale - rep) <= ROUND_TOL + 1e-9
        rows.append((i, scale, ok))
        if not ok:
            bad.append(dict(row=i + 2, reported=_f(rep), raw_product=_f(r, 4), ratio=_f(ratio, 6)))
    key = {1: ["Fuel_Type", "Consumption_Unit"], 2: ["Energy_Type", "Consumption_Unit"], 3: ["Spend_Currency"]}[scope]
    df = df.assign(_scale=[s for _, s, _ in rows], _ok=[o for _, _, o in rows])
    groups = (df.groupby(key).agg(rows=("_ok", "size"), matched=("_ok", "sum"), scales=("_scale", lambda s: sorted(set(s.dropna()))))
              .reset_index().to_dict("records"))
    scales_used = sorted({s for _, s, _ in rows if s is not None})
    return dict(scope=scope, rows=len(df), matched=int(df["_ok"].sum()), mismatches=bad, groups=groups,
                scales_used=scales_used, mixed_scales=len(scales_used) > 1)


# --------------------------------------------------------------------------- totals and breakdowns
def totals() -> dict:
    out = {}
    for s in (1, 2, 3):
        df = load(s)
        out[f"scope{s}"] = dict(tonnes=_f(df["CO2e_Tonnes"].sum()), rows=len(df),
                                period=[str(df["Date"].min().date()), str(df["Date"].max().date())],
                                months=int(df["Date"].dt.to_period("M").nunique()))
    grand = sum(out[k]["tonnes"] for k in out)
    for k in out: out[k]["share_pct"] = _f(100 * out[k]["tonnes"] / grand, 2)
    out["total_tonnes"] = _f(grand)
    out["caveat"] = ("Scope 1 and 2 cover fewer months than Scope 3; shares are not like-for-like."
                     if len({out[k]["months"] for k in ('scope1', 'scope2', 'scope3')}) > 1 else None)
    return out


def _breakdown(df, by, n=None):
    g = df.groupby(by)["CO2e_Tonnes"].sum().sort_values(ascending=False)
    tot = g.sum(); g = g.head(n) if n else g
    return [dict(name=str(k) if not isinstance(k, tuple) else " / ".join(map(str, k)), tonnes=_f(v), share_pct=_f(100 * v / tot))
            for k, v in g.items()]


def scope1_breakdown(by: str = "Fuel_Type") -> dict:
    """by: Facility | Activity_Type | Fuel_Type"""
    return dict(by=by, items=_breakdown(load(1), by), total=_f(load(1)["CO2e_Tonnes"].sum()))


def scope2_breakdown(by: str = "Energy_Type") -> dict:
    """by: Facility | Energy_Type | Grid_Region | ['Facility','Energy_Type']"""
    df = load(2)
    return dict(by=by, items=_breakdown(df, by), total=_f(df["CO2e_Tonnes"].sum()))


def scope3_top(by: str = "Category", n: int = 5) -> dict:
    """by: Category | Activity_Description | Supplier | Data_Quality"""
    df = load(3)
    return dict(by=by, items=_breakdown(df, by, n), total=_f(df["CO2e_Tonnes"].sum()), n_groups=int(df[by].nunique()))


def scope3_category_detail(category: str, n: int = 5) -> dict:
    """Which activities and suppliers drive one category, e.g. 'Category 3'."""
    df = load(3); d = df[df["Category"].str.lower() == category.lower()]
    if d.empty: return dict(category=category, found=False, valid=sorted(df["Category"].unique(), key=lambda x: int(x.split()[-1])))
    return dict(category=category, found=True, tonnes=_f(d["CO2e_Tonnes"].sum()), rows=len(d),
                activities=_breakdown(d, "Activity_Description", n), suppliers=_breakdown(d, "Supplier", n),
                data_quality=_breakdown(d, "Data_Quality"))


def supplier_priorities(n: int = 5) -> dict:
    """Rank suppliers by emissions, with how reliable the underlying data is (share of 'Primary data')."""
    df = load(3); tot = df["CO2e_Tonnes"].sum(); rows = []
    for s, d in df.groupby("Supplier"):
        t = d["CO2e_Tonnes"].sum()
        rows.append(dict(supplier=s, tonnes=_f(t), share_pct=_f(100 * t / tot), rows=len(d),
                         primary_data_pct=_f(100 * (d["Data_Quality"] == "Primary data").mean(), 1),
                         top_activity=d.groupby("Activity_Description")["CO2e_Tonnes"].sum().idxmax()))
    rows.sort(key=lambda r: -r["tonnes"])
    top = rows[:n]
    spread = (rows[0]["tonnes"] - rows[-1]["tonnes"]) / rows[0]["tonnes"]
    return dict(items=top, n_suppliers=len(rows), spread_top_vs_bottom_pct=_f(100 * spread, 1),
                caveat="Suppliers are spread almost evenly, so ranking alone gives weak prioritisation; "
                       "combine with data quality and activity before engaging." if spread < 0.3 else None)


# --------------------------------------------------------------------------- quality checks
def _check_scope1():
    df = load(1); fs = []
    rc = recompute(1)
    fs.append(_finding("s1.arithmetic", "pass" if not rc["mismatches"] else "gap", "high",
                       f"{rc['matched']}/{rc['rows']} rows recompute within rounding", dict(mismatches=rc["mismatches"])))
    fs.append(_finding("s1.units", "verify", "medium", "Factor units are not stated (scales differ by fuel)",
                       dict(scales_used=rc["scales_used"], by_group=rc["groups"]),
                       "How should emission factors, units and conversions be documented and checked?", "protocol"))
    months = df["Date"].dt.to_period("M").nunique()
    fs.append(_finding("s1.period", "gap" if months < 12 else "pass", "high", f"Covers {months} months only",
                       dict(period=[str(df['Date'].min().date()), str(df['Date'].max().date())]),
                       "What must the reporting period cover in a public GHG report?", "protocol"))
    gas = df["Activity_Type"].value_counts().to_dict()
    fs.append(_finding("s1.gases", "gap", "medium", "CO2e only; the six gases are not reported separately",
                       dict(columns=list(df.columns), activity_types=gas),
                       "Which greenhouse gases must be reported separately?", "protocol"))
    top = _breakdown(df, ["Activity_Type", "Fuel_Type"], 2)
    fs.append(_finding("s1.concentration", "info", "medium", "Emissions are concentrated in two sources",
                       dict(top=top), None))
    return fs


def _check_scope2():
    df = load(2); fs = []
    rc = recompute(2)
    fs.append(_finding("s2.arithmetic", "pass" if not rc["mismatches"] else "gap", "high",
                       f"{rc['matched']}/{rc['rows']} rows recompute within rounding", dict(mismatches=rc["mismatches"])))
    fs.append(_finding("s2.units", "verify", "medium", "Factor units are not stated and two scales are mixed",
                       dict(scales_used=rc["scales_used"], by_group=rc["groups"], mixed_scales=rc["mixed_scales"]),
                       "How should emission factors, units and conversions be documented and checked?", "protocol"))
    steam = df[df["Energy_Type"].str.lower() == "steam"]
    sf = steam["Emission_Factor"].unique().tolist()
    fs.append(_finding("s2.steam_factor", "verify", "high",
                       "Steam is the largest Scope 2 source and its factor has no stated source",
                       dict(steam_tonnes=_f(steam["CO2e_Tonnes"].sum()), steam_share_pct=_f(100 * steam["CO2e_Tonnes"].sum() / df["CO2e_Tonnes"].sum(), 1),
                            distinct_factors=sf, regions=sorted(steam["Grid_Region"].unique()),
                            factor_same_across_facilities=len(sf) == 1),
                       "Which emission factors are acceptable for Scope 2, and are supplier-specific factors preferred?", "protocol"))
    elec = df[df["Energy_Type"].str.lower() == "electricity"]
    fs.append(_finding("s2.grid_factors", "pass", "low", "Electricity uses regional grid factors (a published-factor type)",
                       dict(regions=sorted(elec["Grid_Region"].unique()), factors=elec.groupby("Grid_Region")["Emission_Factor"].unique().apply(list).to_dict()),
                       "Which emission factors are acceptable for Scope 2?", "protocol"))
    months = df["Date"].dt.to_period("M").nunique()
    fs.append(_finding("s2.period", "gap" if months < 12 else "pass", "high", f"Covers {months} months only",
                       dict(period=[str(df['Date'].min().date()), str(df['Date'].max().date())]),
                       "What must the reporting period cover in a public GHG report?", "protocol"))
    full = elec["CO2e_Tonnes"].sum()
    applied = (elec["CO2e_Tonnes"] * (1 - elec["Renewable_Percentage"] / 100)).sum()
    fs.append(_finding("s2.renewable", "info", "medium", "Renewable % is listed but not applied to CO2e",
                       dict(electricity_tonnes=_f(full), illustrative_if_all_backed=_f(applied), difference_pct=_f(100 * (full - applied) / full, 1),
                            note="Illustrative only: assumes every renewable % is backed by qualifying contracts, which the data does not show."),
                       "How should renewable energy certificates and green power be reported?", "protocol"))
    fs.append(_finding("s2.dual_reporting", "unknown", "high", "Location-based vs market-based reporting cannot be assessed",
                       dict(columns_present=list(df.columns), market_based_figure_present=False),
                       "What is the market-based method for Scope 2?", "protocol"))
    return fs


def _check_scope3():
    df = load(3); fs = []
    rc = recompute(3)
    fs.append(_finding("s3.arithmetic", "pass" if not rc["mismatches"] else "gap", "high",
                       f"{rc['matched']}/{rc['rows']} rows recompute within rounding", dict(mismatches=rc["mismatches"][:5], n_mismatches=len(rc["mismatches"]))))
    fs.append(_finding("s3.currency", "info", "low", "Single currency (USD); spend-based factors imply kg CO2e per USD", dict(currency=df["Spend_Currency"].unique().tolist())))
    # category vs activity sanity: if categories carried meaning, each activity would concentrate in a few categories
    ct = pd.crosstab(df["Activity_Description"], df["Category"])
    share_top = (ct.max(axis=1) / ct.sum(axis=1)).mean()
    uniform = 1 / ct.shape[1]
    cats_per_activity = (ct > 0).sum(axis=1).mean()
    biz = df[df["Activity_Description"].str.contains("Business Travel")]
    fs.append(_finding("s3.category_mapping", "gap" if share_top < 2 * uniform else "pass", "high",
                       "Categories and activities do not line up",
                       dict(mean_share_of_top_category_per_activity=_f(share_top, 3), uniform_baseline=_f(uniform, 3),
                            mean_categories_per_activity=_f(cats_per_activity, 1), n_categories=int(ct.shape[1]),
                            business_travel_categories=biz["Category"].value_counts().to_dict(),
                            note="Business travel appears under many categories; in the GHG Protocol it is a Scope 3 transport-related activity."),
                       "Which scope does employee business travel belong to?", "protocol"))
    sup = pd.crosstab(df["Supplier"], df["Activity_Description"])
    acts_per_sup = float((sup > 0).sum(axis=1).mean())
    top_share = float((sup.max(axis=1) / sup.sum(axis=1)).mean())
    ex = sup.loc["Corporate Travel"].sort_values(ascending=False).head(3).to_dict() if "Corporate Travel" in sup.index else {}
    fs.append(_finding("s3.supplier_activity", "verify" if acts_per_sup >= 0.9 * sup.shape[1] else "pass", "medium",
                       "Every supplier supplies nearly every activity; supplier names do not match what they supply",
                       dict(mean_activities_per_supplier=_f(acts_per_sup, 1), n_activities=int(sup.shape[1]),
                            mean_share_of_top_activity_per_supplier=_f(top_share, 3), suppliers=sorted(sup.index),
                            example_corporate_travel_activities={k: int(v) for k, v in ex.items()})))
    dq = df["Data_Quality"].value_counts(normalize=True).mul(100).round(1).to_dict()
    prim_t = df[df["Data_Quality"] == "Primary data"]["CO2e_Tonnes"].sum() / df["CO2e_Tonnes"].sum() * 100
    fs.append(_finding("s3.data_quality", "verify", "medium", "Only a minority of rows use primary data",
                       dict(row_share_pct=dq, primary_share_of_tonnes_pct=_f(prim_t, 1)),
                       "What does the GHG Protocol say about the quality of Scope 3 data and estimates?", "protocol"))
    months = df["Date"].dt.to_period("M").nunique()
    fs.append(_finding("s3.period", "pass" if months >= 12 else "gap", "medium", f"Covers {months} months",
                       dict(period=[str(df['Date'].min().date()), str(df['Date'].max().date())])))
    return fs


def quality_report(scope: int | None = None) -> dict:
    """Run all checks. scope=None runs everything plus the cross-scope check."""
    fn = {1: _check_scope1, 2: _check_scope2, 3: _check_scope3}
    scopes = [scope] if scope else [1, 2, 3]
    findings = []
    for s in scopes: findings += [dict(f, scope=s) for f in fn[s]()]
    if scope is None:
        t = totals()
        if t["caveat"]:
            findings.append(dict(_finding("x.period_mismatch", "gap", "high", "Scopes cover different periods",
                                          {k: t[k]["period"] for k in ("scope1", "scope2", "scope3")},
                                          "What must the reporting period cover in a public GHG report?", "protocol"), scope=0))
    order = {"gap": 0, "verify": 1, "unknown": 2, "info": 3, "pass": 4}
    findings.sort(key=lambda f: (order[f["status"]], {"high": 0, "medium": 1, "low": 2}[f["severity"]]))
    return dict(findings=findings, counts=pd.Series([f["status"] for f in findings]).value_counts().to_dict())


# --------------------------------------------------------------------------- load-time summary for the sidebar
def load_status() -> dict:
    """One line per CSV for the UI sidebar: rows, flags (gap + verify), arithmetic ok."""
    out = {}
    for s in (1, 2, 3):
        rep = quality_report(s)
        out[f"scope{s}.csv"] = dict(rows=len(load(s)), flags=sum(1 for f in rep["findings"] if f["status"] in ("gap", "verify")),
                                    arithmetic_ok=next(f["status"] == "pass" for f in rep["findings"] if f["id"].endswith(".arithmetic")))
    return out


TOOLS = {f.__name__: f for f in (totals, recompute, scope1_breakdown, scope2_breakdown, scope3_top,
                                 scope3_category_detail, supplier_priorities, quality_report, load_status)}

if __name__ == "__main__":
    import json
    print(json.dumps(dict(totals=totals(), status=load_status()), indent=1))
