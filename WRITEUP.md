# Write-up: Emissions Analysis & Insights Agent

## Solution
A single Gemini agent (`gemini-4-hydrogen`, temperature 0) runs a manual tool loop with three kinds of tools:
- **pandas tools** for the CSVs: they compute the numbers, so the model never does arithmetic;
- **GHG Protocol retrieval**;
- **a peer-comparison tool**.

Every number is cited as a data source and every rule as a PDF page. The UI turns these into clickable chips that show the underlying table or page text. The design principle is that **the model writes prose, and code owns the facts.**

## Architecture
- **Data.** Each company has its own folder in `projects/<company>/`. Uploads are schema-validated and hot-reloaded, using a cache keyed on file modification time. Each data tool result carries that project's open data-quality findings (`data_caveats`), so answers state the caveats inline.
- **Knowledge.**
  - The Protocol PDF is extracted with plain `pdftotext`, which was chosen over `-layout` in E01.
  - It is split into 300-word chunks and searched with hybrid BM25 + bge-small, merged with reciprocal rank fusion. The top 5 hits are returned with their neighbouring pages.
  - Compound questions are split into one query each.
- **Peers.** Facts are hand-curated from both peer PDFs. A build script asserts that each fact's quote appears on its cited page. Shopify's figures come from a chart, so RAG over that PDF would not be reliable.
- **Guards.**
  1. A citation guard retries once if the answer cites a page that was never retrieved.
  2. A claim check verifies every "shall/required/must" sentence against the cited page, with one rewrite if unsupported.
  3. Internal ids are stripped from answers.
- **Model choice in the UI.** The user can pick the model, or compare up to four Gemini models side by side on the same question, with latency, tokens, cost and whether a guard fired.
- **Data-status flags** in the sidebar are each tagged as a GHG Protocol requirement (with the PDF page and quote, shown on hover) or as best practice. The page references were checked by hand.
- **Report.** Code collects the figures, the LLM only picks hotspot ids and writes actions, and code attaches the numbers. The page is self-contained HTML/SVG.

## Data observations
- Each scope file has 3 flagged findings, and all arithmetic recomputes.
- Steam is about 84% of Scope 2. The Protocol defines Scope 2 around purchased electricity (p.27), while the p.35 footnote extends it. This tension is surfaced rather than hidden.
- Supplier and category fields have gaps, so supplier prioritisation carries explicit data caveats.

## Evaluation
- **Retrieval (E02–E07):**
  - 49 queries, each with a quote-verified gold page, including 6 negatives.
  - Hybrid retrieval had the best hit rate (0.90).
  - Returning page±1 raised answer key-point coverage from 0.88 to 0.93 at 1.8× the tokens.
- **Agent (E10–E13):**
  - The six brief questions were rerun for every prompt and model version and saved side by side in `results/`.
  - Moving to `gemini-4-hydrogen` fixed the two failures that prompt changes alone did not: Core 1's calculation method and Core 2's verdict consistency.
- **Scored agent eval (E16, `eval_agent.py`):**
  - Each brief question has deterministic checks: required facts, required tool calls, cited pages, and no leaked ids or uncited pages. Ground truth comes from the data tools and hand-checked pages, never from an LLM.
  - With 3 fresh runs per question, 114 of 114 checks passed with no variance between runs. The only first-pass failure was a bug in the grader, not in the agent.
  - This proves facts and grounding are present. It does not grade prose quality.
- **Ledger.** Every experiment, with its caveats, is in `EXPERIMENTS.md`.

## Scaling
- **More companies:** swap the folder-per-project store for Postgres or DuckDB plus object storage, and keep the same tool interface.
- **More documents:** move to a vector database with page metadata, and keep the same eval set as a regression test.
- **Operations:** chats are already logged as JSONL with model, prompt version, tokens and cost, which is the raw material for monitoring and for growing the eval set.
- **Concurrency:** the active project is a module global, so the app is single-user. Production needs per-request project context.

## Limits and future improvements
- **Evaluation.** The rubric checks facts, not writing quality. Next: a human-graded rubric for usefulness and clarity, a hand-check of the E06 LLM judge (which grades its own model's answers), and a larger question set grown from logged chats. Run the same rubric across models from the compare view, so model choice is decided by score.
- **Knowledge.** Only the 2004 Corporate Standard is loaded. Adding the 2015 Scope 2 Guidance (market- vs location-based reporting) and the Scope 3 Standard would settle the steam and dual-reporting questions properly.
- **Unanswerable questions.** Questions with no match in the knowledge base (for example "15 Scope 3 categories") score as high as real ones. A sufficiency check before answering would let the agent say "not in the source".
- **Peers.** Peer facts are hand-curated. An extraction pipeline with the same quote assertions would scale to many peers, and revenue data would allow intensity comparisons.
- **Production.** Per-request project context instead of a module global, a real database, authentication, and monitoring dashboards built from the JSONL chat logs.
- **Advice.** Reduction actions and effort ratings are model judgement. A domain expert review, and estimated reduction potential per action, would make the report decision-ready.
