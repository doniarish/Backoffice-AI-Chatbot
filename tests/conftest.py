"""
tests/conftest.py
------------------
Shared pytest fixtures for the Backoffice AI Chatbot demo test suite.
"""

import pytest
from pathlib import Path


@pytest.fixture(scope="session")
def mock_db_path(tmp_path_factory):
    """Create a temporary SQLite test database for the session."""
    tmp = tmp_path_factory.mktemp("testdb") / "test_demo.db"
    from demo.mock_database import create_database
    create_database(tmp)
    return tmp


@pytest.fixture
def sample_documents():
    """Return all sample FAQ documents."""
    from app.rag.documents import get_all_documents
    return get_all_documents()


@pytest.fixture
def built_rag_pipeline():
    """Return a RAG pipeline with FAISS index already built."""
    from app.rag.pipeline import RAGPipeline
    pipeline = RAGPipeline()
    pipeline.build_index()
    return pipeline

