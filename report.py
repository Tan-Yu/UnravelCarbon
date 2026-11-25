"""Summary report as one self-contained HTML file (inline SVG charts, no external assets).

Numbers come only from emissions_tools / peers. The LLM is used for one thing: proposing reduction actions for the
hotspots the code found. It refers to hotspots by id; the report attaches the tonnes and shares itself, so the model
cannot invent figures. Suggestions are labelled best practice (not Protocol requirements) and carry no reduction %.
"""
import html, json, re, time
from pathlib import Path
from google.genai import types
import emissions_tools as et
import peers

SCOPE_COLOURS = {1: "#c2410c", 2: "#1d4ed8", 3: "#0f766e"}
STATUS = {"gap": ("#b91c1c", "Gap"), "verify": ("#b45309", "Verify"), "unknown": ("#6b7280", "Unknown"),
          "info": ("#2563eb", "Info"), "pass": ("#15803d", "Pass")}
e = html.escape
fmt = lambda x: f"{x:,.0f}" if abs(x) >= 100 else f"{x:,.1f}"

PROMPT = """You advise a sustainability team. Below are the emission hotspots found in their data (ids H1, H2...) and the data-quality findings.
Propose emission-reduction actions. Rules:
- Each action must refer to exactly one hotspot_id from the list. Do not state any tonnes, percentages or reduction amounts; the report adds the real figures.
- Be specific to the hotspot's activity (what to change, and the first step), not generic. Say when the right first action is to fix the data.
- If a data-quality finding makes a hotspot unreliable, say so in "caveat" and make the first step a data fix.
- 4 to 7 actions, most important first. effort is one of: low, medium, high.
Return ONLY JSON: {{"headline": "two sentences on where to focus", "actions": [{{"hotspot_id": "H1", "action": "...", "first_step": "...", "effort": "low|medium|high", "caveat": "... or empty"}}]}}

HOTSPOTS:
{hotspots}

DATA-QUALITY FINDINGS (status, scope, title):
{findings}
"""


# ------------------------------------------------------------------ data
def collect():
    t = et.totals(); av = et.available(); d = dict(totals=t, available=av, hotspots=[])
    total = t["total_tonnes"]
    def add(scope, kind, label, tonnes, share_of_scope):
        d["hotspots"].append(dict(id=f"H{len(d['hotspots']) + 1}", scope=scope, kind=kind, label=label, tonnes=tonnes,
                                  share_of_scope=share_of_scope, share_of_total=round(100 * tonnes / total, 2)))
    if 1 in av:
        d["s1_activity"] = et.scope1_breakdown("Activity_Type"); d["s1_fuel"] = et.scope1_breakdown("Fuel_Type")
        for it in d["s1_activity"]["items"][:2]: add(1, "activity", it["name"], it["tonnes"], it["share_pct"])
    if 2 in av:
        d["s2_energy"] = et.scope2_breakdown("Energy_Type")
        it = d["s2_energy"]["items"][0]; add(2, "energy type", it["name"], it["tonnes"], it["share_pct"])
    if 3 in av:
        d["s3_cat"] = et.scope3_top("Category", 10); d["s3_act"] = et.scope3_top("Activity_Description", 6)
        d["suppliers"] = et.supplier_priorities(5)
        for it in d["s3_cat"]["items"][:3]: add(3, "category", it["name"], it["tonnes"], it["share_pct"])
        for it in d["s3_act"]["items"][:2]: add(3, "activity", it["name"], it["tonnes"], it["share_pct"])
    d["quality"] = et.quality_report(); d["peers"] = peers.compare_with_peers()
    return d


def advise(agent, d):
    """One LLM call: reduction actions per hotspot. Returns (headline, actions) with figures attached by id."""
    hs = json.dumps([{k: h[k] for k in ("id", "scope", "kind", "label")} | dict(share_of_total_pct=h["share_of_total"]) for h in d["hotspots"]])
    fs = "\n".join(f"{f['status']} | scope {f.get('scope')} | {f['title']}" for f in d["quality"]["findings"] if f["status"] != "pass")
    from agent import MODEL
    r = agent.client.models.generate_content(model=MODEL, contents=PROMPT.format(hotspots=hs, findings=fs),
                                             config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json",
                                                                                thinking_config=types.ThinkingConfig(thinking_budget=0)))
    try: j = json.loads(r.text)
    except Exception: return "", [], r.usage_metadata
    by = {h["id"]: h for h in d["hotspots"]}
    acts = [dict(a, hotspot=by[a["hotspot_id"]]) for a in j.get("actions", []) if a.get("hotspot_id") in by]
    return j.get("headline", ""), acts, r.usage_metadata


