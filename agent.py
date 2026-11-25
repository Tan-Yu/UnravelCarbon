"""Emissions analysis agent: Gemini with function calling over
(a) deterministic CSV tools (emissions_tools) and (b) GHG Protocol retrieval (rag).
Usage: python3 agent.py "question"   |   python3 agent.py --demo
"""
import json, re, sys, time
from pathlib import Path
from google import genai
from google.genai import types
import emissions_tools as et
import peers
from rag import GHGIndex

ROOT = Path(__file__).resolve().parent
MODEL = "gemini-2.5-flash"
PROMPT_VERSION = "agent-v3"
MAX_STEPS = 6

SYSTEM = """You are an emissions analysis assistant for sustainability professionals. You have two kinds of tools:
- CSV tools: deterministic calculations over the company's Scope 1/2/3 data. Every number you state about the data MUST come from a CSV tool result. Never compute or estimate figures yourself.
- search_ghg_protocol: retrieves excerpts of the GHG Protocol Corporate Standard (2004 edition), each marked [p.N].
Rules:
- Never state a Protocol rule from memory: call search_ghg_protocol first, even for questions that seem to have no answer. A citation is only valid for a page that appeared in a search result.
- Data questions: call the CSV tools. Methodology / rules questions: call search_ghg_protocol. Questions that need both (e.g. "is our steam reporting compliant?", quality assessment): call both; use each finding's rule_query to retrieve the rule.
- Cite every Protocol claim like [p.27]. Cite every number about the company's data with the source_id from the tool result, like [D1], placed right after the claim. Never invent pages, quotes, numbers or source ids. Do not write '(source: ...)'.
- Label each assessment point "Protocol requirement" (the excerpt says "shall"; cite the page) or "Best practice" (a recommendation, "should", or your judgment). Suggest, do not rewrite or change the data.
- If the excerpts do not answer, say "Cannot verify from the provided documents." and what is missing. The 2004 edition has NO Scope 2 Guidance (2015) and NO Scope 3 Standard (2011): say so when relevant instead of guessing.
- For peer comparison call compare_with_peers. State the boundary and period differences from its caveats before drawing any conclusion; never rank the company as better or worse without them. Peers: Docusign FY25 and Shopify 2024 only.
- Split a compound question into its sub-questions and search for each one separately (a single search rarely covers both a classification and a calculation method).
- For validity or compliance questions, open with a one-line verdict (valid / not valid / cannot be determined) and the main reason, then the supporting points.
- Use "shall", "required" or "mandatory" only when the cited page says so; if it only recommends, say "recommended".
- CSV tool results may include data_caveats (data-quality findings for the data you are reporting on). When a caveat affects a claim you make, state it briefly next to that claim; do not present affected groupings as reliable.
- Be concise (under 200 words unless a report is requested)."""


def cited_pages(ans):
    out = set()
    for m in re.finditer(r"\[(?:pp?\.?)\s*([\d,\s\-–]+)\]", ans):
        out |= {int(x) for x in re.findall(r"\d+", m.group(1))}
    return out


FILE_OF = {"scope1_breakdown": "scope1.csv", "scope2_breakdown": "scope2.csv", "scope3_top": "scope3.csv",
           "scope3_category_detail": "scope3.csv", "supplier_priorities": "scope3.csv"}


def describe(name, a):
    """Human-readable label for a data source chip."""
    f = FILE_OF.get(name, "")
    return {
        "totals": "Total emissions per scope (scope1/2/3.csv)",
        "scope1_breakdown": f"{f}: Scope 1 emissions grouped by {a.get('by', 'Fuel_Type')}",
        "scope2_breakdown": f"{f}: Scope 2 emissions grouped by {a.get('by', 'Energy_Type')}",
        "scope3_top": f"{f}: top {a.get('n', 5)} Scope 3 groups by {a.get('by', 'Category')}",
        "scope3_category_detail": f"{f}: what drives Scope 3 {a.get('category', '')}",
        "supplier_priorities": f"{f}: suppliers ranked by emissions and data quality",
        "recompute": f"scope{a.get('scope')}.csv: CO2e recalculated as quantity x factor for every row",
        "compare_with_peers": "Peer reports: Docusign FY25 Impact Report (pp.49-50) and Shopify 2024 Climate Report (pp.18-19)",
        "quality_report": "Data-quality checks" + (f" on scope{a['scope']}.csv" if a.get("scope") else " on all scopes"),
    }.get(name, name)


