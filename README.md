# Palm Mind RAG

A production-oriented **document ingestion and conversational RAG API** built with FastAPI.

The system supports:

* PDF and TXT document ingestion
* Text chunking and embeddings
* Vector storage with Qdrant
* Conversational RAG with Redis chat memory
* LLM-powered responses
* Multi-turn conversation context
* LLM-driven interview booking
* PostgreSQL metadata and booking storage
* Automated testing with pytest
* Strict type checking with mypy
* Code quality enforcement with Ruff

Built for the **Palm Mind AI hiring task**.

---

## Architecture

```text
HTTP Request
     │
     ▼
  Routes
     │
     ▼
 Services
     │
     ├── Repository
     ├── Embedder
     ├── Vector Store
     ├── LLM
     └── Chat Memory
```

### Layers

**Routes**

Located in:

```text
app/api/v1/routes/
```

Routes are responsible for parsing HTTP requests and returning response schemas. Business logic is kept outside the route layer.

**Services**

Located in:

```text
app/services/
```

Services contain the application's business logic, including:

* Document ingestion
* RAG retrieval
* Prompt construction
* Chat memory
* Interview booking

**Repositories**

Located in:

```text
app/repositories/
```

Repositories are responsible for database access.

**Protocol Interfaces**

Interfaces are defined for:

```text
app/embeddings/base.py
app/vectorstore/base.py
app/llm/base.py
```

The `ChatMemory` protocol provides the same abstraction for conversation memory.

These interfaces allow providers to be replaced without changing the service layer.

**Dependency Injection**

Dependencies are wired through:

```text
app/api/deps.py
app/main.py
```

The FastAPI lifespan initializes the required services and infrastructure.

---

## Tech Stack

| Area              | Technology             |
| ----------------- | ---------------------- |
| Language          | Python 3.12            |
| API Framework     | FastAPI                |
| Validation        | Pydantic v2            |
| Metadata Database | PostgreSQL             |
| ORM               | SQLAlchemy 2.0 Async   |
| Migrations        | Alembic                |
| Vector Database   | Qdrant                 |
| Chat Memory       | Redis                  |
| Embeddings        | fastembed              |
| Embedding Model   | BAAI/bge-small-en-v1.5 |
| LLM               | Groq                   |
| LLM Model         | openai/gpt-oss-120b    |
| Package Manager   | uv                     |
| Testing           | pytest                 |
| Linting           | Ruff                   |
| Type Checking     | mypy --strict          |

---

## Key Design Decisions

### No Retrieval Chain Abstraction

The RAG pipeline is implemented manually instead of relying on abstractions such as `RetrievalQAChain`.

The retrieval and prompt-building process is explicitly implemented in:

```text
app/services/rag_service.py
```

This makes the retrieval flow easier to inspect and customize.

### No FAISS or Chroma

Qdrant is used as the vector database.

### No UI

The project is an API-only backend. FastAPI's Swagger documentation can be used to interact with the API during development.

---

# Document Ingestion

Documents can be uploaded as either:

* `.pdf`
* `.txt`

The ingestion pipeline is:

```text
Upload
  │
  ▼
Text Extraction
  │
  ▼
Chunking
  │
  ▼
Embedding Generation
  │
  ▼
Qdrant Vector Storage
  │
  ▼
PostgreSQL Metadata
```

The upload endpoint supports two chunking strategies.

---

## Chunking Strategies

### Fixed

```text
strategy=fixed
```

Uses fixed-size character windows with overlap.

Advantages:

* Predictable chunk size
* Simple implementation

Trade-off:

* Can split text in the middle of a sentence

Implementation:

```text
app/chunking/fixed.py
```

### Sentence

```text
strategy=sentence
```

Groups complete sentences until the maximum chunk size is reached and provides sentence-level overlap.

Advantages:

* Preserves sentence boundaries
* Better semantic continuity

Trade-off:

* Chunk sizes can vary

Implementation:

```text
app/chunking/sentence.py
```

Both implementations follow the shared `Chunker` protocol:

```text
app/chunking/base.py
```

---

# RAG Pipeline

The conversational RAG process is implemented in:

```text
app/services/rag_service.py
```

The pipeline is:

