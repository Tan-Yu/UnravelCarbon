"""Emissions analysis agent: Gemini with function calling over
(a) deterministic CSV tools (emissions_tools) and (b) GHG Protocol retrieval (rag).
Usage: python3 agent.py "question"   |   python3 agent.py --demo
"""
import json, re, sys, time
from pathlib import Path
from google import genai
from google.genai import types
import emissions_tools as et
from rag import GHGIndex

ROOT = Path(__file__).resolve().parent
MODEL = "gemini-2.5-flash"
PROMPT_VERSION = "agent-v1"
MAX_STEPS = 6

SYSTEM = """You are an emissions analysis assistant for sustainability professionals. You have two kinds of tools:
- CSV tools: deterministic calculations over the company's Scope 1/2/3 data. Every number you state about the data MUST come from a CSV tool result. Never compute or estimate figures yourself.
- search_ghg_protocol: retrieves excerpts of the GHG Protocol Corporate Standard (2004 edition), each marked [p.N].
Rules:
- Never state a Protocol rule from memory: call search_ghg_protocol first, even for questions that seem to have no answer. A citation is only valid for a page that appeared in a search result.
- Data questions: call the CSV tools. Methodology / rules questions: call search_ghg_protocol. Questions that need both (e.g. "is our steam reporting compliant?", quality assessment): call both; use each finding's rule_query to retrieve the rule.
- Cite every Protocol claim like [p.27]. Never invent pages, quotes or numbers. Cite data as (source: tool name).
- Label each assessment point "Protocol requirement" (the excerpt says "shall"; cite the page) or "Best practice" (a recommendation, "should", or your judgment). Suggest, do not rewrite or change the data.
- If the excerpts do not answer, say "Cannot verify from the provided documents." and what is missing. The 2004 edition has NO Scope 2 Guidance (2015) and NO Scope 3 Standard (2011): say so when relevant instead of guessing.
- Peer-company reports are not available yet: say so if asked to compare with peers.
- Be concise (under 200 words unless a report is requested)."""


def cited_pages(ans):
    out = set()
    for m in re.finditer(r"\[(?:pp?\.?)\s*([\d,\s\-–]+)\]", ans):
        out |= {int(x) for x in re.findall(r"\d+", m.group(1))}
    return out


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
    _decl("search_ghg_protocol", "Search the GHG Protocol Corporate Standard (2004). Returns page-marked excerpts. "
          "Use a self-contained query, e.g. 'Scope 2 definition purchased electricity heat steam'.",
          {"query": dict(type=S)}, ["query"]),
]
PRICE_IN, PRICE_OUT = 0.30, 2.50   # USD per 1M tokens, gemini-2.5-flash paid-tier list price (free tier costs 0)


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

    def _run_tool(self, name, args):
        args = {k: (int(v) if k in ("scope", "n") else v) for k, v in dict(args).items()}
        if name == "search_ghg_protocol":
            r = self.index.search(args["query"], expand=self.expand)
            return {"returned_pages": r["returned_pages"], "excerpts": r["text"]}, r
        return json.loads(json.dumps(et.TOOLS[name](**args), default=str)), None

    def ask(self, question, history=None):
        contents = list(history or []) + [types.Content(role="user", parts=[types.Part(text=question)])]
        cfg = types.GenerateContentConfig(system_instruction=SYSTEM, temperature=0, max_output_tokens=3000,
                                          tools=[types.Tool(function_declarations=DECLS)],
                                          automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                                          thinking_config=types.ThinkingConfig(thinking_budget=0))
        trace, tin, tout, t0 = [], 0, 0, time.time(); retrieved, guarded = set(), False
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
                if bad and not guarded:
                    guarded = True   # citation guard: one retry when the answer cites pages never retrieved
                    contents.append(r.candidates[0].content)
                    contents.append(types.Content(role="user", parts=[types.Part(text=(
                        f"Your answer cites pages {bad} that no search returned. Call search_ghg_protocol (use each finding's "
                        "rule_query) to find the rule, then answer again citing only retrieved pages; drop any rule you cannot cite."))]))
                    trace.append(dict(tool="citation_guard", args={"uncited_pages": bad}, pages=None)); continue
                return dict(uncited_pages=bad, answer=r.text or "", trace=trace, tokens_in=tin, tokens_out=tout, steps=step + 1,
                            latency=round(time.time() - t0, 1), cost_usd=round(tin * PRICE_IN / 1e6 + tout * PRICE_OUT / 1e6, 5),
                            history=contents + [r.candidates[0].content])
            contents.append(r.candidates[0].content)
            parts = []
            for c in calls:
                try: out, raw = self._run_tool(c.name, c.args or {})
                except Exception as e: out, raw = {"error": str(e)}, None
                if raw: retrieved |= set(raw["returned_pages"])
                trace.append(dict(tool=c.name, args=dict(c.args or {}), pages=(raw or {}).get("returned_pages")))
                parts.append(types.Part.from_function_response(name=c.name, response={"result": out}))
            contents.append(types.Content(role="user", parts=parts))
        return dict(answer="(stopped: too many tool steps)", trace=trace, tokens_in=tin, tokens_out=tout,
                    steps=MAX_STEPS, latency=round(time.time() - t0, 1), cost_usd=0, history=contents)


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
