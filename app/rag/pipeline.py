"""
app/rag/pipeline.py
--------------------
Demonstration RAG (Retrieval-Augmented Generation) pipeline using:
  - sentence-transformers  → local embeddings (no API key required)
  - FAISS                  → local in-memory vector store
  - LangChain              → document loading, splitting, retrieval interface

Pipeline stages:
  1. Document ingestion   — load FAQ documents from documents.py
  2. Chunking             — split long answers into overlapping chunks
  3. Embedding            — encode text using sentence-transformers
  4. Vector storage       — index in FAISS
  5. Similarity retrieval — find top-k relevant chunks for a query
  6. Context assembly     — format retrieved chunks into LLM-readable context

Usage:
    from app.rag.pipeline import rag_pipeline

    context = rag_pipeline.retrieve("What are my reward points?", k=3)
    print(context)
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
DEFAULT_MODEL = "all-MiniLM-L6-v2"   # Small, fast, runs locally — no API key
CHUNK_SIZE = 300                       # characters per chunk
CHUNK_OVERLAP = 50                     # overlap between chunks
DEFAULT_K = 3                          # top-k results to retrieve
SCORE_THRESHOLD = 0.30                 # minimum cosine similarity to include


class RAGPipeline:
    """
    Local RAG pipeline backed by FAISS and sentence-transformers.

    The index is built lazily on first call (or explicitly via `build_index()`).
    Re-building is fast (< 1 second) for the demo document set.
    """

    def __init__(self, embedding_model: str = DEFAULT_MODEL):
        self._embedding_model_name = embedding_model
        self._embedder = None           # sentence_transformers.SentenceTransformer
        self._index = None              # faiss.IndexFlatIP
        self._chunks: List[dict] = []   # raw chunk store: {text, doc_id, category}
        self._built = False

    # ── Private helpers ──────────────────────────────────────────────────────

    def _load_embedder(self):
        """Lazily load the SentenceTransformer model."""
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer(self._embedding_model_name)
                logger.info("[RAG] Loaded embedding model: %s", self._embedding_model_name)
            except ImportError as exc:
                raise ImportError(
                    "sentence-transformers is required for the RAG pipeline. "
                    "Run: pip install sentence-transformers"
                ) from exc
        return self._embedder

    def _embed(self, texts: List[str]):
        """Embed a list of texts and return a numpy float32 array."""
        embedder = self._load_embedder()
        return embedder.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
        """
        Split text into overlapping character-level chunks.
        Simple but effective for short FAQ answers.
        """
        if len(text) <= chunk_size:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

    # ── Public API ───────────────────────────────────────────────────────────

    def build_index(self) -> None:
        """
        Build the FAISS index from the sample FAQ documents.

        Steps:
          1. Load documents from documents.py
          2. Chunk each Q+A pair
          3. Embed all chunks
          4. Insert embeddings into a FAISS IndexFlatIP (inner product = cosine for normalized vecs)
        """
        try:
            import faiss
            import numpy as np
        except ImportError as exc:
            raise ImportError(
                "faiss-cpu is required. Run: pip install faiss-cpu"
            ) from exc

        from app.rag.documents import get_all_documents
        documents = get_all_documents()

        self._chunks = []
        texts_to_embed = []

        for doc in documents:
            # Combine question + answer for richer context
            combined = f"Q: {doc['question']}\nA: {doc['answer']}"
            for chunk in self._chunk_text(combined):
                self._chunks.append({
                    "text": chunk,
                    "doc_id": doc["id"],
                    "question": doc["question"],
                    "answer": doc["answer"],
                    "category": doc["category"],
                })
                texts_to_embed.append(chunk)

        logger.info("[RAG] Embedding %d chunks from %d documents...", len(texts_to_embed), len(documents))
        embeddings = self._embed(texts_to_embed).astype("float32")

        dim = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dim)   # Inner product on normalized vecs = cosine similarity
        self._index.add(embeddings)
        self._built = True
        logger.info("[RAG] FAISS index built. %d vectors, dim=%d.", self._index.ntotal, dim)

    def _ensure_built(self) -> None:
        """Build the index if it hasn't been built yet."""
        if not self._built:
            self.build_index()

    def retrieve(self, query: str, k: int = DEFAULT_K) -> List[dict]:
        """
        Retrieve the top-k most relevant chunks for a query.

        Args:
            query : user question string
            k     : number of results to return

        Returns:
            List of dicts, each containing:
              - text     : the matching chunk text
              - doc_id   : source document ID
              - question : original document question
              - answer   : original document full answer
              - category : topic category
              - score    : cosine similarity score (0–1)
        """
        self._ensure_built()
        import numpy as np

        query_vec = self._embed([query]).astype("float32")
        scores, indices = self._index.search(query_vec, k * 2)   # Retrieve extra, then filter

        results = []
        seen_doc_ids = set()

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or float(score) < SCORE_THRESHOLD:
                continue
            chunk = self._chunks[idx]
            doc_id = chunk["doc_id"]

            # Deduplicate: return at most one chunk per source document
            if doc_id in seen_doc_ids:
                continue
            seen_doc_ids.add(doc_id)

            results.append({**chunk, "score": float(score)})
            if len(results) >= k:
                break

        logger.debug("[RAG] query=%.40r → %d results", query, len(results))
        return results

    def retrieve_context(self, query: str, k: int = DEFAULT_K) -> str:
        """
        Retrieve and format top-k results as a single context string for the LLM.

        Returns:
            Formatted string: "Q: ...\nA: ...\n\nQ: ...\nA: ..." or
            "No relevant information found." if no results pass the threshold.
        """
        results = self.retrieve(query, k=k)
        if not results:
            return "No relevant information found."

        parts = [
            f"Q: {r['question']}\nA: {r['answer']}"
            for r in results
        ]
        return "\n\n".join(parts)

    def get_confidence_score(self, query: str) -> float:
        """
        Return a simple confidence score (0–1) for whether the RAG index
        contains relevant information for the given query.

        Used by the LangGraph node to decide whether to answer via RAG
        or fall back to the LLM directly.
        """
        results = self.retrieve(query, k=1)
        if not results:
            return 0.0
        return results[0]["score"]


# Singleton — import and use throughout the app
rag_pipeline = RAGPipeline()