_TOKEN = re.compile(r"\[\s*((?:D\d+|pp?\.?\s*\d+)(?:\s*[,;]\s*(?:D\d+|pp?\.?\s*\d+))*)\s*\]")


def number_sources(answer, sources):
    """Replace [D3] / [p.27] markers with [1], [2]... and return the cited sources in order."""
    order, out = [], []
    def key(t):
        t = t.strip()
        return t if t.startswith("D") else "p." + re.sub(r"\D", "", t)
    def sub(m):
        nums = []
        for t in re.split(r"[,;]", m.group(1)):
            k = key(t)
            if k not in sources: continue
            if k not in order: order.append(k)
            nums.append(order.index(k) + 1)
        return "".join(f"[{n}]" for n in sorted(set(nums)))
    out = _TOKEN.sub(sub, answer)
    return out, [dict(n=i + 1, id=k, **sources[k]) for i, k in enumerate(order)]


def _decl(name, desc, props=None, required=()):
    return types.FunctionDeclaration(name=name, description=desc, parameters=types.Schema(
        type="OBJECT", properties={k: types.Schema(**v) for k, v in (props or {}).items()}, required=list(required)))

S, I = "STRING", "INTEGER"
DECLS = [
    _decl("totals", "Total CO2e (tonnes) per scope, grand total, each scope's share, and reporting periods."),
    _decl("scope1_breakdown", "Scope 1 emissions grouped by Facility, Activity_Type or Fuel_Type.",
          {"by": dict(type=S, enum=["Facility", "Activity_Type", "Fuel_Type"])}),
    _decl("scope2_breakdown", "Scope 2 emissions grouped by Facility, Energy_Type (electricity/steam/...) or Grid_Region.",
          {"by": dict(type=S, enum=["Facility", "Energy_Type", "Grid_Region"])}),
    _decl("scope3_top", "Top-n Scope 3 groups by emissions.",
          {"by": dict(type=S, enum=["Category", "Activity_Description", "Supplier", "Data_Quality"]), "n": dict(type=I)}),
    _decl("scope3_category_detail", "Activities and suppliers driving one Scope 3 category, e.g. 'Category 3'.",
          {"category": dict(type=S), "n": dict(type=I)}, ["category"]),
    _decl("supplier_priorities", "Rank suppliers by emissions with data reliability (share of primary data).",
          {"n": dict(type=I)}),
    _decl("recompute", "Recompute CO2e = quantity x factor for every row of one scope and list mismatches.",
          {"scope": dict(type=I, enum=["1", "2", "3"])}, ["scope"]),
    _decl("quality_report", "Run all data-quality checks; returns findings with status, severity, evidence and a rule_query "
          "to look up in the Protocol. Omit scope for all scopes plus cross-scope checks.",
          {"scope": dict(type=I, enum=["1", "2", "3"])}),
    _decl("compare_with_peers", "Company totals next to two peer companies' reported emissions (Docusign FY25, Shopify 2024), with page numbers and comparability caveats."),
    _decl("search_ghg_protocol", "Search the GHG Protocol Corporate Standard (2004). Returns page-marked excerpts. "
          "Use a self-contained query, e.g. 'Scope 2 definition purchased electricity heat steam'.",
          {"query": dict(type=S)}, ["query"]),
]
TOOLS = {**et.TOOLS, "compare_with_peers": peers.compare_with_peers}
PRICE_IN, PRICE_OUT = 0.30, 2.50   # USD per 1M tokens, gemini-2.5-flash paid-tier list price (free tier costs 0)


OBLIGATION = re.compile(r"\b(shall|must|required|requires|requirement|mandatory)\b", re.I)
SCOPES_OF = {"scope1_breakdown": [1], "scope2_breakdown": [2], "scope3_top": [3], "scope3_category_detail": [3],
             "supplier_priorities": [3], "totals": None}
