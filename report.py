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

SCOPE_VAR = {1: "var(--s1)", 2: "var(--s2)", 3: "var(--s3)"}
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


# ------------------------------------------------------------------ components (plain HTML/CSS/SVG, no external assets)
def hbars(items, scope, unit="t"):
    """items: (label, tonnes, share_pct). Bars are anchored to the baseline, 4px rounded data end, animated on load."""
    mx = max(v for _, v, _ in items) or 1; rows = []
    for label, v, sh in items:
        tip = f"{label}: {fmt(v)} {unit} ({sh}%)"
        rows.append(f'<div class="hb" data-tip="{e(tip)}"><div class="hl">{e(label)}</div>'
                    f'<div class="ht"><div class="hf" style="--w:{100 * v / mx:.1f}%;background:{SCOPE_VAR[scope]}"></div></div>'
                    f'<div class="hv">{fmt(v)}<span>{sh}%</span></div></div>')
    return "".join(rows)


def stack(parts, height=34):
    """Single 100% stacked bar, 2px surface gaps between segments, direct labels when wide enough."""
    tot = sum(v for _, v, _ in parts) or 1; segs = []
    for label, v, scope in parts:
        pct = 100 * v / tot
        segs.append(f'<div class="seg" style="flex:{v};background:{SCOPE_VAR[scope]}" data-tip="{e(label)}: {fmt(v)} t ({pct:.1f}%)">'
                    + (f'<span>{e(label)} {pct:.0f}%</span>' if pct > 14 else "") + '</div>')
    return f'<div class="stack" style="height:{height}px">{"".join(segs)}</div>'


def matrix(actions):
    """Priority matrix: x = effort, y = size of the hotspot (share of total), bubble area = tonnes. Dashed ring = fix the data first."""
    if not actions: return ""
    W, H, L, B, T = 760, 330, 70, 40, 14; cols = {"low": 0, "medium": 1, "high": 2}; used = {}
    mx = max(a["hotspot"]["share_of_total"] for a in actions) * 1.25 or 1; mt = max(a["hotspot"]["tonnes"] for a in actions)
    cw = (W - L - 10) / 3; g = [f'<rect x="{L}" y="{T}" width="{cw:.0f}" height="{(H - B - T) * 0.5:.0f}" fill="var(--s3)" opacity=".10"/>',
                                f'<text x="{L + 8}" y="{T + 16}" class="ax" fill="var(--s3)">Do first: big and easy</text>']
    for i, name in enumerate(("Low effort", "Medium effort", "High effort")):
        g.append(f'<text x="{L + cw * (i + .5):.0f}" y="{H - 14}" text-anchor="middle" class="ax">{name}</text>')
        if i: g.append(f'<line x1="{L + cw * i:.0f}" x2="{L + cw * i:.0f}" y1="{T}" y2="{H - B}" class="gl"/>')
    for k in range(0, 5):
        y = T + (H - B - T) * k / 4; g.append(f'<line x1="{L}" x2="{W - 10}" y1="{y:.0f}" y2="{y:.0f}" class="gl"/>'
                                               f'<text x="{L - 8}" y="{y + 4:.0f}" text-anchor="end" class="ax">{mx * (1 - k / 4):.0f}%</text>')
    for i, a in enumerate(actions, 1):
        h = a["hotspot"]; c = cols.get(str(a.get("effort", "medium")).lower(), 1); n = used.get(c, 0); used[c] = n + 1
        cx = L + cw * (c + .5) + (n % 3 - 1) * 46; cy = T + (H - B - T) * (1 - h["share_of_total"] / mx); r = 12 + 22 * (h["tonnes"] / mt) ** .5
        tip = f"{i}. {h['label']}: {fmt(h['tonnes'])} t, {h['share_of_total']}% of total, effort {a.get('effort')}" + (" · fix data first" if a.get("caveat") else "")
        g.append(f'<g data-tip="{e(tip)}"><circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.0f}" fill="{SCOPE_VAR[h["scope"]]}" fill-opacity=".85" '
                 f'stroke="var(--surface)" stroke-width="2"' + (' stroke-dasharray="4 3"' if a.get("caveat") else "") + '/>'
                 + (f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r + 4:.0f}" fill="none" stroke="var(--fg)" stroke-width="1.5" stroke-dasharray="4 3" opacity=".6"/>' if a.get("caveat") else "")
                 + f'<text x="{cx:.0f}" y="{cy + 5:.0f}" text-anchor="middle" class="bn">{i}</text></g>')
    return f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Priority matrix of reduction actions">{"".join(g)}</svg>'


