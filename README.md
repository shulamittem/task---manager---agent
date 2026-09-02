# Task Manager Agent

Phase 1 of a client pipeline that reads Hebrew WhatsApp group messages and uses
an LLM (Gemini) to classify each message as a task / not a task, extracting
task fields in the same call when it is one.

This repo is a **local, runnable LangGraph graph** — nothing else. There is no
WhatsApp integration, no database, no web server, and no deployment yet. See
[Roadmap](#roadmap) below for where those land.

## Architecture

### State

The graph is driven by a single Pydantic state model, `MessageState`, carrying:

- Message identity/context: `id`, `timestamp`, `sender`, `group_id`, `raw_text`
- Classification/extraction result: `is_task`, `title`, `due_date`, `assignee`,
  `priority` — all task fields are `Optional`, since they only apply when
  `is_task` is true
- Pipeline bookkeeping: `needs_review: bool`, `error: str | None`

### Single-call classify + extract

Classification and extraction happen in **one** Gemini API call, using a
structured-output schema (`ClassificationExtraction`) where every task field
is optional. This was a deliberate choice over two separate LLM calls
(classify, then extract):

- **Latency** — one round trip instead of two.
- **Accuracy** — the model has the full message context available while
  extracting, rather than extracting blind from a bare "yes, it's a task"
  verdict produced by an earlier, separate call.

### Graph shape

```
classify_node --(is_task?)--> extract_node --> END
      |
      +--(not a task, or classification failed)--> END
```

- `classify_node` makes the one LLM call. It sets `is_task` and, when true,
  the extracted fields. It catches timeouts, malformed model output, and
  empty input itself — on failure it sets `needs_review=True` and populates
  `error`, rather than raising.
- The conditional edge routes on `is_task`. If it's false, or classification
  failed, the graph goes straight to `END` and `extract_node` never runs.
- `extract_node` is pure — no LLM call. It only validates/normalizes the
  fields `classify_node` already returned.

## Install & run

```bash
pip install -e .
```

Copy `.env.example` to `.env` and fill in `GOOGLE_API_KEY`:

```bash
cp .env.example .env
```

Run the fixtures:

```bash
python -m task_manager_agent.run_fixtures
```

## Roadmap

1. **Phase 1 (this repo, now)** — local LangGraph graph + fixtures
2. **Phase 2** (not yet built) — Supabase persistence: a `messages` table
   (`id`, `timestamp`, `sender`, `group_id`, `raw_text`, `is_task`, `title`,
   `due_date`, `assignee`, `priority`; task fields nullable)
3. **Phase 3** (not yet built) — WhatsApp Cloud API integration (webhook
   receiver)
4. **Phase 4** (not yet built) — FastAPI webhook + deploy (Cloud Run or
   Render)
5. **Phase 5** (not yet built) — Daily summary job (Cloud Scheduler or
   pg_cron)

## Environment variables

| Variable          | Required | Default             |
| ------------------ | -------- | -------------------- |
| `GOOGLE_API_KEY`   | yes      | —                     |
| `GEMINI_MODEL`     | no       | `gemini-3.6-flash`   |

## Client work — secrets

This is client work. `.env` holds real secrets and is gitignored — never
commit an API key. Only `.env.example` (with blank values) is tracked.