VERIFY = """For each numbered claim, decide if the cited page text states or clearly supports it (including the strength: a claim that something
is required/shall is unsupported if the page only says should/recommended or says nothing). Return ONLY JSON: {{"unsupported": [claim numbers]}}.
{body}"""


def _key():
    for l in open(ROOT / ".env"):
        if "=" in l and not l.strip().startswith("#") and l.split("=")[0].strip().upper().startswith("GEMINI"):
            return l.split("=", 1)[1].strip().strip("\"'")
    sys.exit("no GEMINI key in .env")


class Agent:
    def __init__(self, expand=1):
        self.client = genai.Client(api_key=_key())
        self.index = GHGIndex()
        self.expand = expand       # 0 = page, 1 = page+-1
        self.dcount = 0            # data source ids stay unique across turns (history keeps old ids)

    def set_project(self, name):
        et.set_project(name); self.project = name

    def _run_tool(self, name, args, sources):
        args = {k: (int(v) if k in ("scope", "n") else v) for k, v in dict(args).items()}
        if name == "search_ghg_protocol":
            r = self.index.search(args["query"], expand=self.expand)
            for p in r["returned_pages"]:
                sources[f"p.{p}"] = dict(kind="page", label=f"GHG Protocol Corporate Standard (2004), PDF page {p}",
                                         detail=self.index.pages[p])
            return {"returned_pages": r["returned_pages"], "excerpts": r["text"]}, r
        res = json.loads(json.dumps(TOOLS[name](**args), default=str))
        self.dcount += 1; sid = f"D{self.dcount}"
        sources[sid] = dict(kind="data", label=describe(name, args), detail=res, tool=name, args=args)
        extra = {}
        if name in SCOPES_OF or name == "recompute":   # attach the data-quality findings that affect what was just reported
            scopes = [args["scope"]] if name == "recompute" else SCOPES_OF[name]
            fs = et.quality_report(scopes[0] if scopes else None)["findings"]
            extra["data_caveats"] = [dict(id=f["id"], severity=f["severity"], title=f["title"])
                                     for f in fs if f["status"] in ("gap", "verify", "unknown")]
        return {"source_id": sid, **res, **extra}, None

    def _verify(self, text, sources):
        """Claim check: obligation claims ('shall', 'required') are checked against the page they cite."""
        claims = []
        for sent in re.split(r"(?<=[.!?])\s+|\n+", text):
            pgs = [f"p.{n}" for n in cited_pages(sent) if f"p.{n}" in sources]
            if pgs and OBLIGATION.search(sent): claims.append((sent.strip(), pgs))
        claims = claims[:8]
        if not claims: return [], 0, 0
        body = "\n\n".join(f"Claim {i+1}: {c}\nCited page text:\n" + "\n".join(f"[{p}] {re.sub(chr(10)+'+', ' ', sources[p]['detail'])[:3500]}" for p in pg)
                            for i, (c, pg) in enumerate(claims))
        r = self.client.models.generate_content(model=MODEL, contents=VERIFY.format(body=body), config=types.GenerateContentConfig(
            temperature=0, response_mime_type="application/json", thinking_config=types.ThinkingConfig(thinking_budget=0)))
        try: bad = [claims[i - 1][0] for i in json.loads(r.text)["unsupported"] if 1 <= i <= len(claims)]
        except Exception: bad = []
        u = r.usage_metadata
        return bad, u.prompt_token_count or 0, u.candidates_token_count or 0

    def ask(self, question, history=None):
        contents = list(history or []) + [types.Content(role="user", parts=[types.Part(text=question)])]
        cfg = types.GenerateContentConfig(system_instruction=SYSTEM, temperature=0, max_output_tokens=3000,
                                          tools=[types.Tool(function_declarations=DECLS)],
                                          automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                                          thinking_config=types.ThinkingConfig(thinking_budget=0))
        trace, tin, tout, t0 = [], 0, 0, time.time(); retrieved, guarded, sources, revised, claim_check = set(), False, {}, False, None
        for step in range(MAX_STEPS):
            for a in range(5):
                try:
                    r = self.client.models.generate_content(model=MODEL, contents=contents, config=cfg); break
                except Exception as e:
                    print("  retry:", str(e)[:80], flush=True); time.sleep(20 * (a + 1))
            else:
                raise RuntimeError("LLM call failed")
            u = r.usage_metadata; tin += u.prompt_token_count or 0; tout += u.candidates_token_count or 0
            calls = r.function_calls or []
            if not calls:
                bad = sorted(cited_pages(r.text or "") - retrieved)
                ans, cited = number_sources(r.text or "", sources)
                if bad and not guarded:
                    guarded = True   # citation guard: one retry when the answer cites pages never retrieved
                    contents.append(r.candidates[0].content)
                    contents.append(types.Content(role="user", parts=[types.Part(text=(
                        f"Your answer cites pages {bad} that no search returned. Call search_ghg_protocol (use each finding's "
                        "rule_query) to find the rule, then answer again citing only retrieved pages; drop any rule you cannot cite."))]))
                    trace.append(dict(tool="citation_guard", args={"uncited_pages": bad}, pages=None)); continue
                if not bad or guarded:
                    unsup, vi, vo = self._verify(r.text or "", sources); tin += vi; tout += vo
                    claim_check = dict(unsupported=unsup, revised=revised)
                    if unsup and not revised:
                        revised = True
                        contents.append(r.candidates[0].content)
                        contents.append(types.Content(role="user", parts=[types.Part(text=(
                            "These claims are not supported by the page text you cited: " + " | ".join(unsup) +
                            ". Rewrite the whole answer: remove or soften those claims (say 'recommended' when the page only recommends), keep the rest."))]))
                        trace.append(dict(tool="claim_check", args={"unsupported": unsup}, pages=None)); continue
                return dict(uncited_pages=bad, claim_check=claim_check, answer=ans, answer_raw=r.text or "", sources=cited, trace=trace, tokens_in=tin, tokens_out=tout, steps=step + 1,
                            latency=round(time.time() - t0, 1), cost_usd=round(tin * PRICE_IN / 1e6 + tout * PRICE_OUT / 1e6, 5),
                            history=contents + [r.candidates[0].content])
            contents.append(r.candidates[0].content)
            parts = []
            for c in calls:
                try: out, raw = self._run_tool(c.name, c.args or {}, sources)
                except Exception as e: out, raw = {"error": str(e)}, None
                if raw: retrieved |= set(raw["returned_pages"])
                trace.append(dict(tool=c.name, args=dict(c.args or {}), pages=(raw or {}).get("returned_pages")))
                parts.append(types.Part.from_function_response(name=c.name, response={"result": out}))
            contents.append(types.Content(role="user", parts=parts))
        return dict(answer="(stopped: too many tool steps)", trace=trace, tokens_in=tin, tokens_out=tout,
                    steps=MAX_STEPS, sources=[], uncited_pages=[], latency=round(time.time() - t0, 1), cost_usd=0, history=contents)


