"""Streamlit chat UI. Run: streamlit run app.py
One shared GHG Protocol knowledge base; one folder per company in projects/<name>/ (CSVs + saved chats)."""
import io, json, re, time, uuid
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import streamlit as st
from report import build_report
import emissions_tools as et
from agent import Agent, MODEL, MODELS, PROMPT_VERSION

st.set_page_config(page_title="Emissions Analysis Agent", layout="wide")


@st.cache_resource
def get_agent():
    return Agent()


ag = get_agent()
S = st.session_state
S.setdefault("msgs", []); S.setdefault("hist", []); S.setdefault("sid", time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4])
S.setdefault("tot", dict(q=0, tin=0, tout=0, tools=0, cost=0.0))
S.setdefault("project", et.list_projects()[0] if et.list_projects() else None)

QUICK = ["Which Scope 3 category has the highest emissions?",
         "What share of Scope 2 comes from steam, and does the GHG Protocol count steam as Scope 2?",
         "Is Scope 3 reporting mandatory under the GHG Protocol?",
         "Which suppliers should we prioritise for engagement?"]
REPORT = ("Generate a summary report: (1) totals by scope with shares, (2) the top hotspots in Scope 1, 2 and 3, "
          "(3) a data-quality assessment where each point is labelled Protocol requirement (cited) or Best practice, "
          "(4) knowledge-base gaps. Suggest fixes; do not rewrite the data.")


def reset_chat():
    S.msgs, S.hist = [], []; S.sid = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
    S.tot = dict(q=0, tin=0, tout=0, tools=0, cost=0.0)


def show_sources(sources, key):
    if not sources: return
    st.caption("Sources (click to see the data)")
    cols = st.columns(min(3, len(sources)))
    for i, s in enumerate(sources):
        with cols[i % len(cols)].popover(f"[{s['n']}] {s['label']}", use_container_width=True):
            d = s["detail"]
            if s["kind"] == "page":
                st.markdown("**Text of this page of the PDF** (as extracted):")
                st.text(re.sub(r"\n{3,}", "\n\n", d)[:6000])
            else:
                st.markdown(f"**Tool:** `{s['tool']}`  \n**Arguments:** `{s['args']}`  \n**Folder:** `projects/{S.project}/`")
                if isinstance(d, dict) and isinstance(d.get("items"), list):
                    st.dataframe(pd.DataFrame(d["items"]), hide_index=True)
                    st.json({k: v for k, v in d.items() if k != "items"}, expanded=False)
                elif isinstance(d, dict) and isinstance(d.get("findings"), list):
                    st.dataframe(pd.DataFrame([{k: f[k] for k in ("scope", "status", "severity", "title") if k in f} for f in d["findings"]]),
                                 hide_index=True)
                    st.json(d["findings"], expanded=False)
                else:
                    st.json(d, expanded=False)


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("Company project")
    names = et.list_projects()
    if names:
        sel = st.selectbox("Project", names, index=names.index(S.project) if S.project in names else 0)
        if sel != S.project: S.project = sel; reset_chat(); st.rerun()
    with st.expander("New project"):
        new = st.text_input("Company name", key="newname")
        if st.button("Create") and new.strip():
            slug = re.sub(r"[^a-z0-9_-]+", "-", new.strip().lower()).strip("-")
            (et.PROJECTS / slug / "chats").mkdir(parents=True, exist_ok=True)
            S.project = slug; reset_chat(); st.rerun()
    if not S.project:
        st.info("Create a project to start."); st.stop()
    ag.set_project(S.project)

    with st.expander("Upload data (replaces that scope's file)"):
        for sc in (1, 2, 3):
            up = st.file_uploader(f"scope{sc}.csv", type="csv", key=f"up{sc}_{S.project}")
            if up is not None:
                try:
                    df = pd.read_csv(io.BytesIO(up.getvalue())); errs = et.validate_csv(sc, df)
                except Exception as e:
                    errs = [f"cannot read file: {e}"]
                if errs:
                    st.error("Not saved: " + "; ".join(errs))
                else:
                    (et.PROJECTS / S.project).mkdir(exist_ok=True)
                    (et.PROJECTS / S.project / et.FILES[sc]).write_bytes(up.getvalue())
                    st.success(f"Saved scope{sc}.csv ({len(df)} rows). Loaded; no restart needed.")

    st.subheader("Data status")
    avail = et.available()
    if not avail: st.warning("No CSVs yet. Upload at least one scope.")
    for f, s in (et.load_status() if avail else {}).items():
        if s["ok"]:
            st.markdown(f"✅ **{f}** ({s['rows']} rows): all checks pass")
        else:
            why = ["arithmetic does not recompute"] * (not s["arithmetic_ok"]) + s["issues"]
            st.markdown(f"❌ **{f}** ({s['rows']} rows): {len(why)} to review")
            for w in why: st.caption(f"• {w}")
            st.caption("Ask for a quality assessment for details.")
    for sc in (1, 2, 3):
        if sc not in avail: st.markdown(f"**scope{sc}.csv**: missing")
    st.caption("Knowledge base (shared): GHG Protocol Corporate Standard 2004, 116 pages. Peer reports: not loaded.")
    st.divider()
    st.subheader("Model")
    S.model = st.selectbox("Answer with", list(MODELS), index=list(MODELS).index(S.get("model", MODEL)),
                           help="Switching keeps the conversation; the next answer uses the new model.")
    compare = st.toggle("Compare models side by side", help="Each question goes to every chosen model at once. "
                        "Compare answers are single-turn (no history) so the models see the same input.")
    cmp_models = st.multiselect("Models to compare", list(MODELS), default=list(MODELS)[:3], max_selections=4) if compare else []
    mode = st.radio("Retrieval returns", ["Page", "Page ±1"], index=1,
                    help="Page±1 added coverage in E06 (0.93 vs 0.88) at 1.8x the tokens.")
    ag.expand = 1 if mode == "Page ±1" else 0
    st.divider()
    t = S.tot
    st.metric("Questions", t["q"]); st.metric("Tool calls", t["tools"])
    st.metric("Tokens in / out", f"{t['tin']:,} / {t['tout']:,}")
    st.metric("Est. cost (list price)", f"${t['cost']:.4f}")
    st.caption("Free tier is used, so the real cost is $0.")
    if st.button("New conversation"): reset_chat(); st.rerun()
    st.caption(f"Saved to projects/{S.project}/chats/{S.sid}.jsonl")

