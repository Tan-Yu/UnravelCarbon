"""E07: compare embedding models on stage-1 retrieval (no answering LLM).
Usage: python3 -I build/embed_compare.py MODEL [MODEL ...]
  MODEL = a sentence-transformers name (e.g. BAAI/bge-small-en-v1.5) or 'gemini:gemini-embedding-001'
Appends rows to build/embed_compare.csv (never overwrites earlier rows).
"""
import json, re, sys, time, csv, itertools
from pathlib import Path
import numpy as np
from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parent.parent
CW, OVERLAP, RRF_K = 300, 0.2, 60
pages = {p["page"]: p["text"] for p in json.load(open(ROOT / "build/ghg-protocol-revised.plain.json"))}
E = [json.loads(l) for l in open(ROOT / "build/eval_queries.jsonl")]
POS = [e for e in E if e["type"] != "negative" and e["gold_pages"]]

words, wpage = [], []
for pg, t in pages.items():
    w = t.split(); words += w; wpage += [pg] * len(w)
step = int(CW * (1 - OVERLAP)); chunks = []
for s in range(0, len(words), step):
    e = min(len(words), s + CW)
    chunks.append(dict(pages=sorted(set(wpage[s:e])), text=" ".join(words[s:e])))
    if e == len(words): break
tok = lambda s: re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", s.lower())
bm25 = BM25Okapi([tok(c["text"]) for c in chunks])
BM = {e["query"]: np.array(bm25.get_scores(tok(e["query"]))) for e in POS}


def get_embedder(name):
    if name.startswith("gemini:"):
        from google import genai
        from google.genai import types
        key = next(l.split("=", 1)[1].strip().strip("\"'") for l in open(ROOT / ".env")
                   if "=" in l and l.split("=")[0].strip().upper().startswith("GEMINI"))
        c = genai.Client(api_key=key); mid = name.split(":", 1)[1]
        def enc(texts, kind):
            out = []
            for i in range(0, len(texts), 50):
                for a in range(6):
                    try:
                        r = c.models.embed_content(model=mid, contents=texts[i:i + 50], config=types.EmbedContentConfig(
                            task_type="RETRIEVAL_DOCUMENT" if kind == "doc" else "RETRIEVAL_QUERY"))
                        out += [x.values for x in r.embeddings]; break
                    except Exception as ex:
                        print("  retry", str(ex)[:80], flush=True); time.sleep(20 * (a + 1))
                time.sleep(1)
            v = np.array(out, dtype=np.float32); return v / np.linalg.norm(v, axis=1, keepdims=True)
        return enc
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(name)
    qp = "Represent this sentence for searching relevant passages: " if "bge" in name and "en-v1.5" in name else ""
    qp = "query: " if "e5" in name else qp
    dp = "passage: " if "e5" in name else ""
    return lambda texts, kind: m.encode([(dp if kind == "doc" else qp) + t for t in texts], normalize_embeddings=True,
                                       batch_size=32, show_progress_bar=False)


def run(name):
    enc = get_embedder(name)
    t0 = time.time(); D = enc([c["text"] for c in chunks], "doc"); idx_secs = time.time() - t0
    Q = enc([e["query"] for e in POS], "query")
    rows = []
    for retr, k, expand in itertools.product(["dense", "hybrid"], [3, 5], ["page", "page+-1"]):
        recs = []
        for qi, e in enumerate(POS):
            d = D @ Q[qi]
            if retr == "dense": s = d
            else:
                b = BM[e["query"]]
                rb = np.empty(len(b)); rb[np.argsort(-b)] = np.arange(len(b))
                rd = np.empty(len(b)); rd[np.argsort(-d)] = np.arange(len(b))
                s = 1 / (RRF_K + rb + 1) + 1 / (RRF_K + rd + 1)
            ranked = []
            for ci in np.argsort(-s)[:k]:
                for p in chunks[ci]["pages"]:
                    if p not in ranked: ranked.append(p)
            j = 1 if expand == "page+-1" else 0
            got = {p + dl for p in ranked for dl in range(-j, j + 1) if 1 <= p + dl <= len(pages)}
            gold = set(e["gold_pages"]); rel = gold | set(e["also_relevant"])
            recs.append((len(gold & got) / len(gold), float(bool(gold & got)),
                         next((1 / (i + 1) for i, p in enumerate(ranked) if p in gold), 0.0),
                         len(rel & got) / max(1, len(got)), sum(len(pages[p].split()) for p in got) * 1.3))
        r = np.mean(recs, axis=0)
        rows.append(dict(model=name, dim=D.shape[1], index_secs=round(idx_secs, 1), retriever=retr, k=k, expand=expand,
                         n_queries=len(POS), recall=round(r[0], 3), hit=round(r[1], 3), mrr=round(r[2], 3),
                         precision=round(r[3], 3), ctx_tokens=int(r[4])))
    return rows


if __name__ == "__main__":
    out = ROOT / "build/embed_compare.csv"; new = not out.exists(); allrows = []
    for name in sys.argv[1:]:
        print("model:", name, flush=True); allrows += run(name)
    with out.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(allrows[0]));
        if new: w.writeheader()
        w.writerows(allrows)
    import pandas as pd
    df = pd.DataFrame(allrows); pd.set_option("display.width", 200)
    print(df.to_string(index=False))
