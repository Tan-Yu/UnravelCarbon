"""Stage 2: end-to-end answers with Gemini. Compares return unit `page` vs `page+-1`
(hybrid retrieval, 300-word chunks, k=5). Resumable: results cached in build/cache/stage2.jsonl.
Usage: python3 -I build/stage2.py [--limit N] [--configs page,page+-1]
"""
import json, re, sys, time, hashlib
from pathlib import Path
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parent.parent
MODEL = "gemini-2.5-flash"
SYSTEM_PROMPT_VERSION = "v1"
CW, K, OVERLAP, RRF_K = 300, 5, 0.2, 60
SLEEP = 7.0   # free tier: ~10 requests/minute
CACHE = ROOT / "build/cache/stage2.jsonl"; CACHE.parent.mkdir(parents=True, exist_ok=True)

SYSTEM = """You are an emissions analysis assistant for sustainability professionals.
Answer ONLY from the provided GHG Protocol Corporate Standard (2004 edition) excerpts. Each excerpt is marked [p.N] (PDF page).
Rules:
- Cite the page for every claim, like [p.27]. Never invent pages, quotes or numbers.
- If the excerpts do not answer the question, reply exactly: "Cannot verify from the provided documents." and say briefly what is missing. The 2004 edition has no Scope 2 Guidance (2015) or Scope 3 Standard (2011).
- Distinguish requirements ("shall") from recommendations ("should").
- Be concise: at most 120 words."""

JUDGE = """You grade an answer from a RAG assistant. Return ONLY JSON.
Question: {q}
Expected key points:
{kp}
Reference evidence (exact quotes from the source):
{ev}
Assistant answer:
{ans}

Return JSON: {{"covered": [true/false for each expected key point, in order, true only if the answer states or clearly implies it],
"abstained": true if the answer says it cannot verify / the documents do not answer, else false,
"contradicts_evidence": true if the answer states something that contradicts the reference evidence, else false}}"""


def load_key():
    for l in open(ROOT / ".env"):
        if "=" in l and not l.strip().startswith("#"):
            k, v = l.split("=", 1)
            if k.strip().upper().startswith("GEMINI"):
                return v.strip().strip('"').strip("'")
    sys.exit("no GEMINI key in .env")


client = genai.Client(api_key=load_key())

def call(prompt, system=None, retries=6):
    for a in range(retries):
        try:
            r = client.models.generate_content(model=MODEL, contents=prompt, config=types.GenerateContentConfig(
                system_instruction=system, temperature=0, max_output_tokens=2048,
                thinking_config=types.ThinkingConfig(thinking_budget=0)))
            u = r.usage_metadata
            return r.text or "", u.prompt_token_count or 0, u.candidates_token_count or 0
        except Exception as e:
            msg = str(e)
            wait = 30 * (a + 1) if ("429" in msg or "503" in msg or "RESOURCE" in msg or "UNAVAILABLE" in msg) else 5
            print(f"  retry {a+1}: {msg[:90]!r}; wait {wait}s", flush=True); time.sleep(wait)
    raise RuntimeError("LLM call failed")


# ---------------- retrieval (same as notebook) ----------------
pages = {p["page"]: p["text"] for p in json.load(open(ROOT / "build/ghg-protocol-revised.plain.json"))}
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
emb_model = SentenceTransformer("BAAI/bge-small-en-v1.5")
EMB = emb_model.encode([c["text"] for c in chunks], normalize_embeddings=True, batch_size=32, show_progress_bar=False)

def retrieve(q, expand):
    d = EMB @ emb_model.encode([q], normalize_embeddings=True)[0]
    b = np.array(bm25.get_scores(tok(q)))
    rb = np.empty(len(b)); rb[np.argsort(-b)] = np.arange(len(b))
    rd = np.empty(len(b)); rd[np.argsort(-d)] = np.arange(len(b))
    s = 1 / (RRF_K + rb + 1) + 1 / (RRF_K + rd + 1)
    hit_pages = []
    for ci in np.argsort(-s)[:K]:
        for p in chunks[ci]["pages"]:
            if p not in hit_pages: hit_pages.append(p)
    j = 1 if expand == "page+-1" else 0
    ret = sorted({p + dlt for p in hit_pages for dlt in range(-j, j + 1) if 1 <= p + dlt <= len(pages)})
    return ret


def context(ret):
    return "\n\n".join(f"[p.{p}]\n{re.sub(chr(10)+'{3,}', chr(10)+chr(10), pages[p]).strip()}" for p in ret)


def cited_pages(ans):
    out = set()
    for m in re.finditer(r"\[(?:p\.?|pp\.?)\s*([\d,\s\-–and]+)\]", ans):
        for part in re.split(r"[,\s]+|and", m.group(1)):
            if re.fullmatch(r"\d+", part): out.add(int(part))
    for m in re.finditer(r"p\.\s*(\d+)", ans): out.add(int(m.group(1)))
    return out


def parse_json(t):
    m = re.search(r"\{.*\}", t, re.S)
    return json.loads(m.group(0)) if m else {}


def main():
    limit = None; cfgs = ["page", "page+-1"]
    a = sys.argv[1:]
    if "--limit" in a: limit = int(a[a.index("--limit") + 1])
    if "--configs" in a: cfgs = a[a.index("--configs") + 1].split(",")
    E = [json.loads(l) for l in open(ROOT / "build/eval_queries.jsonl")]
    if limit: E = E[:limit]
    done = {}
    if CACHE.exists():
        for l in CACHE.read_text().splitlines():
            r = json.loads(l); done[(r["query"], r["config"], r["model"], r["prompt_version"])] = r
    for i, e in enumerate(E):
        for cfg in cfgs:
            key = (e["query"], cfg, MODEL, SYSTEM_PROMPT_VERSION)
            if key in done: continue
            ret = retrieve(e["query"], cfg)
            ctx = context(ret)
            t0 = time.time()
            ans, tin, tout = call(f"Excerpts:\n{ctx}\n\nQuestion: {e['query']}", system=SYSTEM)
            lat = time.time() - t0; time.sleep(SLEEP)
            kp = "\n".join(f"{n+1}. {x}" for n, x in enumerate(e["key_points"]))
            ev = "\n".join(f'p.{pg}: "{q}"' for pg, q in e["evidence"].items()) or "(none: the source does not cover this)"
            jtxt, jin, jout = call(JUDGE.format(q=e["query"], kp=kp, ev=ev, ans=ans))
            time.sleep(SLEEP)
            try: j = parse_json(jtxt)
            except Exception: j = {}
            row = dict(query=e["query"], type=e["type"], split=e["split"], config=cfg, model=MODEL,
                       prompt_version=SYSTEM_PROMPT_VERSION, returned_pages=ret, ctx_tokens_in=tin, tokens_out=tout,
                       latency=round(lat, 2), answer=ans, cited=sorted(cited_pages(ans)), judge=j,
                       gold=e["gold_pages"], also=e["also_relevant"])
            with CACHE.open("a") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")
            done[key] = row
            print(f"[{i+1}/{len(E)}] {cfg:8s} in={tin:6d} out={tout:4d} cov={j.get('covered')} abst={j.get('abstained')} | {e['query'][:55]}", flush=True)


if __name__ == "__main__":
    main()