# ------------------------------------------------------------------ main
st.title(f"Emissions Analysis & Insights Agent: {S.project}")
cols = st.columns(len(QUICK) + 1)
clicked = None
for c, q in zip(cols, QUICK):
    if c.button(q, use_container_width=True): clicked = q
if cols[-1].button("Generate summary report", type="primary", use_container_width=True):
    if not avail: st.error("Upload data for this project first.")
    else:
        with st.spinner("Building report..."):
            f, page, st_ = build_report(ag, S.project)
        S.report = dict(page=page, name=f.name, project=S.project, stats=st_)
if S.get("report") and S.report["project"] == S.project:
    r_ = S.report
    st.success(f"Report saved to projects/{S.project}/reports/{r_['name']} ({r_['stats']['actions']} suggested actions)")
    st.download_button("Download report (HTML)", r_["page"], file_name=r_["name"], mime="text/html")
    st.iframe(r_["page"], height=900)   # all LLM text in the page is html-escaped by report.render

def show_answer(m, key):
    st.markdown(m["content"])
    show_sources(m["sources"], key)
    with st.expander("How I got this"):
        for tr in m["trace"]:
            st.code(f"{tr['tool']}({tr['args']})" + (f"  -> pages {tr['pages']}" if tr.get("pages") else ""))
        st.caption(m["stats"])


def stats_of(r):
    return f"{r['steps']} steps, {r['tokens_in']:,} in / {r['tokens_out']:,} out tokens, {r['latency']}s, ~${r['cost_usd']}"


