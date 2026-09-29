
- **Routes** (`app/api/v1/routes/`) parse requests and return schemas. No business logic.
- **Services** (`app/services/`) hold the actual logic: ingestion pipeline, RAG
  retrieval and prompting, chat memory, interview booking.
- **Repositories** (`app/repositories/`) are the only code that touches the database.
- **Protocol interfaces** (`app/embeddings/base.py`, `app/vectorstore/base.py`,
  `app/llm/base.py`, the `ChatMemory` protocol) decouple services from specific
  providers, so the embedder, vector store or LLM can be swapped by adding one
  implementation, no service code changes.
- Dependency injection is wired in `app/api/deps.py` and the FastAPI `lifespan`
  in `app/main.py`, so every route gets fully constructed services.

## Stack

| Concern | Choice | Why |
|---|---|---|
| Framework | FastAPI + Pydantic v2, Python 3.12 | Async-native, typed, matches the task's typing requirement |
| Metadata DB | PostgreSQL + SQLAlchemy 2.0 (async) + Alembic | Versioned schema, typed ORM |
| Vector DB | Qdrant | Simple to self-host, good async Python client |
| Chat memory | Redis (capped list per session + TTL) | Fast, expiry built in |
| Embeddings | `fastembed` (BAAI/bge-small-en-v1.5), local | Free, no API key, runs on CPU |
| LLM | Groq (`openai/gpt-oss-120b`) via the OpenAI-compatible API | Free tier, fast, and the OpenAI-compatible interface means switching to OpenAI/Gemini is a 3-line `.env` change |
| Package management | `uv` | Fast, lockfile-based |
| Quality | `ruff`, `mypy --strict`, `pytest` | Full typing coverage, enforced lint rules |

## Two chunking strategies

Selectable per upload via the `strategy` form field:

- **`fixed`** — fixed-size character windows with overlap (`app/chunking/fixed.py`).
  Predictable size, can cut mid-sentence.
- **`sentence`** — packs whole sentences up to a max length, with sentence-level
  overlap (`app/chunking/sentence.py`). Keeps meaning intact, sizes vary.

Both implement a shared `Chunker` protocol (`app/chunking/base.py`), so the
ingestion service is agnostic to which one is used.

## Custom RAG pipeline

No chain abstraction. `RagService.answer()` (`app/services/rag_service.py`) does,
step by step:

1. Load recent history from Redis.
2. If there's history, ask the LLM to rewrite the latest message into a
   standalone question (resolves "it", "that", "the second one", etc.) —
   this is what makes multi-turn retrieval work, since a bare follow-up like
   "and how many can I carry over?" embeds to something meaningless on its own.
3. Embed the standalone question, search Qdrant, drop hits below `RAG_MIN_SCORE`.
4. Build the prompt: system instructions + retrieved context + conversation
   history + the original (non-rewritten) question.
5. Call the LLM, save the question/answer pair back to Redis.

The system prompt explicitly tells the model to treat retrieved context as
data, not instructions — basic mitigation against prompt injection via
uploaded document content.

## Interview booking

A hand-written slot-filling state machine (`app/services/booking_service.py`,
`app/services/chat_service.py`):

1. Every chat turn, one JSON-mode LLM call asks: is the user trying to book,
   and what booking fields (name, email, date, time) can be extracted from the
   conversation so far?
2. Extracted fields are merged into whatever was already collected for that
   session (stored in Redis, not overwritten by nulls).
3. If any field is missing, the assistant asks for the next one and the
   turn short-circuits before reaching RAG.
4. Once complete, Pydantic validates the slots, the booking is saved to
   Postgres, and the pending state is cleared.

**Known limitation:** whether a message is "a booking turn" depends on the
LLM's `wants_to_book` judgment each turn. It performed well in testing but
isn't guaranteed. There's also no explicit "cancel my booking" path yet — a
user must complete or abandon (let it expire via the Redis TTL) a pending
booking. Both are reasonable next steps, left out for time.

## Setup

**Prerequisites:** Python 3.12, [uv](https://docs.astral.sh/uv/), Docker Desktop.

```powershell
git clone <your-repo-url>
cd palm-mind-rag
uv sync
cp .env.example .env   # fill in LLM_API_KEY (see below)
docker compose up -d
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs`.

### Environment variables

See `.env.example`. You need a free Groq API key from
[console.groq.com](https://console.groq.com) for `LLM_API_KEY`. To use a
different OpenAI-compatible provider, change `LLM_BASE_URL` and `LLM_MODEL`
accordingly — no code changes needed.

## API

### `POST /api/v1/documents`
Multipart upload. Fields: `file` (`.pdf` or `.txt`), `strategy` (`fixed` |
`sentence`, default `fixed`). Extracts text, chunks it, embeds and stores in
Qdrant, saves metadata in Postgres.

### `GET /api/v1/documents`, `GET /api/v1/documents/{id}`, `DELETE /api/v1/documents/{id}`
List, fetch, and delete document records (delete also removes vectors from Qdrant).

### `POST /api/v1/chat`
```json
{ "session_id": "any-string", "message": "How many leave days do I get?" }
```
Returns the reply, cited sources (if any), and `booking_confirmed`. Reuse the
same `session_id` across a conversation for memory and multi-turn booking to work.

## Testing

```powershell
uv run pytest -v        # 24 tests, all with fakes/mocks — no Docker needed
uv run ruff check .
uv run mypy app          # strict mode
```

End-to-end smoke tests against real Qdrant/Redis/Groq are in `scripts/` and
run manually (`uv run python -m scripts.smoke_step9`, etc.) — not part of the
automated suite since they need live services and a real LLM key.

## Design notes for reviewers

- **Domain exceptions, not HTTP exceptions, in services.** Services raise
  `AppError` subclasses (`app/core/exceptions.py`); one handler
  (`app/api/errors.py`) maps them to status codes. Services stay
  framework-agnostic and testable without FastAPI.
- **Everything heavy is async or off-loaded.** PDF parsing and local embedding
  inference are synchronous/CPU-bound, so they're run via `asyncio.to_thread`
  to avoid blocking the event loop.
- **Ingestion failure cleans up after itself.** A failed embed/store marks the
  document `FAILED` in Postgres and removes any partial vectors from Qdrant,
  so the two stores don't drift out of sync.
- **In production**, document ingestion would move to a background
  queue/worker instead of running synchronously inside the request, and the
  booking intent-detection would likely be backed by a more deterministic
  trigger (an explicit `/book` command or button) in addition to the LLM
  judgment, for reliability.