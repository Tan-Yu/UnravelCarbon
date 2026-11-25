"""Scored evaluation of the agent on the six brief questions.

Each question has a rubric of deterministic checks: facts that must appear, claims that must not, tools that must be
called, and pages that must be cited. Ground truth comes from the data tools and from Protocol pages checked by hand,
never from an LLM. Each question is run N times to measure run-to-run variance.

Usage: python3 eval_agent.py [--runs 3] [--only "Core 1"]
Output: results/eval/<timestamp>.json and a summary table on stdout.
"""
import json, re, sys, time
from pathlib import Path
import agent
from agent import Agent
from run_tests import QS

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results/eval"

# A check is (name, kind, arg). Kinds:
#   any    - answer matches at least one regex in arg (case-insensitive)
#   none   - answer matches none of the regexes in arg
#   tool   - tool arg was called
#   page   - at least one of the pages in arg was cited
#   first  - the first 200 characters match regex arg
R = {
    "Core 1": [
        ("says Scope 3", "any", [r"\*\*scope 3\*\*", r"classified as scope 3", r"is scope 3"]),
        ("owned vehicles are Scope 1", "any", [r"(owned|controlled)[^.]{0,80}scope 1", r"scope 1[^.]{0,80}(owned|controlled)"]),
        ("gives a calculation method", "any", [r"distance", r"emission factor", r"activity data"]),
        ("searched the Protocol", "tool", "search_ghg_protocol"),
        ("cites scope definition / travel page", "page", [27, 28, 29, 30, 31]),
    ],
    "Core 2": [
        ("opens with a verdict", "first", r"verdict|valid|not valid|cannot be (fully )?determined"),
        ("flags the 3-month period", "any", [r"3 months", r"three months", r"2024-03-15", r"quarter"]),
        ("mentions steam", "any", [r"steam"]),
        ("checked the data", "tool", "quality_report"),
        ("no invented requirement on period length", "none", [r"(protocol|standard) requires (a |an )?(12|twelve)[- ]month"]),
    ],
    "Core 3": [
        ("called the peer tool", "tool", "compare_with_peers"),
        ("names Docusign", "any", [r"docusign"]),
        ("names Shopify", "any", [r"shopify"]),
        ("states comparability caveat", "any", [r"not (directly )?comparable", r"like-for-like", r"different (reporting )?(period|boundar)", r"annuali[sz]"]),
        ("gives an insight", "any", [r"insight", r"suggest", r"recommend", r"opportunit"]),
    ],
    "Bonus 1": [
        ("names Category 3", "any", [r"category 3\b"]),
        ("gives its size", "any", [r"31,?794", r"8\.49?\s?%"]),
        ("lists activities", "tool", "scope3_category_detail"),
    ],
    "Bonus 2": [
        ("names the top supplier", "any", [r"officemax"]),
        ("notes the even spread", "any", [r"even", r"similar", r"close", r"spread"]),
        ("uses data quality", "any", [r"primary data", r"data quality", r"supplier-specific"]),
        ("called supplier tool", "tool", "supplier_priorities"),
    ],
    "Bonus 3": [
        ("states the total", "any", [r"378,?683", r"378\.7\s?k", r"378,?68\d"]),
        ("Scope 3 dominates", "any", [r"98\.8?9", r"99\s?%"]),
        ("flags period mismatch", "any", [r"3 months", r"three months", r"not like-for-like", r"different (numbers of )?months"]),
        ("called totals", "tool", "totals"),
    ],
}
UNIVERSAL = [
    ("no uncited pages", "uncited", None),
    ("no leaked ids", "none", [r"\[s\d\.", r"\[D\d+\]", r"\[p\.\d+\]"]),
]


def score(r, checks):
    a, tools = r["answer"], [t["tool"] for t in r["trace"]]
    pages = {int(s["id"].split(".")[1]) for s in r["sources"] if s["kind"] == "page"}
    out = []
    for name, kind, arg in checks + UNIVERSAL:
        ok = {"any": lambda: any(re.search(p, a, re.I) for p in arg),
              "none": lambda: not any(re.search(p, a, re.I) for p in arg),
              "tool": lambda: arg in tools,
              "page": lambda: bool(pages & set(arg)),
              "first": lambda: bool(re.search(arg, a[:200], re.I)),
              "uncited": lambda: not r.get("uncited_pages")}[kind]()
        out.append(dict(check=name, ok=ok))
    return out


def rescore(path):
    """Re-grade saved answers after a rubric fix, without calling the model. Text checks are recomputed;
    tool, page and citation checks keep their saved result (the trace is not stored)."""
    d = json.loads(Path(path).read_text())
    for row in d["rows"]:
        kinds = {n: (k, a) for n, k, a in R[row["tag"]] + UNIVERSAL}
        for c in row["checks"]:
            k, a = kinds[c["check"]]
            if k in ("any", "none", "first"):
                c["ok"] = score(dict(answer=row["answer"], trace=[], sources=[]), [(c["check"], k, a)])[0]["ok"]
        row["passed"] = sum(c["ok"] for c in row["checks"])
    d["rescored"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    Path(path).write_text(json.dumps(d, indent=1, default=str))
    return d["rows"]


def summary(rows):
    print(f"\n| Question | Mean score | Min | Max | Always failing |\n|---|---|---|---|---|")
    for tag in dict.fromkeys(x["tag"] for x in rows):
        xs = [x for x in rows if x["tag"] == tag]; s = [x["passed"] / x["total"] for x in xs]
        fails = [c["check"] for j, c in enumerate(xs[0]["checks"]) if all(not y["checks"][j]["ok"] for y in xs)]
        print(f"| {tag} | {sum(s)/len(s):.2f} | {min(s):.2f} | {max(s):.2f} | {', '.join(fails) or '-'} |")
    allp = sum(x["passed"] for x in rows) / sum(x["total"] for x in rows)
    print(f"\nOverall check pass rate: {allp:.3f} over {len(rows)} answers.")


def main():
    if "--rescore" in sys.argv:
        return summary(rescore(sys.argv[sys.argv.index("--rescore") + 1]))
    runs = int(sys.argv[sys.argv.index("--runs") + 1]) if "--runs" in sys.argv else 3
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for tag, q in QS:
        if only and tag != only: continue
        for i in range(runs):
            ag = Agent()   # fresh agent: no shared history between runs
            t = time.time(); r = ag.ask(q)
            sc = score(r, R[tag])
            rows.append(dict(tag=tag, run=i + 1, passed=sum(c["ok"] for c in sc), total=len(sc), checks=sc,
                             answer=r["answer"], tools=[x["tool"] for x in r["trace"]], tokens_in=r["tokens_in"],
                             tokens_out=r["tokens_out"], cost_usd=r["cost_usd"], latency=round(time.time() - t, 1)))
            print(f"{tag} run {i+1}: {rows[-1]['passed']}/{rows[-1]['total']}  fails: "
                  f"{[c['check'] for c in sc if not c['ok']]}", flush=True)
            time.sleep(5)
    f = OUT / f"{time.strftime('%Y%m%d-%H%M%S')}_{agent.MODEL}_{agent.PROMPT_VERSION}.json"
    f.write_text(json.dumps(dict(model=agent.MODEL, prompt=agent.PROMPT_VERSION, runs=runs, rows=rows), indent=1, default=str))
    summary(rows); print(f"Saved {f.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