# ------------------------------------------------------------------ svg charts
def bars(items, colour, width=520):
    if not items: return ""
    mx = max(v for _, v, _ in items) or 1; rows = []
    for i, (label, v, extra) in enumerate(items):
        y = i * 30; w = max(2, (width - 250) * v / mx)
        rows.append(f'<text x="0" y="{y + 15}" font-size="12" fill="currentColor">{e(label[:32])}</text>'
                    f'<rect x="200" y="{y + 3}" width="{w:.1f}" height="16" rx="3" fill="{colour}"/>'
                    f'<text x="{205 + w:.1f}" y="{y + 15}" font-size="11" fill="currentColor">{fmt(v)} t{extra}</text>')
    return f'<svg viewBox="0 0 {width} {len(items) * 30}" width="100%" role="img">{"".join(rows)}</svg>'


def donut(parts):
    tot = sum(v for _, v, _ in parts) or 1; r, c = 70, 2 * 3.14159 * 70; off = 0; arcs = []; legend = []
    for label, v, col in parts:
        ln = c * v / tot
        arcs.append(f'<circle r="{r}" cx="100" cy="100" fill="none" stroke="{col}" stroke-width="32" '
                    f'stroke-dasharray="{ln:.2f} {c - ln:.2f}" stroke-dashoffset="{-off:.2f}" transform="rotate(-90 100 100)"/>')
        off += ln; legend.append(f'<div><span class="dot" style="background:{col}"></span>{e(label)}: <b>{fmt(v)} t</b> ({100 * v / tot:.1f}%)</div>')
    return f'<div class="donut"><svg viewBox="0 0 200 200" width="190">{"".join(arcs)}</svg><div>{"".join(legend)}</div></div>'


