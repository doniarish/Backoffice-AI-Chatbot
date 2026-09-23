# Backoffice AI Chatbot — Demo

A sanitized, open-source portfolio demonstration of a modern **Backoffice AI Chatbot** architecture — built with LangGraph, RAG, Text-to-SQL, tool routing, Redis session context, and multilingual (English + Arabic) query handling.

> **Disclaimer**: This repository is an independently implemented, sanitized demonstration inspired by general AI application architecture patterns. It does **not** contain proprietary source code, credentials, production data, or confidential company information.

---

## Architecture

```
User Query (EN / AR)
      │
      ▼
┌─────────────┐
│  FastAPI    │  ← /chat, /health, /session
└──────┬──────┘
       │  session context  ←→  ┌─────────────────┐
       │                       │  Session Store   │
       ▼                       │  Redis / Memory  │
┌──────────────────────────────┴──────┐
│      LangGraph Orchestrator         │
│                                     │
│  ┌────────────┐                     │
│  │  classify  │ Language + Intent   │
│  └─────┬──────┘  + Entities         │
│        │                            │
│   ┌────▼─────────────────────┐      │
│   │     Route by Intent      │      │
│   └──┬──────┬──────┬────────┘      │
│      │      │      │               │
│  Tool   RAG  Text-  Fallback       │
│  Node   Node to-SQL  Node          │
│      │      │  Node  │             │
│      └──────┴───┬────┘             │
│                 │                  │
│         response_node              │
│         (RTL wrap if AR)           │
└─────────────────┬──────────────────┘
                  ▼
            final_answer
```

---

## Features Demonstrated

| Feature | Implementation |
|---------|---------------|
| **LangGraph workflow** | `StateGraph` with 6 nodes, conditional routing |
| **Intent classification** | Fast-path keywords + LLM-based (10 intents) |
| **RAG pipeline** | FAISS + sentence-transformers (local, no API key) |
| **Vector search** | Cosine similarity retrieval with deduplication |
| **Text-to-SQL** | LLM prompt → SQL → dual guardrails → SQLite |
| **Tool routing** | Intent-to-tool dispatcher pattern |
| **Session context** | Redis-backed (in-memory fallback), multi-turn |
| **Multilingual** | Arabic + English detection and response |
| **SQL safety** | SELECT-only guard, PII blocklist, keyword filter |
| **FastAPI API** | REST endpoints with Pydantic validation |

---

## Example Queries

### English
```
"What are my reward points for user 1?"
"How many completed pickups are there in Greenville?"
"Show me the top 5 users by weight collected."
"Is Maplewood within your service coverage?"
"What materials are accepted for recycling?"
"How many users registered this month?"
```

### Arabic
```
"ما هي نقاط المكافآت الخاصة بي؟"
"كم عدد الطلبات المكتملة؟"
"ما هي المواد المقبولة لإعادة التدوير؟"
"هل منطقة Greenville تقع ضمن نطاق الخدمة؟"
```

---

## Tech Stack

| Technology | Role |
|-----------|------|
| **Python 3.11+** | Runtime |
| **FastAPI** | REST API layer |
| **LangGraph** | Workflow orchestration |
| **LangChain + OpenAI** | LLM integration |
| **sentence-transformers** | Local embeddings (no API key for RAG) |
| **FAISS** | Local vector store |
| **SQLite** | Mock database (Text-to-SQL) |
| **Redis** | Session context (in-memory fallback) |
| **pytest** | Test suite |

---

## Project Structure

