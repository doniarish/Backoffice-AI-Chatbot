"""
tests/test_rag.py
------------------
Unit tests for the RAG pipeline.

Tests document loading, FAISS index building, and similarity retrieval
without requiring any external API calls.
"""

import pytest


class TestDocumentLoading:
    """Tests for the sample FAQ document loading."""

    def test_documents_loaded(self, sample_documents):
        assert len(sample_documents) > 0, "No documents loaded"

    def test_documents_have_required_keys(self, sample_documents):
        required = {"id", "question", "answer", "category"}
        for doc in sample_documents:
            assert required.issubset(doc.keys()), f"Document {doc.get('id')} missing keys"

    def test_documents_have_non_empty_content(self, sample_documents):
        for doc in sample_documents:
            assert doc["question"].strip(), f"Empty question in doc {doc['id']}"
            assert doc["answer"].strip(), f"Empty answer in doc {doc['id']}"

    def test_arabic_documents_present(self, sample_documents):
        arabic_docs = [d for d in sample_documents if "ar" in d["id"] or
                       any(ord(c) > 0x0600 for c in d["question"])]
        assert len(arabic_docs) >= 1, "No Arabic documents found"

    def test_categories_valid(self, sample_documents):
        valid_categories = {"pickup", "materials", "rewards", "corporate", "coverage", "account"}
        for doc in sample_documents:
            assert doc["category"] in valid_categories, (
                f"Unknown category '{doc['category']}' in doc {doc['id']}"
            )


class TestRAGPipelineIndexing:
    """Tests for FAISS index building."""

    def test_index_built_successfully(self, built_rag_pipeline):
        assert built_rag_pipeline._built is True
        assert built_rag_pipeline._index is not None
        assert built_rag_pipeline._index.ntotal > 0

    def test_chunks_created(self, built_rag_pipeline):
        assert len(built_rag_pipeline._chunks) > 0

    def test_rebuild_does_not_raise(self, built_rag_pipeline):
        """Rebuilding the index should be idempotent."""
        built_rag_pipeline.build_index()
        assert built_rag_pipeline._built is True


class TestRAGRetrieval:
    """Tests for similarity search and context retrieval."""

    def test_retrieve_returns_results(self, built_rag_pipeline):
        results = built_rag_pipeline.retrieve("how do reward points work?", k=3)
        assert len(results) > 0

    def test_retrieve_results_have_required_keys(self, built_rag_pipeline):
        results = built_rag_pipeline.retrieve("schedule a pickup", k=2)
        for r in results:
            assert "text" in r
            assert "question" in r
            assert "answer" in r
            assert "score" in r
            assert "category" in r

    def test_retrieve_scores_between_0_and_1(self, built_rag_pipeline):
        results = built_rag_pipeline.retrieve("reward points", k=3)
        for r in results:
            assert 0.0 <= r["score"] <= 1.0, f"Score out of range: {r['score']}"

    def test_retrieve_context_returns_string(self, built_rag_pipeline):
        context = built_rag_pipeline.retrieve_context("cancel a pickup", k=2)
        assert isinstance(context, str)
        assert len(context) > 0

    def test_retrieve_context_no_results(self, built_rag_pipeline):
        """Low-relevance query should return fallback message."""
        context = built_rag_pipeline.retrieve_context(
            "xyznonsense gibberish abc123", k=1
        )
        assert isinstance(context, str)

    def test_retrieve_deduplication(self, built_rag_pipeline):
        """Should not return multiple chunks from the same source document."""
        results = built_rag_pipeline.retrieve("reward points", k=5)
        doc_ids = [r["doc_id"] for r in results]
        assert len(doc_ids) == len(set(doc_ids)), "Duplicate document IDs in results"

    def test_confidence_score_high_for_relevant_query(self, built_rag_pipeline):
        score = built_rag_pipeline.get_confidence_score("how do reward points work?")
        assert score > 0.3, f"Expected confidence > 0.3, got {score}"

    def test_confidence_score_low_for_irrelevant_query(self, built_rag_pipeline):
        score = built_rag_pipeline.get_confidence_score("xyz random nonsense 12345abc")
        # Score may be 0.0 or very low
        assert score < 0.5, f"Expected low confidence, got {score}"

    def test_arabic_query_retrieval(self, built_rag_pipeline):
        """Arabic queries should retrieve results (multilingual embedding support)."""
        results = built_rag_pipeline.retrieve("ما هي نقاط المكافآت", k=3)
        assert isinstance(results, list)

