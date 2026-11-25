"""Streamlit chat UI. Run: streamlit run app.py"""
import streamlit as st
import emissions_tools as et
from agent import Agent

st.set_page_config(page_title="Emissions Analysis Agent", layout="wide")


@st.cache_resource
def get_agent():
    return Agent()


ag = get_agent()
S = st.session_state
S.setdefault("msgs", []); S.setdefault("hist", []); S.setdefault("tot", dict(q=0, tin=0, tout=0, tools=0, cost=0.0, lat=0.0))

QUICK = ["Which Scope 3 category has the highest emissions?",
         "What share of Scope 2 comes from steam, and does the GHG Protocol count steam as Scope 2?",
         "Is Scope 3 reporting mandatory under the GHG Protocol?",
         "Which suppliers should we prioritise for engagement?"]
REPORT = ("Generate a summary report: (1) totals by scope with shares, (2) the top hotspots in Scope 1, 2 and 3, "
          "(3) a data-quality assessment where each point is labelled Protocol requirement (cited) or Best practice, "
          "(4) knowledge-base gaps. Suggest fixes; do not rewrite the data.")

with st.sidebar:
    st.header("Data status")
    for f, s in et.load_status().items():
        st.markdown(f"**{f}**: {s['rows']} rows, {s['flags']} flags, arithmetic {'OK' if s['arithmetic_ok'] else 'MISMATCH'}")
    st.caption("Knowledge base: GHG Protocol Corporate Standard (2004), 116 pages. Peer reports: not loaded.")
    st.divider()
    mode = st.radio("Retrieval returns", ["Page", "Page ±1"], index=1,
                    help="Page±1 added coverage in E06 (0.93 vs 0.88) at 1.8x the tokens.")
    ag.expand = 1 if mode == "Page ±1" else 0
    st.divider()
    t = S.tot
    st.metric("Questions", t["q"]); st.metric("Tool calls", t["tools"])
    st.metric("Tokens in / out", f"{t['tin']:,} / {t['tout']:,}")
    st.metric("Est. cost (list price)", f"${t['cost']:.4f}")
    st.caption("Free tier is used, so the real cost is $0.")
    if st.button("Clear chat"):
        S.msgs, S.hist = [], []; st.rerun()

st.title("Emissions Analysis & Insights Agent")
cols = st.columns(len(QUICK) + 1)
clicked = None
for c, q in zip(cols, QUICK):
    if c.button(q, use_container_width=True): clicked = q
if cols[-1].button("Generate summary report", type="primary", use_container_width=True): clicked = REPORT

for m in S.msgs:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("trace") is not None:
            with st.expander("How I got this"):
                for tr in m["trace"]:
                    st.code(f"{tr['tool']}({tr['args']})" + (f"  -> pages {tr['pages']}" if tr.get("pages") else ""))
                st.caption(m["stats"])

prompt = st.chat_input("Ask about your emissions data or the GHG Protocol") or clicked
if prompt:
    S.msgs.append(dict(role="user", content=prompt))
    with st.chat_message("user"): st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            r = ag.ask(prompt, history=S.hist)
        st.markdown(r["answer"])
        if r.get("uncited_pages"):
            st.warning(f"Pages {r['uncited_pages']} were cited but never retrieved; treat those citations as unverified.")
    S.hist = r["history"]
    stats = f"{r['steps']} steps, {r['tokens_in']:,} in / {r['tokens_out']:,} out tokens, {r['latency']}s, ~${r['cost_usd']}"
    S.msgs.append(dict(role="assistant", content=r["answer"], trace=r["trace"], stats=stats))
    t = S.tot; t["q"] += 1; t["tin"] += r["tokens_in"]; t["tout"] += r["tokens_out"]
    t["tools"] += sum(x["tool"] != "citation_guard" for x in r["trace"]); t["cost"] += r["cost_usd"]
    st.rerun()