# ------------------------------------------------------------------ html
def render(d, headline, actions, project, model):
    t = d["totals"]; sc = [(f"Scope {s}", t[f"scope{s}"]["tonnes"], SCOPE_COLOURS[s]) for s in d["available"]]
    kpis = "".join(f'<div class="kpi"><div class="v">{fmt(v)}</div><div class="l">{e(l)} tCO2e<br><span>{t[f"scope{s}"]["share_pct"]}% of total, {t[f"scope{s}"]["months"]} months</span></div></div>'
                   for (l, v, _), s in zip(sc, d["available"]))
    cav = f'<div class="note">⚠ {e(t["caveat"])} Treat the shares as indicative.</div>' if t.get("caveat") else ""
    charts = []
    if "s1_activity" in d: charts.append(("Scope 1 by activity", bars([(i["name"], i["tonnes"], f' ({i["share_pct"]}%)') for i in d["s1_activity"]["items"]], SCOPE_COLOURS[1])))
    if "s2_energy" in d: charts.append(("Scope 2 by energy type", bars([(i["name"], i["tonnes"], f' ({i["share_pct"]}%)') for i in d["s2_energy"]["items"]], SCOPE_COLOURS[2])))
    if "s3_cat" in d: charts.append(("Scope 3 top categories", bars([(i["name"], i["tonnes"], f' ({i["share_pct"]}%)') for i in d["s3_cat"]["items"][:8]], SCOPE_COLOURS[3])))
    if "s3_act" in d: charts.append(("Scope 3 top activities", bars([(i["name"], i["tonnes"], f' ({i["share_pct"]}%)') for i in d["s3_act"]["items"]], SCOPE_COLOURS[3])))
    chart_html = "".join(f'<div class="card"><h3>{e(n)}</h3>{c}</div>' for n, c in charts)

    acts = ""
    for i, a in enumerate(actions, 1):
        h = a["hotspot"]
        acts += (f'<div class="action"><div class="rank">{i}</div><div><div class="ttl">{e(a["action"])}</div>'
                 f'<div class="meta"><span class="tag" style="background:{SCOPE_COLOURS[h["scope"]]}">Scope {h["scope"]}</span> '
                 f'{e(h["label"])}: <b>{fmt(h["tonnes"])} t</b> ({h["share_of_total"]}% of total) · effort: <b>{e(str(a.get("effort", "")))}</b></div>'
                 f'<div class="first">First step: {e(a.get("first_step", ""))}</div>'
                 + (f'<div class="cav">Data caveat: {e(a["caveat"])}</div>' if a.get("caveat") else "") + '</div></div>')
    fnd = "".join(f'<tr><td><span class="chip" style="background:{STATUS[f["status"]][0]}">{STATUS[f["status"]][1]}</span></td>'
                  f'<td>{"Scope " + str(f["scope"]) if f.get("scope") else "All"}</td><td>{e(f["title"])}</td><td>{e(f["severity"])}</td></tr>'
                  for f in d["quality"]["findings"])
    counts = d["quality"]["counts"]
    cnt = " · ".join(f"{counts.get(k, 0)} {STATUS[k][1].lower()}" for k in ("gap", "verify", "unknown", "info", "pass"))
    pe = d["peers"]; prow = ""
    for m in ("scope1", "scope2"):
        c = t.get(m)
        if not c: continue
        cell = lambda name: next((f"{fmt(float(x['value']))}" for x in pe["items"] if x["peer"] == name and x["metric"] in (m, m + "_location")), "n/a")
        ann = pe["company"][m].get("annualised_tonnes_if_flat")
        prow += (f"<tr><td>{m.replace('scope', 'Scope ')}</td><td>{fmt(c['tonnes'])} ({c['months']} mo)"
                 + (f"<br><span class='sub'>≈ {fmt(ann)} annualised, if flat</span>" if ann else "")
                 + f"</td><td>{cell('Docusign')}{' (location-based; market 3.1)' if m == 'scope2' else ''}</td><td>{cell('Shopify')}</td></tr>")
    pcav = "".join(f"<li>{e(x)}</li>" for x in pe["caveats"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Emissions summary: {e(project)}</title><style>
:root{{--bg:#fafaf7;--fg:#1c1b19;--mut:#6b6a65;--card:#fff;--line:#e5e3dc}}
@media (prefers-color-scheme:dark){{:root{{--bg:#14140f;--fg:#ecebe6;--mut:#a09f98;--card:#1d1d17;--line:#33332b}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}}
main{{max-width:1000px;margin:auto;padding:28px 16px 60px}}h1{{margin:0 0 4px;font-size:26px}}h2{{margin:36px 0 10px;font-size:19px}}h3{{margin:0 0 8px;font-size:14px;color:var(--mut)}}
.sub,.l span{{color:var(--mut);font-size:12px}}.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}}
.kpi,.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}}.kpi .v{{font-size:28px;font-weight:650}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:12px}}.note{{background:#fef3c7;color:#78350f;border-radius:8px;padding:10px 12px;margin:12px 0}}
.headline{{font-size:17px;border-left:4px solid #0f766e;padding:4px 14px;margin:14px 0}}.action{{display:flex;gap:14px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin:10px 0}}
.rank{{font-size:22px;font-weight:700;color:var(--mut);width:24px}}.ttl{{font-weight:600}}.meta{{font-size:13px;color:var(--mut);margin:4px 0}}.first{{font-size:14px}}.cav{{font-size:13px;color:#b45309;margin-top:4px}}
.tag,.chip{{color:#fff;border-radius:4px;padding:1px 7px;font-size:12px}}.donut{{display:flex;gap:18px;align-items:center;flex-wrap:wrap}}.dot{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}}
table{{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}}td,th{{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;font-size:14px;vertical-align:top}}
footer{{margin-top:36px;color:var(--mut);font-size:12px}}</style></head><body><main>
<h1>Emissions summary: {e(project)}</h1><div class="sub">Generated {time.strftime("%Y-%m-%d %H:%M")} · all figures computed from the uploaded CSVs; suggestions by {e(model)}</div>
<h2>Where to focus</h2>{f'<div class="headline">{e(headline)}</div>' if headline else ''}
<div class="kpis"><div class="kpi"><div class="v">{fmt(t["total_tonnes"])}</div><div class="l">Total tCO2e<br><span>sum of the scopes shown</span></div></div>{kpis}</div>{cav}
<h2>Total by scope</h2><div class="card">{donut(sc)}</div>
<h2>Hotspots</h2><div class="grid">{chart_html}</div>
<h2>Suggested reduction actions</h2><div class="sub">Best practice, not Protocol requirements. Sized by the hotspot's emissions; no reduction percentage is claimed because none can be derived from this data.</div>{acts or '<div class="note">No actions could be generated.</div>'}
<h2>Data quality: can these numbers be trusted?</h2><div class="sub">{cnt}</div><table><tr><th>Status</th><th>Scope</th><th>Finding</th><th>Severity</th></tr>{fnd}</table>
<h2>Compared with peers (tCO2e)</h2><table><tr><th>Metric</th><th>This company</th><th>Docusign FY25</th><th>Shopify 2024</th></tr>{prow}</table>
<div class="sub" style="margin-top:8px">Read before comparing:</div><ul class="sub">{pcav}</ul>
<footer>Knowledge base: GHG Protocol Corporate Standard (2004). It does not include the 2015 Scope 2 Guidance or the 2011 Scope 3 Standard.</footer></main></body></html>"""


def build_report(agent, project):
    d = collect(); headline, acts, u = advise(agent, d)
    from agent import MODEL
    page = render(d, headline, acts, project, MODEL)
    out = et.PROJECTS / project / "reports"; out.mkdir(parents=True, exist_ok=True)
    f = out / f"summary-{time.strftime('%Y%m%d-%H%M%S')}.html"; f.write_text(page)
    return f, page, dict(tokens_in=u.prompt_token_count or 0, tokens_out=u.candidates_token_count or 0, actions=len(acts))