STATUS_ICON = {"gap": "✕", "verify": "!", "unknown": "?", "info": "i", "pass": "✓"}


def insights(d):
    t = d["totals"]; out = []
    top = max(d["available"], key=lambda s: t[f"scope{s}"]["tonnes"])
    out.append((f'{t[f"scope{top}"]["share_pct"]}%', f"of emissions are Scope {top}", top))
    if "s2_energy" in d: i = d["s2_energy"]["items"][0]; out.append((f'{i["share_pct"]}%', f'of Scope 2 is {i["name"].lower()}', 2))
    if "s1_activity" in d: i = d["s1_activity"]["items"][0]; out.append((f'{i["share_pct"]}%', f'of Scope 1 is {i["name"].lower()}', 1))
    if "s3_act" in d: i = d["s3_act"]["items"][0]; out.append((fmt(i["tonnes"]) + " t", f'{i["name"]}, top Scope 3 activity', 3))
    return out


def render(d, headline, actions, project, model):
    t = d["totals"]; av = d["available"]
    chips = "".join(f'<div class="chip-i" style="--c:{SCOPE_VAR[s]}"><b>{e(v)}</b><span>{e(l)}</span></div>' for v, l, s in insights(d))
    kpis = "".join(f'<div class="kpi" style="--c:{SCOPE_VAR[s]}" data-tip="{t[f"scope{s}"]["months"]} months of data">'
                   f'<div class="kl">Scope {s}</div><div class="kv">{fmt(t[f"scope{s}"]["tonnes"])}<small> t</small></div>'
                   f'<div class="ks">{t[f"scope{s}"]["share_pct"]}% of total · {t[f"scope{s}"]["months"]} months</div></div>' for s in av)
    cav = f'<div class="note">⚠ {e(t["caveat"])} Treat the shares as indicative.</div>' if t.get("caveat") else ""
    split = stack([(f"Scope {s}", t[f"scope{s}"]["tonnes"], s) for s in av])
    small = [s for s in av if t[f"scope{s}"]["share_pct"] < 10]
    zoom = (f'<div class="sub zoom">Zoom on the small scopes (Scope {" + ".join(str(s) for s in small)}):</div>'
            + stack([(f"Scope {s}", t[f"scope{s}"]["tonnes"], s) for s in small])) if len(small) > 1 else ""
    cards = []
    if "s1_activity" in d: cards.append(("Scope 1 · by activity", hbars([(i["name"], i["tonnes"], i["share_pct"]) for i in d["s1_activity"]["items"]], 1)))
    if "s2_energy" in d: cards.append(("Scope 2 · by energy type", hbars([(i["name"], i["tonnes"], i["share_pct"]) for i in d["s2_energy"]["items"]], 2)))
    if "s3_cat" in d: cards.append(("Scope 3 · top categories", hbars([(i["name"], i["tonnes"], i["share_pct"]) for i in d["s3_cat"]["items"][:8]], 3)))
    if "s3_act" in d: cards.append(("Scope 3 · top activities", hbars([(i["name"], i["tonnes"], i["share_pct"]) for i in d["s3_act"]["items"]], 3)))
    cards_html = "".join(f'<div class="card"><h3>{e(n)}</h3>{c}</div>' for n, c in cards)
    acts = ""
    for i, a in enumerate(actions, 1):
        h = a["hotspot"]; ef = str(a.get("effort", "")).lower()
        acts += (f'<article class="action" style="--c:{SCOPE_VAR[h["scope"]]}"><div class="rank">{i}</div><div class="ab">'
                 f'<div class="ttl">{e(a["action"])}</div>'
                 f'<div class="meta"><span class="tag">Scope {h["scope"]} · {e(h["label"])}</span><span class="size"><b>{fmt(h["tonnes"])} t</b> · {h["share_of_total"]}% of total</span>'
                 f'<span class="eff eff-{e(ef)}">{e(ef)} effort</span></div>'
                 f'<div class="first"><b>First step</b> {e(a.get("first_step", ""))}</div>'
                 + (f'<div class="cav"><b>Fix the data first</b> {e(a["caveat"])}</div>' if a.get("caveat") else "") + '</div></article>')
    counts = d["quality"]["counts"]
    summ = "".join(f'<span class="st st-{k}"><i>{STATUS_ICON[k]}</i>{counts.get(k, 0)} {STATUS[k][1].lower()}</span>' for k in ("gap", "verify", "unknown", "info", "pass"))
    fnd = "".join(f'<div class="fr"><span class="st st-{f["status"]}"><i>{STATUS_ICON[f["status"]]}</i>{STATUS[f["status"]][1]}</span>'
                  f'<span class="fs">{"Scope " + str(f["scope"]) if f.get("scope") else "All"}</span><span class="ft">{e(f["title"])}</span><span class="fv">{e(f["severity"])}</span></div>'
                  for f in d["quality"]["findings"])
    pe = d["peers"]; peer_rows = ""
    for m, sc in (("scope1", 1), ("scope2", 2)):
        if m not in t: continue
        vals = [("This company" + (" (3 mo, annualised)" if pe["company"][m].get("annualised_tonnes_if_flat") else ""),
                 pe["company"][m].get("annualised_tonnes_if_flat") or t[m]["tonnes"], 1)]
        for name in ("Docusign", "Shopify"):
            x = next((x for x in pe["items"] if x["peer"] == name and x["metric"] in (m, m + "_location")), None)
            if x: vals.append((name + (" (location-based)" if x["metric"].endswith("location") else ""), float(x["value"]), 2))
        mx = max(v for _, v, _ in vals); peer_rows += f'<div class="pgroup"><h4>Scope {sc}</h4>'
        for lab, v, kind in vals:
            peer_rows += (f'<div class="hb" data-tip="{e(lab)}: {fmt(v)} t"><div class="hl">{e(lab)}</div><div class="ht"><div class="hf" '
                          f'style="--w:{100 * v / mx:.1f}%;background:{SCOPE_VAR[sc] if kind == 1 else "var(--mut)"}"></div></div><div class="hv">{fmt(v)}</div></div>')
        peer_rows += "</div>"
    pcav = "".join(f"<li>{e(x)}</li>" for x in pe["caveats"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Emissions summary: {e(project)}</title><style>
:root{{color-scheme:light;--bg:#f4f3ef;--surface:#fcfcfb;--fg:#0b0b0b;--mut:#6a6963;--line:#e4e2da;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;
--good:#0ca30c;--warn:#b7791f;--bad:#d03b3b;--hero1:#10231f;--hero2:#16423a}}
@media (prefers-color-scheme:dark){{:root{{color-scheme:dark;--bg:#111110;--surface:#1a1a19;--fg:#f0efec;--mut:#a3a29a;--line:#2f2f2c;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--warn:#fab219;--hero1:#0b1513;--hero2:#123731}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}}
.hero{{background:linear-gradient(135deg,var(--hero1),var(--hero2));color:#f3f7f5;padding:44px 16px 64px}}.wrap{{max-width:1040px;margin:auto}}
.eyebrow{{letter-spacing:.14em;text-transform:uppercase;font-size:12px;opacity:.7}}h1{{margin:6px 0 0;font-size:38px;line-height:1.1;letter-spacing:-.02em}}
.hero .big{{display:flex;align-items:baseline;gap:10px;margin-top:22px}}.hero .big b{{font-size:64px;letter-spacing:-.03em}}.hero .big span{{opacity:.75}}
.headline{{max-width:720px;font-size:19px;margin-top:14px;opacity:.95}}.chips{{display:flex;flex-wrap:wrap;gap:10px;margin-top:22px}}
.chip-i{{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);border-left:4px solid var(--c);border-radius:10px;padding:8px 14px;display:flex;flex-direction:column}}
.chip-i b{{font-size:22px}}.chip-i span{{font-size:12px;opacity:.8}}
main{{margin-top:-34px;padding:0 16px 60px}}section{{margin-top:34px}}h2{{font-size:22px;margin:0 0 4px;letter-spacing:-.01em}}.lead{{color:var(--mut);margin:0 0 14px;font-size:14px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}}.kpi,.card,.action,.panel{{background:var(--surface);border:1px solid var(--line);border-radius:14px}}
.kpi{{padding:16px 18px;border-top:4px solid var(--c)}}.kl{{font-size:12px;color:var(--mut);text-transform:uppercase;letter-spacing:.08em}}.kv{{font-size:34px;font-weight:700;letter-spacing:-.02em}}.kv small{{font-size:14px;color:var(--mut);font-weight:500}}.ks{{font-size:13px;color:var(--mut)}}
.note{{background:color-mix(in srgb,var(--warn) 16%,var(--surface));border:1px solid color-mix(in srgb,var(--warn) 40%,var(--line));border-radius:10px;padding:10px 14px;margin:14px 0;font-size:14px}}
.panel{{padding:18px}}.stack{{display:flex;gap:2px;border-radius:8px;overflow:hidden}}.seg{{display:flex;align-items:center;justify-content:center;min-width:3px}}.seg span{{color:#fff;font-size:12px;font-weight:600;white-space:nowrap;padding:0 6px;text-shadow:0 1px 2px rgba(0,0,0,.35)}}
.zoom{{margin:14px 0 6px}}.sub{{color:var(--mut);font-size:13px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:12px}}
.card{{padding:16px 18px}}h3{{margin:0 0 12px;font-size:13px;color:var(--mut);text-transform:uppercase;letter-spacing:.08em}}h4{{margin:12px 0 6px;font-size:13px;color:var(--mut)}}
.hb{{display:grid;grid-template-columns:150px 1fr 96px;gap:10px;align-items:center;padding:4px 0}}.hl{{font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.ht{{height:14px;background:color-mix(in srgb,var(--line) 55%,transparent);border-radius:4px}}.hf{{height:100%;width:var(--w);border-radius:0 4px 4px 0;animation:grow .9s cubic-bezier(.2,.7,.2,1) both}}
.hv{{font-size:13px;font-variant-numeric:tabular-nums;text-align:right}}.hv span{{color:var(--mut);margin-left:6px;font-size:12px}}@keyframes grow{{from{{width:0}}}}
@media (prefers-reduced-motion:reduce){{.hf{{animation:none}}}}.hb:hover .hf{{filter:brightness(1.12)}}
.action{{display:flex;gap:16px;padding:16px 18px;margin:10px 0;border-left:5px solid var(--c)}}.rank{{font-size:30px;font-weight:700;color:var(--c);width:34px;line-height:1}}.ab{{flex:1}}.ttl{{font-size:17px;font-weight:620}}
.meta{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0}}.tag{{background:color-mix(in srgb,var(--c) 16%,transparent);color:var(--fg);border-radius:999px;padding:2px 10px;font-size:12px;font-weight:600}}
.size{{font-size:13px;color:var(--mut)}}.eff{{border:1px solid var(--line);border-radius:999px;padding:1px 9px;font-size:12px}}.eff-low{{border-color:var(--good);color:var(--good)}}.eff-high{{border-color:var(--bad);color:var(--bad)}}
.first{{font-size:14px}}.first b,.cav b{{display:inline-block;font-size:11px;text-transform:uppercase;letter-spacing:.08em;margin-right:8px;color:var(--mut)}}.cav{{font-size:13px;margin-top:8px;padding:8px 10px;border-radius:8px;background:color-mix(in srgb,var(--warn) 13%,transparent)}}
svg text.ax{{font-size:12px;fill:var(--mut)}}svg .gl{{stroke:var(--line);stroke-dasharray:3 4}}svg .bn{{font-size:13px;font-weight:700;fill:#fff}}
.legend{{display:flex;gap:18px;flex-wrap:wrap;font-size:12px;color:var(--mut);margin-top:6px}}
.st{{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;margin-right:12px}}.st i{{font-style:normal;width:18px;height:18px;border-radius:50%;display:inline-grid;place-items:center;color:#fff;font-size:11px}}
.st-gap i{{background:var(--bad)}}.st-verify i{{background:#c9731a}}.st-unknown i{{background:#7b7a73}}.st-info i{{background:var(--s1)}}.st-pass i{{background:var(--good)}}
.fr{{display:grid;grid-template-columns:96px 70px 1fr 64px;gap:8px;padding:9px 4px;border-bottom:1px solid var(--line);font-size:14px;align-items:center}}.fr:last-child{{border:0}}.fs,.fv{{color:var(--mut);font-size:12px}}
ul.cv{{color:var(--mut);font-size:13px;padding-left:18px}}footer{{margin-top:40px;color:var(--mut);font-size:12px}}
#tip{{position:fixed;pointer-events:none;background:var(--fg);color:var(--bg);padding:6px 10px;border-radius:6px;font-size:12px;opacity:0;transition:opacity .1s;z-index:9;max-width:320px}}
@media (max-width:640px){{h1{{font-size:28px}}.hero .big b{{font-size:44px}}.hb{{grid-template-columns:100px 1fr 80px}}.grid{{grid-template-columns:1fr}}.fr{{grid-template-columns:84px 1fr}}.fs,.fv{{display:none}}}}
@media print{{.hero{{background:#fff;color:#000}}#tip{{display:none}}}}
</style></head><body>
<header class="hero"><div class="wrap"><div class="eyebrow">Emissions summary · {e(project)}</div><h1>Where your emissions are, and what to do first</h1>
<div class="big"><b>{fmt(t["total_tonnes"])}</b><span>tCO2e in the data supplied</span></div>
{f'<div class="headline">{e(headline)}</div>' if headline else ''}<div class="chips">{chips}</div></div></header>
<main><div class="wrap">
<section><div class="kpis">{kpis}</div>{cav}</section>
<section><h2>How the total splits</h2><p class="lead">Share of emissions by scope.</p><div class="panel">{split}{zoom}</div></section>
<section><h2>Hotspots</h2><p class="lead">The largest sources inside each scope. Hover a bar for the exact figure.</p><div class="grid">{cards_html}</div></section>
<section><h2>What to focus on</h2><p class="lead">Suggested actions are best practice, not Protocol requirements. Bubble area is the hotspot's emissions; a dashed ring means the data should be fixed before acting. No reduction percentage is claimed because none can be derived from this data.</p>
<div class="panel">{matrix(actions)}<div class="legend"><span>● area = tonnes</span><span>◌ dashed ring = fix the data first</span><span>numbers match the list below</span></div></div>{acts or '<div class="note">No actions could be generated.</div>'}</section>
<section><h2>Can these numbers be trusted?</h2><p class="lead">{summ}</p><div class="panel">{fnd}</div></section>
<section><h2>Compared with peers</h2><p class="lead">Scope 1 and 2 in tCO2e. Read the caveats before drawing conclusions.</p><div class="panel">{peer_rows}<ul class="cv">{pcav}</ul></div></section>
<footer>Generated {time.strftime("%Y-%m-%d %H:%M")} · figures computed from the uploaded CSVs, advice by {e(model)} · knowledge base: GHG Protocol Corporate Standard (2004), which predates the 2015 Scope 2 Guidance and the 2011 Scope 3 Standard.</footer>
</div></main><div id="tip"></div>
<script>const tip=document.getElementById('tip');document.addEventListener('mousemove',ev=>{{const el=ev.target.closest('[data-tip]');
if(!el){{tip.style.opacity=0;return}}tip.textContent=el.dataset.tip;tip.style.opacity=1;tip.style.left=Math.min(ev.clientX+14,innerWidth-330)+'px';tip.style.top=(ev.clientY+16)+'px'}});</script>
</body></html>"""


def build_report(agent, project):
    d = collect(); headline, acts, u = advise(agent, d)
    from agent import MODEL
    page = render(d, headline, acts, project, MODEL)
    out = et.PROJECTS / project / "reports"; out.mkdir(parents=True, exist_ok=True)
    f = out / f"summary-{time.strftime('%Y%m%d-%H%M%S')}.html"; f.write_text(page)
    return f, page, dict(tokens_in=u.prompt_token_count or 0, tokens_out=u.candidates_token_count or 0, actions=len(acts))
