# CLAUDE.md

Guidance for Claude Code (and other agents) working in this repository.

## Project

This pipeline reads Hebrew WhatsApp group messages and uses an LLM to decide
whether each message describes a task and, if so, extract its fields (title,
due date, assignee, priority). This is client work.

This repo currently covers **Phase 1 only**: a local, runnable LangGraph
graph with no external services wired up.

## Stack

- Python (>=3.10 — code uses `typing.Optional` and `Literal`)
- LangGraph — orchestrates the classify/extract flow as a graph
- Pydantic (v2) — schema for state and LLM output
- Gemini via the `google-genai` SDK — model `gemini-3.6-flash`. Chosen over
  a LangChain-based LLM wrapper because Gemini's native structured/schema
  output already covers what we need (a single call returning classification
  + optional extracted fields); pulling in the full LangChain framework for
  that would be unnecessary weight.

**Later phase, not yet built** (do not assume these exist or start wiring
them in during Phase 1 work):

- Supabase (persistence)
- WhatsApp Cloud API (message ingestion / webhook)
- FastAPI (webhook service)
- Cloud Run / Render (deployment target)
- Cloud Scheduler / pg_cron (daily summary job)

## Architecture

State model `MessageState` (Pydantic) carries message identity/context (`id`,
`timestamp`, `sender`, `group_id`, `raw_text`), classification/extraction
output (`is_task`, `title`, `due_date`, `assignee`, `priority` — all task
fields `Optional`), and pipeline bookkeeping (`needs_review: bool`,
`error: str | None`).

**Single-call classify + extract.** Classification and extraction happen in
one Gemini call via a structured-output schema (`ClassificationExtraction`)
where every task field is optional — not two separate LLM calls. Reasons:

- Lower latency (one round trip instead of two).
- Better accuracy: the model has full message context while extracting,
  instead of extracting blind from a bare classification verdict produced
  by an earlier, separate call.

**Graph shape:**

```
classify_node --(is_task?)--> extract_node --> END
      |
      +--(not a task, or classification failed)--> END
```

- `classify_node`: the one LLM call. Sets `is_task` and, when true, the
  extracted fields. Catches timeouts, malformed model output, and empty
  input itself, setting `needs_review=True` + `error=...` instead of
  raising.
- Conditional edge on `is_task`: false, or a failed classification, routes
  straight to `END` — `extract_node` never runs in that case.
- `extract_node`: pure, no LLM call. Validates/normalizes the fields
  `classify_node` already returned.

## Roadmap

1. Phase 1 (this repo, now) — local LangGraph graph + fixtures
2. Phase 2 — Supabase persistence (`messages` table: id, timestamp, sender,
   group_id, raw_text, is_task, title, due_date, assignee, priority; task
   fields nullable)
3. Phase 3 — WhatsApp Cloud API integration (webhook receiver)
4. Phase 4 — FastAPI webhook + deploy (Cloud Run or Render)
5. Phase 5 — Daily summary job (Cloud Scheduler or pg_cron)

## Conventions

- Pydantic models at every boundary: state, LLM output, and (later) the
  persistence layer.
- Nodes must be pure and independently testable — state in, state-update
  out, no hidden I/O beyond the one API call `classify_node` owns.
- Secrets live only in `.env` (gitignored). Never inline an API key in code.
- How to run: `pip install -e .`, then
  `python -m task_manager_agent.run_fixtures`.

## Known constraints

- Input is Hebrew-language text.
- Client data sensitivity: do not log or echo raw message content beyond
  what's needed to run/debug the pipeline.
- Later phases (persistence, deployment, scheduling) are targeting free-tier
  infrastructure — keep that in mind when those phases are designed.