```text
User Message
     │
     ▼
Load Redis History
     │
     ▼
Rewrite Follow-up Question
     │
     ▼
Generate Embedding
     │
     ▼
Search Qdrant
     │
     ▼
Apply Score Threshold
     │
     ▼
Build Prompt
     │
     ├── System Instructions
     ├── Retrieved Context
     ├── Conversation History
     └── Original User Question
     │
     ▼
LLM Response
     │
     ▼
Save Conversation to Redis
```

### Follow-up Question Rewriting

For multi-turn conversations, a follow-up such as:

```text
"And how many can I carry over?"
```

may not contain enough information to retrieve the correct document context by itself.

When conversation history exists, the system asks the LLM to rewrite the latest message into a standalone question.

The rewritten question is then embedded and searched against Qdrant.

The original user message is still used when constructing the final prompt.

---

## Retrieval Filtering

Retrieved Qdrant results are filtered using:

```text
RAG_MIN_SCORE
```

Results below the configured threshold are discarded before the prompt is constructed.

---

## Prompt Injection Mitigation

The system prompt instructs the LLM to treat retrieved document content as **data rather than instructions**.

This provides a basic defense against instructions embedded inside uploaded documents attempting to influence the model's behavior.

---

# Conversational Memory

Redis is used to maintain conversation history.

Each session is identified by:

```json
{
  "session_id": "any-string"
}
```

Reusing the same `session_id` allows the application to maintain:

* Conversation history
* Multi-turn context
* Interview booking state

Redis memory uses a capped list per session and TTL-based expiration.

---

# Interview Booking

The application includes an LLM-driven interview booking workflow.

The booking process follows a slot-filling state machine.

Required fields:

```text
name
email
date
time
```

### Booking Flow

```text
User Message
     │
     ▼
Detect Booking Intent
     │
     ▼
Extract Available Fields
     │
     ▼
Merge With Existing Session State
     │
     ▼
Are All Fields Present?
     │
     ├── No ──► Ask For Missing Field
     │
     └── Yes
           │
           ▼
      Validate With Pydantic
           │
           ▼
      Save To PostgreSQL
           │
           ▼
      Clear Pending State
```

Previously collected fields are preserved when new messages provide only additional information.

Null values do not overwrite existing booking data.

---

## Known Booking Limitation

Booking intent currently depends on the LLM's `wants_to_book` classification.

Although this performed well during testing, LLM-based intent detection is not guaranteed to be deterministic.

There is also currently no explicit:

```text
Cancel Booking
```

workflow.

A pending booking can instead be completed or abandoned until the Redis TTL expires.

Possible future improvements include:

* Explicit `/book` command
* Explicit booking UI/action
* Dedicated booking intent trigger
* Booking cancellation flow

---

# API

Base URL during local development:

```text
http://localhost:8000
```

Swagger documentation:

```text
http://localhost:8000/docs
```

---

## Upload Document

### `POST /api/v1/documents`

Multipart upload.

Parameters:

| Parameter  | Type   | Description           |
| ---------- | ------ | --------------------- |
| `file`     | File   | PDF or TXT document   |
| `strategy` | String | `fixed` or `sentence` |

Example:

```text
POST /api/v1/documents
```

The document is extracted, chunked, embedded, stored in Qdrant, and its metadata is saved in PostgreSQL.

---

## List Documents

### `GET /api/v1/documents`

Returns stored document records.

---

## Get Document

### `GET /api/v1/documents/{id}`

Returns a specific document record.

---

## Delete Document

### `DELETE /api/v1/documents/{id}`

Deletes the document record and removes its vectors from Qdrant.

---

## Chat

### `POST /api/v1/chat`

Example request:

```json
{
  "session_id": "demo-session",
  "message": "How many leave days do I get?"
}
```

The response contains:

* Generated reply
* Retrieved sources, when available
* `booking_confirmed` status

Reuse the same `session_id` to maintain conversation context.

---

# Testing

The automated test suite uses `pytest`.

```bash
uv run pytest -v
```

The test suite contains **24 tests** using fakes and mocks, so Docker services are not required to execute the automated tests.

Additional quality checks:

```bash
uv run ruff check .
```

Strict type checking:

```bash
uv run mypy app
```

---

## End-to-End Smoke Tests

End-to-end smoke tests are available in:

```text
scripts/
```

