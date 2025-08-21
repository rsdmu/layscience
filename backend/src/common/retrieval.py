from rank_bm25 import BM25Okapi
from typing import List
import re
from .models import Chunk

def normalize(s: str):
    return re.findall(r"[a-zA-Z0-9]+", s.lower())

def bm25_topk(chunks: List[Chunk], query: str, k: int = 5) -> List[Chunk]:
    corpus = [normalize(c.text) for c in chunks]
    bm25 = BM25Okapi(corpus)
    q = normalize(query)
    scores = bm25.get_scores(q)
    pairs = sorted(list(enumerate(scores)), key=lambda x: x[1], reverse=True)[:k]
    return [chunks[i] for i,_ in pairs]