DEMO = [
    "Which Scope 3 category has the highest emissions?",
    "What share of Scope 2 comes from steam, and does the GHG Protocol count steam as Scope 2?",
    "Is Scope 3 reporting mandatory under the GHG Protocol?",
    "Run a data quality assessment of our emissions data and flag anything that conflicts with the Protocol.",
    "How do we compare with our peers?",
    "How many categories of Scope 3 are there in the 2004 standard?",
]

if __name__ == "__main__":
    ag = Agent()
    qs = DEMO if "--demo" in sys.argv else [" ".join(sys.argv[1:])]
    log = (ROOT / "build/cache/agent_demo.jsonl").open("a") if "--demo" in sys.argv else None
    for q in qs:
        r = ag.ask(q)
        print(f"\nQ: {q}\n{r['answer']}\n-- tools: {[(t['tool'], t['args']) for t in r['trace']]}"
              f"\n-- steps={r['steps']} in={r['tokens_in']} out={r['tokens_out']} {r['latency']}s ${r['cost_usd']}")
        if log:
            log.write(json.dumps({k: v for k, v in r.items() if k != "history"} | dict(question=q, model=MODEL, prompt=PROMPT_VERSION,
                                                                                    expand=ag.expand), ensure_ascii=False) + "\n"); log.flush()
            time.sleep(7)