for i, m in enumerate(S.msgs):
    if m.get("compare"):
        with st.chat_message("assistant"):
            st.caption("Model comparison (same question, no history)")
            rows = [dict(model=c["model"], seconds=c["latency"], tools=len([t for t in c["trace"] if t["tool"] not in ("citation_guard", "claim_check")]),
                         sources=len(c["sources"]), tokens_in=c["tokens_in"], tokens_out=c["tokens_out"], cost_usd=c["cost_usd"],
                         guard_fired=any(t["tool"] in ("citation_guard", "claim_check") for t in c["trace"])) for c in m["compare"]]
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
            for col, c in zip(st.columns(len(m["compare"])), m["compare"]):
                with col:
                    st.markdown(f"#### `{c['model']}`")
                    if c.get("error"): st.error(c["error"]); continue
                    with st.container(height=520): show_answer(c, f"{i}-{c['model']}")
        continue
    with st.chat_message(m["role"]):
        if m.get("model"): st.caption(m["model"])
        if m.get("trace") is not None: show_answer(m, i); continue
        st.markdown(m["content"])

prompt = st.chat_input("Ask about your emissions data or the GHG Protocol") or clicked
if prompt:
    if not avail:
        st.error("Upload data for this project first."); st.stop()
    with st.chat_message("user"): st.markdown(prompt)
    if compare and cmp_models:
        def run(m):
            try: return ag.ask(prompt, model=m)
            except Exception as e: return dict(model=m, error=str(e)[:300], answer="", trace=[], sources=[], tokens_in=0,
                                               tokens_out=0, latency=0, cost_usd=0, steps=0)
        with st.spinner(f"Asking {len(cmp_models)} models in parallel..."):
            with ThreadPoolExecutor(len(cmp_models)) as ex: res = list(ex.map(run, cmp_models))
        S.msgs.append(dict(role="user", content=prompt))
        S.msgs.append(dict(role="assistant", content="", compare=[r | dict(content=r["answer"], stats=stats_of(r)) for r in res]))
        t = S.tot; t["q"] += 1
        for r in res: t["tin"] += r["tokens_in"]; t["tout"] += r["tokens_out"]; t["cost"] += r["cost_usd"]
        log = et.PROJECTS / S.project / "chats"; log.mkdir(parents=True, exist_ok=True)
        with (log / f"{S.sid}.jsonl").open("a") as f:
            for r in res:
                f.write(json.dumps(dict(ts=time.strftime("%Y-%m-%dT%H:%M:%S"), session=S.sid, project=S.project, turn=t["q"], compare=True,
                                        question=prompt, answer=r["answer"], error=r.get("error"), trace=r["trace"],
                                        tokens_in=r["tokens_in"], tokens_out=r["tokens_out"], latency=r["latency"], cost_usd=r["cost_usd"],
                                        model=r["model"], prompt_version=PROMPT_VERSION), ensure_ascii=False, default=str) + "\n")
        st.rerun()
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            r = ag.ask(prompt, history=S.hist, model=S.model)
    S.hist = r["history"]
    stats = stats_of(r)
    S.msgs.append(dict(role="user", content=prompt))
    S.msgs.append(dict(role="assistant", content=r["answer"], trace=r["trace"], stats=stats, sources=r["sources"], model=S.model))
    t = S.tot; t["q"] += 1; t["tin"] += r["tokens_in"]; t["tout"] += r["tokens_out"]
    t["tools"] += sum(x["tool"] not in ("citation_guard", "claim_check") for x in r["trace"]); t["cost"] += r["cost_usd"]
    log = et.PROJECTS / S.project / "chats"; log.mkdir(parents=True, exist_ok=True)
    with (log / f"{S.sid}.jsonl").open("a") as f:
        f.write(json.dumps(dict(ts=time.strftime("%Y-%m-%dT%H:%M:%S"), session=S.sid, project=S.project, turn=t["q"],
                                question=prompt, answer=r["answer"], answer_raw=r.get("answer_raw"),
                                sources=[{k: s[k] for k in ("n", "id", "kind", "label")} for s in r["sources"]],
                                uncited_pages=r.get("uncited_pages"), trace=r["trace"], steps=r["steps"],
                                tokens_in=r["tokens_in"], tokens_out=r["tokens_out"], latency=r["latency"], cost_usd=r["cost_usd"],
                                model=S.model, prompt_version=PROMPT_VERSION, retrieval="page+-1" if ag.expand else "page"),
                           ensure_ascii=False, default=str) + "\n")
    st.rerun()
