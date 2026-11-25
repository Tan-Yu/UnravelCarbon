"""Build and VERIFY build/eval_queries.jsonl for the GHG Protocol (2004) PDF.

Each query has:
  gold_pages     PDF pages (1-based) that directly contain the answer
  also_relevant  pages that are related/partial, not penalised when retrieved
  evidence       {page: exact phrase} - checked against the page text by this script
Run:  python3 -I build/make_eval.py     (fails loudly if any quote is missing)
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = {x["page"]: x["text"] for x in json.load(open(ROOT / "build/ghg-protocol-revised.plain.json"))}


def norm(s):
    s = s.lower().replace("’", "'").replace("“", '"').replace("”", '"').replace("­", "")
    return re.sub(r"\s+", " ", s)


NP = {n: norm(t) for n, t in PAGES.items()}

Q = []
def q(query, type_, gold, evidence, key_points, also=(), scan=None):
    Q.append(dict(query=query, type=type_, gold_pages=sorted(gold), also_relevant=sorted(also),
                  evidence={str(k): v for k, v in evidence.items()}, key_points=key_points, scan=scan))

# ---------------- scopes and boundaries ----------------
q("How does the GHG Protocol define Scope 1 (direct) emissions?", "rule", [27, 29, 99],
  {99: "direct ghg emissions emissions from sources that are owned or controlled by the reporting company",
   27: "direct ghg emissions occur from sources that are owned or controlled by the company",
   29: "companies report ghg emissions from sources they own or control as scope 1"},
  ["emissions from sources owned or controlled by the company"], scan="owned or controlled")
q("How are Scope 2 emissions defined?", "rule", [27, 29, 88, 103],
  {88: "emissions associated with the generation of purchased electricity that is consumed by the reporting company are reported in scope 2",
   103: "scope 2 inventory a reporting organization's emissions associated with the generation of electricity, heating/ cooling, or steam purchased for own consumption",
   27: "scope 2 accounts for ghg emissions from the generation of purchased electricity",
   29: "companies report the emissions from the generation of purchased electricity that is consumed in its owned or controlled equipment or operations as scope 2"},
  ["generation of purchased electricity", "consumed in owned or controlled equipment or operations"],
  scan="generation of purchased electricity")
q("Does Scope 2 include purchased heat and steam?", "rule", [43, 103],
  {43: "identify indirect emission sources from the consumption of purchased electricity, heat, or steam",
   103: "scope 2 inventory a reporting organization's emissions associated with the generation of electricity, heating/ cooling, or steam purchased for own consumption"},
  ["Scope 2 definition in ch.4 (pp.27,29) names electricity only",
   "ch.6 (p.43) and glossary (p.103) extend indirect/Scope 2 sources to purchased heat and steam"],
  also=[17, 27, 29, 40], scan="purchased electricity, heat, or steam")
q("What is Scope 3 and is it mandatory to report?", "rule", [27, 31],
  {27: "scope 3 is an optional reporting category",
   31: "scope 3 is optional"},
  ["optional", "all other indirect emissions not in scope 2"], also=[103])
q("Which scopes must a company report at a minimum?", "rule", [27, 65],
  {27: "companies shall separately account for and report on scopes 1 and 2 at a minimum",
   65: "requires reporting a minimum of scope 1 and scope 2 emissions"},
  ["scope 1 and scope 2 reported separately"])
q("Which scope does employee business travel belong to?", "rule", [31, 34, 94, 95],
  {31: "employee business travel",
   34: "scope 3 indirect emissions associated with business air travel",
   94: "employee business travel",
   95: "employee business travel"},
  ["Scope 3 (transport-related activities)", "indirect, in vehicles not owned or controlled by the company",
   "NOTE: the 2004 PDF has no numbered Scope 3 categories ('category 6' is from the later Scope 3 Standard)"],
  also=[28, 33, 45])
q("How should direct CO2 emissions from burning biomass be treated?", "rule", [27, 65],
  {27: "direct co2 emissions from the combustion of biomass shall not be included in scope 1 but reported separately",
   65: "emissions data for direct co2 emissions from biologically sequestered carbon"},
  ["not in Scope 1", "reported separately from the scopes"])
q("Are CFCs and NOx included in Scope 1?", "rule", [27, 28, 65],
  {27: "shall not be included in scope 1 but may be reported separately",
   28: "may be reported separately from the scopes in a ghg public report",
   65: "emissions from ghgs not covered by the kyoto protocol"},
  ["not covered by the Kyoto Protocol", "excluded from Scope 1", "may be reported separately"])
q("Who reports the emissions from transmission and distribution (T&D) losses?", "rule", [29, 30, 88, 89],
  {88: "t&d losses are not reported under scope 2, as they would already be accounted for under scope 1",
   29: "reported in scope 2 by the company that owns or controls the t&d operation",
   30: "end consumers may, however, report their indirect emissions associated with t&d losses in scope 3",
   89: "companies that purchase electricity and transport it in their own t&d systems would report the portion of electricity consumed in t&d under scope 2"},
  ["utility that owns/controls the T&D system: Scope 2", "end consumers: not Scope 2, optionally Scope 3"])
q("How should electricity bought for resale to end users be reported?", "rule", [30, 31, 88],
  {88: "emissions from the generation of purchased electricity for resale to end-users",
   30: "generation of electricity that is purchased and then resold to end users",
   31: "purchase of electricity that is sold to an end user (reported by utility company)"},
  ["Scope 3, category 'generation of electricity that is purchased and then resold to end users'", "reported by the utility company"],
  also=[7])
q("Are upstream emissions from fuel extraction for the electricity I buy part of Scope 2?", "rule", [30, 31, 89],
  {30: "indirect emissions from activities upstream of a company's electricity provider (e.g., exploration, drilling, flaring, transportation) are reported under scope 3",
   31: "extraction, production, and transportation of fuels consumed in the generation of electricity",
   89: "emissions associated with the extraction and production of fuels consumed in the generation of purchased electricity may be reported in scope 3"},
  ["no: upstream fuel emissions are Scope 3"])
q("How are emissions from leased assets accounted for?", "rule", [33, 34],
  {33: "the selected consolidation approach (equity share or one of the control approaches) is also applied to account for and categorize direct and indirect ghg emissions from contractual arrangements such as leased assets",
   34: "the lessee only accounts for emissions from leased assets that it operates"},
  ["follows the chosen consolidation approach", "finance vs operating leases"])

# ---------------- organizational boundary ----------------
q("What approaches can be used to consolidate GHG emissions at the organizational level?", "rule", [19],
  {19: "two distinct approaches can be used to consolidate ghg emissions: the equity share and the control approaches"},
  ["equity share", "control (financial or operational)"])
q("How do financial control and operational control differ?", "rule", [19, 20],
  {19: "the company has financial control over the operation if the former has the ability to direct the financial and operating policies of the latter",
   20: "a company has operational control over an operation if the former or one of its subsidiaries"},
  ["financial: ability to direct financial and operating policies for economic benefit", "operational: full authority to introduce and implement operating policies"])
q("How does the equity share approach account for emissions?", "rule", [19],
  {19: "under the equity share approach, a company accounts for ghg emissions from operations according to its share of equity in the operation"},
  ["proportional to equity share", "economic substance overrides legal ownership"])
q("Must the same consolidation approach be used across all levels of the organization?", "rule", [20],
  {20: "once a corporate consolidation policy has been selected, it shall be applied to all levels of the organization"},
  ["yes, one policy at all levels"])

# ---------------- base year ----------------
q("What must a company's base year emissions recalculation policy include?", "rule", [37],
  {37: "companies shall develop a base year emissions recalculation policy, and clearly articulate the basis and context for any recalculations"},
  ["a policy is required", "state any significance threshold applied"])
q("Which events trigger a recalculation of base year emissions?", "rule", [37],
  {37: "the following cases shall trigger recalculation of base year emissions"},
  ["structural changes (mergers, acquisitions, divestments, outsourcing/insourcing)",
   "changes in methodology or accuracy of factors or data", "discovery of significant errors"])
q("Is base year emissions recalculated for organic growth?", "rule", [41],
  {41: "base year emissions and any historic data are not recalculated for organic growth or decline"},
  ["no"])
q("Is the base year recalculated when a company acquires a facility that did not exist in the base year?", "rule", [40, 41],
  {40: "base year emissions are not recalculated if the company makes an acquisition of (or insources) operations that did not exist in its base year",
   41: "the base year emissions of company teta do not change because the acquired facility c did not exist in year one"},
  ["no recalculation of base year"])
q("Does outsourcing electricity production trigger a base year recalculation?", "rule", [40],
  {40: "outsourcing production of electricity, heat, or steam does not trigger base year emissions recalculation"},
  ["no, because Scope 2 reporting is required"])
q("How should a company choose its base year?", "rule", [37, 38],
  {37: "companies shall choose and report a base year for which verifiable emissions data are available",
   38: "companies should choose as a base year the earliest relevant point in time for which they have reliable data"},
  ["verifiable data", "state reasons for the chosen year", "earliest year with reliable data"])

# ---------------- Scope 2 calculation ----------------
q("How should Scope 2 emissions be calculated and which emission factors are acceptable?", "rule", [44, 89],
  {44: "supplier-specific, local grid, or other published emission factors",
   89: "recommends that companies obtain source/supplier specific emission factors for the electricity purchased"},
  ["metered electricity consumption x factor", "supplier-specific preferred", "otherwise regional/grid or other published factors"])
q("Which emission factor does the GHG Protocol require for Scope 2: generation-based (EFG) or consumption-based (EFC)?", "rule", [89],
  {89: "requires the use of efg to calculate scope 2 emissions"},
  ["EFG (emission factor at generation)"])
q("Are the GHG Protocol calculation tools mandatory?", "rule", [44],
  {44: "the tools, however, are optional"},
  ["optional; own methods allowed if at least as accurate or consistent"])

# ---------------- offsets, RECs, trades ----------------
q("What are renewable energy certificates (RECs)?", "keyword", [63],
  {63: "recs, which represent the environmental benefits of renewable energy unbundled from the actual flow of electrons"},
  ["unbundled environmental benefits of renewable energy", "can be sold bundled or separately"], scan="recs")
q("Should GHG trades and offsets be reported separately from inventory emissions?", "rule", [62, 65, 84],
  {62: "report their physical inventory emissions for their chosen inventory boundaries separately and independently of any ghg trades",
   65: "total scope 1 and 2 emissions independent of any ghg trades",
   84: "companies should always report their own internal emissions in separate accounts from offsets"},
  ["yes, report inventory emissions independently", "trades under optional information"])
q("How should double counting of offsets be avoided?", "rule", [62, 84],
  {62: "to avoid double counting, the reductions giving rise to the offset must occur at sources or sinks not included in the target or cap",
   84: "this can occur when a ghg offset is counted towards the target by both the selling and purchasing organizations"},
  ["registries with serial numbers or contracts", "reductions outside the target boundary"])

# ---------------- reporting ----------------
q("What information must a public GHG emissions report include?", "rule", [65],
  {65: "a public ghg emissions report that is in accordance with the ghg protocol corporate standard shall include the following information"},
  ["organizational and operational boundaries", "reporting period", "emissions per scope", "all six gases", "base year", "methodologies", "exclusions"])
q("Which greenhouse gases must be reported separately?", "rule", [65],
  {65: "emissions data for all six ghgs separately (co2, ch4, n2o, hfcs, pfcs, sf6) in metric tonnes and in tonnes of co2 equivalent"},
  ["CO2, CH4, N2O, HFCs, PFCs, SF6", "metric tonnes and tonnes CO2e"], also=[28])
q("What optional information should a public GHG report include?", "rule", [65, 66],
  {65: "a public ghg emissions report should include, when applicable, the following additional information",
   66: "a list of facilities included in the inventory"},
  ["scope 3 data where reliable", "emissions by facility/country/source type", "inventory quality and uncertainty", "offsets information"])

# ---------------- principles, quality, uncertainty, verification ----------------
q("What are the five principles of GHG accounting and reporting?", "rule", [9],
  {9: "ghg accounting and reporting shall be based on the following principles"},
  ["relevance", "completeness", "consistency", "transparency", "accuracy"], also=[10])
q("Can a company use a materiality threshold to leave out small emission sources?", "rule", [10],
  {10: "the practical implementation of such a threshold is not compatible with the completeness principle"},
  ["no: not compatible with completeness", "exclusions must be disclosed and justified"])
q("What types of estimation uncertainty exist in a GHG inventory?", "rule", [57],
  {57: "estimation uncertainty can be further classified into two types: model uncertainty and parameter uncertainty"},
  ["model uncertainty", "parameter uncertainty"])
q("Can uncertainty estimates be used to compare inventory quality between companies?", "rule", [58],
  {58: "nor can they be used to compare the quality of emission estimates between source categories or companies"},
  ["no, with limited exceptions (identical methods, same facility over time)"])
q("What generic quality checks apply to emission calculations and unit conversions?", "rule", [53],
  {53: "check that conversion factors are correct"},
  ["check units are labeled and carried through", "check conversion factors", "check a sample of calculations"], also=[52, 54])
q("What is the concept of materiality in verification?", "rule", [71],
  {71: "information is considered to be material if, by its inclusion or exclusion, it can be seen to influence any decisions or actions taken by users of it"},
  ["material discrepancy: error that significantly differs from true value"])

# ---------------- targets ----------------
q("What steps are involved in setting a GHG target?", "rule", [77],
  {77: "steps in setting a ghg target"},
  ["10 steps from senior management commitment to tracking and reporting progress"], also=[76])
q("What is the difference between a fixed and a rolling target base year?", "rule", [81, 83],
  {81: "using a rolling target base year",
   83: "comparing a stabilization target under the fixed and rolling target base year approach"},
  ["fixed: compare to a fixed year in the past", "rolling: compare to the previous year"])
q("How should offsets be reported when used to meet a GHG target?", "rule", [83, 84],
  {83: "a ghg target can be met entirely from internal reductions at sources included in the target boundary or through additionally using offsets",
   84: "when reporting on the target, it should be specified whether offsets are used and how much of the target reduction was achieved using them"},
  ["specify whether offsets are used and how much", "report internal emissions separately from offsets"])

# ---------------- paraphrase / keyword ----------------
q("electricity bought from a utility", "paraphrase", [27, 29],
  {27: "purchased electricity is defined as electricity that is purchased or otherwise brought into the organizational boundary of the company",
   29: "companies report the emissions from the generation of purchased electricity"},
  ["purchased electricity -> Scope 2"])
q("supplier-specific emission factors", "keyword", [44, 89],
  {44: "supplier-specific, local grid, or other published emission factors",
   89: "source/supplier specific emission factors"},
  ["preferred over generic factors"])
q("T&D losses", "keyword", [29, 30, 88, 89],
  {88: "t&d losses are not reported under scope 2",
   29: "emissions from the generation of purchased electricity that is consumed during transmission and distribution",
   30: "t&d losses",
   89: "accounting for indirect emissions associated with t&d losses"},
  ["transmission and distribution losses"])

# ---------------- negatives: nothing in the 2004 PDF answers these ----------------
NEG = [
 ("What is the location-based method for Scope 2 reporting?", ["location-based", "location based"]),
 ("How does market-based Scope 2 accounting use contractual instruments and the residual mix?", ["residual mix", "market-based scope 2", "contractual instruments"]),
 ("How do I calculate Scope 3 purchased goods and services emissions using the spend-based method?", ["purchased goods and services", "spend-based"]),
 ("Which targets qualify as science-based targets?", ["science-based", "science based"]),
 ("Which IPCC Sixth Assessment Report GWP values should be used?", ["sixth assessment"]),
 ("What are the 15 categories of Scope 3 emissions?", ["15 categories", "fifteen"]),
]
for query, absent in NEG:
    Q.append(dict(query=query, type="negative", gold_pages=[], also_relevant=[], evidence={},
                  key_points=["not covered by the 2004 PDF: " + ", ".join(absent)], scan=None, absent_terms=absent))

# ---------------- verification ----------------
errors = []
for e in Q:
    for pg, phrase in e["evidence"].items():
        if norm(phrase) not in NP[int(pg)]:
            errors.append(f"MISSING QUOTE p{pg} for {e['query']!r}: {phrase!r}")
    if set(map(int, e["evidence"])) != set(e["gold_pages"]):
        errors.append(f"evidence pages != gold pages for {e['query']!r}")
    for t in e.get("absent_terms", []):
        h = [n for n, tx in NP.items() if t in tx]
        if h:
            errors.append(f"NEGATIVE NOT ABSENT {t!r} found on pages {h} for {e['query']!r}")
if errors:
    print("\n".join(errors)); sys.exit(1)

# completeness scan: pages containing an anchor term that are not gold/also
for e in Q:
    if e.get("scan"):
        found = [n for n, tx in NP.items() if e["scan"] in tx]
        extra = sorted(set(found) - set(e["gold_pages"]) - set(e["also_relevant"]))
        print(f"scan {e['scan']!r}: pages {found}; not in gold/also: {extra}")

# splits: alternate dev/test within each type, deterministic
cnt = {}
for e in Q:
    i = cnt.get(e["type"], 0); cnt[e["type"]] = i + 1
    e["split"] = "dev" if i % 2 == 0 else "test"
    e.pop("scan", None); e.pop("absent_terms", None)

out = ROOT / "build/eval_queries.jsonl"
out.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in Q) + "\n")
print(f"\nOK: {len(Q)} queries written, all {sum(len(e['evidence']) for e in Q)} evidence quotes verified, "
      f"{sum(e['type']=='negative' for e in Q)} negatives verified absent")
