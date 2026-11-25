"""GHG Protocol retrieval: hybrid (BM25 + bge-small, RRF), 300-word chunks, k=5.
Same settings as build/stage2.py (E06). Embeddings are cached in build/cache/.
"""
import json, re
from pathlib import Path
import numpy as np
from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parent
CW, K, OVERLAP, RRF_K = 300, 5, 0.2, 60
EMB_MODEL = "BAAI/bge-small-en-v1.5"
QP = "Represent this sentence for searching relevant passages: "
_tok = lambda s: re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", s.lower())


class GHGIndex:
    def __init__(self, pages_json=ROOT / "build/ghg-protocol-revised.plain.json"):
        self.pages = {p["page"]: p["text"] for p in json.load(open(pages_json))}
        words, wpage = [], []
        for pg, t in self.pages.items():
            w = t.split(); words += w; wpage += [pg] * len(w)
        step = int(CW * (1 - OVERLAP)); self.chunks = []
        for s in range(0, len(words), step):
            e = min(len(words), s + CW)
            self.chunks.append(dict(pages=sorted(set(wpage[s:e])), text=" ".join(words[s:e])))
            if e == len(words): break
        self.bm25 = BM25Okapi([_tok(c["text"]) for c in self.chunks])
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(EMB_MODEL)
        cache = ROOT / "build/cache/emb_bge_small_300.npy"
        if cache.exists() and np.load(cache).shape[0] == len(self.chunks):
            self.emb = np.load(cache)
        else:
            self.emb = self.model.encode([c["text"] for c in self.chunks], normalize_embeddings=True,
                                         batch_size=32, show_progress_bar=False)
            cache.parent.mkdir(exist_ok=True); np.save(cache, self.emb)

    def search(self, query: str, expand: int = 1, k: int = K) -> dict:
        """expand=0 returns hit pages only; expand=1 adds the neighbouring pages (page+-1)."""
        d = self.emb @ self.model.encode([QP + query], normalize_embeddings=True)[0]
        b = np.array(self.bm25.get_scores(_tok(query)))
        rb = np.empty(len(b)); rb[np.argsort(-b)] = np.arange(len(b))
        rd = np.empty(len(b)); rd[np.argsort(-d)] = np.arange(len(b))
        s = 1 / (RRF_K + rb + 1) + 1 / (RRF_K + rd + 1)
        hits = []
        for ci in np.argsort(-s)[:k]:
            for p in self.chunks[ci]["pages"]:
                if p not in hits: hits.append(p)
        ret = sorted({p + dl for p in hits for dl in range(-expand, expand + 1) if 1 <= p + dl <= len(self.pages)})
        text = "\n\n".join(f"[p.{p}]\n{re.sub(chr(10) + '{3,}', chr(10) * 2, self.pages[p]).strip()}" for p in ret)
        return dict(hit_pages=hits, returned_pages=ret, text=text, words=len(text.split()))
