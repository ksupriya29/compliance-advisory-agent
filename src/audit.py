"""
src/audit.py — Append-only audit trail writer.

Every query that passes through the pipeline produces exactly one audit record
written as a single JSON line to data/audit_log.jsonl.

The file is opened in append mode for each write — no buffering — to minimise
data loss if the process is interrupted.

Record schema:
{
    "id":                "<uuid4>",
    "timestamp":         "<ISO-8601 UTC>",
    "query":             "<user query string>",
    "topic":             "DPO|AML|Legal|Other",
    "stakes":            "low|medium|high",
    "citations":         ["policy_a.md#chunk-3", ...],
    "answer":            "<final answer shown to user>",
    "routing":           "answered|refused|escalated|escalated_with_answer",
    "escalation_reason": "<string or null>"
}
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from src.classify import ClassificationResult
from src.governance import GovernanceDecision
from src.retrieve import AnswerResult

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AUDIT_LOG_PATH = Path(os.getenv("AUDIT_LOG_PATH", "data/audit_log.jsonl"))


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def append_audit_record(
    query: str,
    retrieval: AnswerResult,
    classification: ClassificationResult,
    decision: GovernanceDecision,
) -> str:
    """
    Build and append one audit record to AUDIT_LOG_PATH.

    Args:
        query:          Original user query.
        retrieval:      Output of src.retrieve.answer().
        classification: Output of src.classify.classify().
        decision:       Output of src.governance.apply_rules().

    Returns:
        The UUID string of the written record (useful for cross-referencing).
    """
    record = build_record(query, retrieval, classification, decision)
    write_record(record)
    return record["id"]


# ---------------------------------------------------------------------------
# Record construction
# ---------------------------------------------------------------------------

def build_record(
    query: str,
    retrieval: AnswerResult,
    classification: ClassificationResult,
    decision: GovernanceDecision,
) -> dict:
    """
    Assemble the audit record dict from pipeline outputs.
    """
    return {
        "id":                str(uuid.uuid4()),
        "timestamp":         datetime.now(timezone.utc).isoformat(),
        "query":             query,
        "topic":             classification.topic,
        "stakes":            classification.stakes,
        "citations":         retrieval.citations,
        "answer":            decision.final_answer,
        "routing":           decision.routing.value,
        "escalation_reason": decision.escalation_reason,
    }


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def write_record(record: dict) -> None:
    """
    Append a single JSON record to AUDIT_LOG_PATH (one record per line).

    Creates the file (and parent directories) if they do not exist.
    Opens in append mode with UTF-8 encoding; flushes immediately.
    """
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()


# ---------------------------------------------------------------------------
# Read-back helpers (for the Streamlit audit-log tab)
# ---------------------------------------------------------------------------

def read_all_records() -> List[dict]:
    """
    Read and parse every record from AUDIT_LOG_PATH.

    Returns records in append order (oldest first).
    Returns an empty list if the file does not exist.
    """
    if not AUDIT_LOG_PATH.exists():
        return []
    with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def read_pending_review() -> List[dict]:
    """
    Return only records whose routing is 'escalated' or 'escalated_with_answer'.

    Used by the Streamlit "Pending Human Review" tab.
    """
    return [
        r for r in read_all_records()
        if r.get("routing") in {"escalated", "escalated_with_answer"}
    ]