```
backoffice-ai-chatbot-demo/
│
├── main.py                          ← FastAPI entry point
│
├── app/
│   ├── api/
│   │   └── routes.py                ← /chat, /health, /session endpoints
│   │
│   ├── graph/
│   │   ├── workflow.py              ← LangGraph StateGraph definition
│   │   └── nodes.py                 ← Individual node functions
│   │
│   ├── rag/
│   │   ├── pipeline.py              ← FAISS RAG pipeline (ingest→embed→retrieve)
│   │   └── documents.py             ← Fictional FAQ documents (18 Q&A pairs)
│   │
│   ├── text_to_sql/
│   │   ├── generator.py             ← Text-to-SQL pipeline (prompt→LLM→validate→execute)
│   │   └── validator.py             ← SQL safety validator (syntax + semantic)
│   │
│   ├── tools/
│   │   ├── mock_tools.py            ← 5 generic tool implementations (SQLite-backed)
│   │   └── router.py                ← Intent → tool dispatcher
│   │
│   ├── session/
│   │   └── manager.py               ← Redis/in-memory session manager
│   │
│   └── services/
│       ├── intent_classifier.py     ← Intent classification (fast-path + LLM)
│       ├── language_handler.py      ← Arabic/English detection
│       ├── llm_service.py           ← Centralized LLM client
│       └── response_polisher.py     ← Context-only RAG polishing + result formatting
│
├── demo/
│   └── mock_database.py             ← SQLite schema + fictional seed data
│
├── tests/
│   ├── conftest.py                  ← Shared pytest fixtures
│   ├── test_intent_classifier.py    ← Intent classification tests
│   ├── test_rag.py                  ← RAG pipeline tests
│   ├── test_text_to_sql.py          ← SQL validator + DB query tests
│   ├── test_tools.py                ← Tool dispatch tests
│   └── test_session.py              ← Session manager + language detection tests
│
├── docs/
│   └── architecture.md              ← Mermaid diagram + component docs
│
├── .env.example                     ← Environment template (no real values)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Running Locally

### 1. Clone and set up environment

```bash
git clone https://github.com/<your-username>/backoffice-ai-chatbot-demo.git
cd backoffice-ai-chatbot-demo

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
```

> **Note**: The RAG pipeline (sentence-transformers + FAISS) works **without an API key**.
> Only intent classification and Text-to-SQL require `OPENAI_API_KEY`.

### 3. Run the server

```bash
uvicorn main:app --reload
```

- **Swagger UI**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

### 4. Run tests

```bash
pytest tests/ -v
```

> Most tests run **without an API key** (LLM calls are mocked where needed).

### 5. Try the chat API

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are my reward points for user 1?", "session_id": "demo-001"}'
```

---

## API Reference

### POST /chat

```json
Request:
{
  "message": "How many completed requests are in Greenville?",
  "session_id": "my-session-123"
}

Response:
{
  "success": true,
  "answer": "| city | total_weight_kg |\n| --- | --- |\n| Greenville | 89.5 |\n\n*Showing 1 result(s).*",
  "session_id": "my-session-123",
  "intent": "data_query",
  "handled_by": "text_to_sql",
  "language": "en",
  "error": null
}
```

### GET /health

```json
{
  "status": "ok",
  "service": "Backoffice AI Chatbot Demo",
  "version": "1.0.0"
}
```

### GET /session/{session_id}

```json
{
  "session_id": "my-session-123",
  "message_count": 4,
  "history": [
    {"role": "user", "content": "Hello!", "timestamp": "2026-09-23T10:00:00Z"},
    {"role": "assistant", "content": "Hello! How can I help?", "timestamp": "2026-09-23T10:00:01Z"}
  ]
}
```

---

## Security & Sanitization Statement

This repository:
- ✅ Contains **no API keys, tokens, or credentials** of any kind
- ✅ Contains **no production database connections** (SQLite only)
- ✅ Contains **no real user data** (all fictional seed data)
- ✅ Contains **no proprietary source code** (independently implemented)
- ✅ Contains **no internal URLs, IP addresses, or server names**
- ✅ Contains **no confidential business logic or schemas**
- ✅ Uses `.env.example` only — real `.env` is `.gitignored`

---

## License

MIT License — see [LICENSE](LICENSE) for details.

