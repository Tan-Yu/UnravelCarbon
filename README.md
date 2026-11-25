# Emissions Analysis & Insights Agent

A chat agent that answers questions about a company's Scope 1–3 emissions data and the GHG Protocol Corporate Standard. It cites every number and every rule. It also builds an HTML summary report with reduction advice.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "GEMINI_API_KEY=your-key" > .env
streamlit run app.py          # http://localhost:8501
```

The first run downloads `bge-small-en-v1.5` (~130 MB) and caches the embeddings in `build/cache/`.

## What it does

| Brief requirement | Where |
|---|---|
| Natural-language data queries | `emissions_tools.py` (totals, breakdowns, top suppliers, quality report), called by Gemini |
| GHG Protocol questions (RAG) | `rag.py` (hybrid BM25 + bge-small, 300-word chunks, k=5, page±1) |
| Data-quality assessment | `quality_report`: each finding is marked as a Protocol requirement (cited) or best practice |
| Peer comparison | `peers.py`: page-verified facts from both peer PDFs, plus comparability caveats |
| Summary report | "Generate summary report" button, or `report.py`: an HTML page with charts, a priority matrix and actions |

## Layout

```
agent.py            tool-calling loop, citation numbering, citation guard, claim check
app.py              Streamlit UI: projects, uploads, clickable sources, saved chats
emissions_tools.py  pandas tools over projects/<company>/scope{1,2,3}.csv
rag.py / peers.py   Protocol retrieval / peer facts
report.py           HTML summary report
projects/<company>/ scope CSVs, chats/*.jsonl, reports/*.html (one folder per company)
results/            the six test questions answered by every agent version + COMPARISON.md
EXPERIMENTS.md      ledger of every experiment (E01–E15)
build/              extraction, eval sets and experiment scripts
```

## Reproduce

```bash
python3 run_tests.py                          # six brief questions -> build/cache/test_questions.md
python3 build/stage2.py                       # retrieval answer-quality experiment (E06)
python3 build/make_peers.py                   # rebuild peers/peers.json (asserts every fact against its page)
for f in tests/test_*.py; do python3 $f; done # unit tests
```

To add a company, use **New project** in the sidebar and upload its CSVs. The upload is validated and loaded without a restart.

See [WRITEUP.md](WRITEUP.md) for the design, the evaluation and the known limits.
