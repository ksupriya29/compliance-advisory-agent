# Compliance Advisory & Triage Agent — Architecture

## Overview

This system answers compliance questions grounded exclusively in ingested policy
documents.  It classifies every query by **topic** and **stakes**, enforces
hard governance rules, routes high-stakes queries to a human reviewer, and
writes a tamper-evident audit trail for every interaction.

---

## Agent Pipeline (LangGraph)

```
User query
    │
    ▼
[retrieve]  ── ChromaDB semantic search ──► top-k chunks + citations
    │
    ▼
[classify]  ── Claude claude-sonnet-4-6 ──► topic + stakes label
    │
    ▼
[governance] ── hard-coded rules ─────────► allow / refuse / escalate
    │
    ▼
[audit]     ── append to audit_log.jsonl ──► immutable audit trail
    │
    ▼
Response to user  (or "pending human review" queue)
```

---

## Module Responsibilities

| File | Responsibility |
|------|---------------|
| `src/ingest.py` | Load markdown policy docs → chunk → embed → upsert into ChromaDB |
| `src/retrieve.py` | Embed query → similarity search → generate grounded answer via Claude |
| `src/classify.py` | Classify topic (DPO / AML / Legal / Other) and stakes (low / medium / high) using Claude |
| `src/governance.py` | Enforce rules: refuse on no retrieval match; escalate when stakes ≥ medium |
| `src/audit.py` | Append structured JSON record to `data/audit_log.jsonl` |
| `src/graph.py` | LangGraph `StateGraph` wiring the above nodes into a DAG |
| `app.py` | Streamlit UI: Chat tab, Pending Review tab, Audit Log tab |

---

## Governance Rules (non-negotiable)

1. **No retrieval match** → refuse to answer; respond with a standardised
   "I could not find a relevant policy" message.  Do NOT hallucinate.
2. **stakes = medium** → append to the pending-human-review queue AND answer
   with a disclaimer that the answer is under review.
3. **stakes = high** → refuse to answer directly; route entirely to human
   reviewer; respond with escalation notice only.
4. All responses must include the **policy source citations** used.

---

## Environment Variables

Create a `.env` file (never commit it):

```
ANTHROPIC_API_KEY=sk-ant-...
CHROMA_PERSIST_DIR=./data/chroma_db
```

---

## Adding Policy Documents

Drop `.md` files into `data/policies/` then run:

```bash
python -m src.ingest
```

This is idempotent — documents are upserted by filename hash so re-running
will not create duplicates.

---

## Running the App

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Ingest policies
python -m src.ingest

# 3. Launch UI
streamlit run app.py
```

---

## Audit Log

Every query produces one JSONL record in `data/audit_log.jsonl`:

```json
{
  "id": "<uuid>",
  "timestamp": "<ISO-8601>",
  "query": "...",
  "topic": "DPO|AML|Legal|Other",
  "stakes": "low|medium|high",
  "citations": ["policy_a.md#chunk-3", "..."],
  "answer": "...",
  "routing": "answered|refused|escalated",
  "escalation_reason": "..."
}
```