They interact with real infrastructure such as:

* Qdrant
* Redis
* Groq

Example:

```bash
uv run python -m scripts.smoke_step9
```

These tests are run manually because they require live services and a real LLM API key.

---

# Error Handling

The service layer uses domain-specific exceptions rather than raising HTTP exceptions directly.

Application exceptions are defined in:

```text
app/core/exceptions.py
```

A centralized error handler in:

```text
app/api/errors.py
```

maps application errors to HTTP status codes.

This keeps the service layer independent of FastAPI and makes it easier to test business logic without an HTTP server.

---

# Async Processing

The application is designed to avoid blocking the FastAPI event loop.

CPU-bound or synchronous operations such as:

* PDF parsing
* Local embedding inference

are executed using:

```python
asyncio.to_thread(...)
```

This allows the API to continue handling other asynchronous operations while these tasks execute.

---

# Data Consistency

Document ingestion handles failures across PostgreSQL and Qdrant.

If embedding or vector storage fails:

1. The document is marked as `FAILED` in PostgreSQL.
2. Any partially stored vectors are removed from Qdrant.

This reduces the possibility of PostgreSQL and Qdrant becoming inconsistent.

---

# Project Structure

A simplified structure is:

```text
palm-mind-rag/
│
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   └── routes/
│   │   ├── deps.py
│   │   └── errors.py
│   │
│   ├── chunking/
│   │   ├── base.py
│   │   ├── fixed.py
│   │   └── sentence.py
│   │
│   ├── core/
│   │   └── exceptions.py
│   │
│   ├── embeddings/
│   │   └── base.py
│   │
│   ├── llm/
│   │   └── base.py
│   │
│   ├── repositories/
│   │
│   ├── services/
│   │   ├── rag_service.py
│   │   ├── chat_service.py
│   │   └── booking_service.py
│   │
│   ├── vectorstore/
│   │   └── base.py
│   │
│   └── main.py
│
├── scripts/
│   └── smoke_*.py
│
├── alembic/
│
├── tests/
│
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
├── .env.example
└── README.md
```

---

# Setup

## Prerequisites

Install:

* Python 3.12
* uv
* Docker Desktop

---

## Clone the Repository

```bash
git clone <your-repo-url>
cd palm-mind-rag
```

---

## Install Dependencies

```bash
uv sync
```

---

## Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Set the required LLM API key:

```text
LLM_API_KEY=your-groq-api-key
```

The application uses Groq by default.

The LLM provider can be changed through the OpenAI-compatible configuration:

```text
LLM_BASE_URL
LLM_MODEL
```

No service-layer code changes are required to switch providers.

---

## Start Infrastructure

```bash
docker compose up -d
```

---

## Run Database Migrations

```bash
uv run alembic upgrade head
```

---

## Start the API

```bash
uv run uvicorn app.main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

Swagger documentation:

```text
http://localhost:8000/docs
```

---

# Production Considerations

The current implementation is designed as a hiring-task project and keeps several production improvements as future work.

### Background Ingestion

Document ingestion currently happens during the request.

For production, ingestion would be moved to a background queue/worker system.

### Deterministic Booking Trigger

The booking workflow currently relies on LLM intent detection.

A production implementation could combine the LLM with a deterministic trigger such as:

```text
/book
```

or a dedicated booking action.

### Booking Cancellation

An explicit booking cancellation workflow could be added to allow users to cancel an in-progress booking.

---

# Future Improvements

Potential improvements include:

* Background document processing
* Explicit booking commands
* Booking cancellation
* More comprehensive integration tests
* Evaluation datasets for RAG quality
* Retrieval quality metrics
* LLM response evaluation
* Latency monitoring
* More detailed observability
* Production authentication and authorization
* Rate limiting
* API deployment configuration

---

# Project Goals

This project demonstrates practical implementation of:

* FastAPI service architecture
* Async Python
* REST API development
* PostgreSQL and SQLAlchemy
* Redis-based conversational memory
* Vector search with Qdrant
* Embedding generation
* Retrieval-Augmented Generation
* LLM integration
* LLM-based structured extraction
* Dependency injection
* Protocol-based abstractions
* Automated testing
* Mock-based testing
* Static type checking
* Linting
* Error handling
* Data consistency across services

---
