"""Freshness-aware hybrid retrieval: Qdrant dense + BM25 sparse + RRF.

Dense embeddings use a deterministic hashing vectorizer so the graph runs in CI
with no model download; in production this is swapped for BAAI/bge-small-en (the
`Embedder` protocol is the seam). Qdrant runs in-memory (`:memory:`) — real
Qdrant, no server. Reciprocal rank fusion blends the two rankings; documents from
the last 15 minutes get a 3x weight so current operational context wins over
stale reference docs.
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from rank_bm25 import BM25Okapi

_TOKEN = re.compile(r"[a-z0-9]+")

FRESHNESS_WINDOW_MINUTES = 15
FRESHNESS_WEIGHT = 3.0
RRF_K = 60


def _tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class HashingEmbedder:
    """Deterministic bag-of-words hashing embedder (stand-in for bge-small)."""

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = np.zeros(self.dim, dtype=np.float32)
        for tok in _tokenize(text):
            vec[hash(tok) % self.dim] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec.tolist()


class HybridRetriever:
    def __init__(self, docs: list[dict[str, Any]], embedder: HashingEmbedder | None = None) -> None:
        self.docs = docs
        self.embedder = embedder or HashingEmbedder()
        self._client = QdrantClient(location=":memory:")
        self._collection = "knowledge"
        self._client.create_collection(
            self._collection,
            vectors_config=VectorParams(size=self.embedder.dim, distance=Distance.COSINE),
        )
        self._client.upsert(
            self._collection,
            points=[
                PointStruct(id=i, vector=self.embedder.embed(d["text"]), payload=d)
                for i, d in enumerate(docs)
            ],
        )
        self._bm25 = BM25Okapi([_tokenize(d["text"]) for d in docs])

    def _dense_ranking(self, query: str) -> list[int]:
        resp = self._client.query_points(
            self._collection,
            query=self.embedder.embed(query),
            limit=len(self.docs),
        )
        return [p.id for p in resp.points]

    def _sparse_ranking(self, query: str) -> list[int]:
        scores = self._bm25.get_scores(_tokenize(query))
        return list(np.argsort(scores)[::-1])

    def search(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        """Return the top-k documents by freshness-weighted RRF."""
        rankings = [self._dense_ranking(query), self._sparse_ranking(query)]

        rrf: dict[int, float] = {}
        for ranking in rankings:
            for rank, doc_id in enumerate(ranking):
                rrf[doc_id] = rrf.get(doc_id, 0.0) + 1.0 / (RRF_K + rank)

        # Freshness weighting: recent operational events get a 3x boost.
        scored = []
        for doc_id, score in rrf.items():
            doc = self.docs[doc_id]
            if doc.get("recency_minutes", 1e9) <= FRESHNESS_WINDOW_MINUTES:
                score *= FRESHNESS_WEIGHT
            scored.append((score, doc_id))

        scored.sort(reverse=True)
        return [
            {**self.docs[doc_id], "retrieval_score": round(score, 5)}
            for score, doc_id in scored[:k]
        ]
