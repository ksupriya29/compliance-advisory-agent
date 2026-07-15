"""
src/governance.py — Hard-coded governance rules.

Rules (in evaluation order — first match wins):
    1. NO_MATCH    → REFUSE:   no retrieval match found; refuse to answer.
    2. stakes=high → ESCALATE: route entirely to human review; do not expose answer.
    3. stakes=medium → ESCALATE_WITH_ANSWER: answer with disclaimer + add to review queue.
    4. stakes=low  → ALLOW:    answer may be returned directly.

These rules are intentionally hard-coded and NOT configurable at runtime.
Any change to the rules must go through a code review.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.classify import ClassificationResult
from src.retrieve import RetrievalResult


# ---------------------------------------------------------------------------
# Routing decisions
# ---------------------------------------------------------------------------

class Routing(str, Enum):
    ALLOW               = "answered"
    REFUSE              = "refused"
    ESCALATE            = "escalated"
    ESCALATE_WITH_ANSWER = "escalated_with_answer"


# Standard messages — do NOT localise or customise without compliance sign-off.
REFUSE_MESSAGE = (
    "I was unable to find a relevant policy to answer your question. "
    "Please consult your compliance officer directly."
)

ESCALATE_MESSAGE = (
    "Your query involves high-stakes compliance risk and has been routed to a "
    "human compliance reviewer. You will receive a response within one business day."
)

ESCALATE_WITH_ANSWER_DISCLAIMER = (
    "\n\n⚠️  This response involves medium-stakes compliance risk and is pending "
    "human review. Treat it as preliminary guidance only."
)


# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------

@dataclass
class GovernanceDecision:
    """Result of applying governance rules to a query."""
    routing: Routing
    final_answer: str               # answer shown to the user (may be a refusal/escalation notice)
    escalation_reason: Optional[str] = None   # set when routing != ALLOW
    add_to_review_queue: bool = False          # True for ESCALATE and ESCALATE_WITH_ANSWER


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------

def apply_rules(
    retrieval: RetrievalResult,
    classification: ClassificationResult,
) -> GovernanceDecision:
    """
    Apply governance rules and return a GovernanceDecision.

    Rules:
        1. retrieval.no_match → REFUSE
        2. classification.stakes == "high" → ESCALATE
        3. classification.stakes == "medium" → ESCALATE_WITH_ANSWER
        4. classification.stakes == "low" → ALLOW

    TODO:
        1. if retrieval.no_match: return _refuse("No matching policy found")
        2. if classification.stakes == "high": return _escalate(classification)
        3. if classification.stakes == "medium": return _escalate_with_answer(retrieval, classification)
        4. return _allow(retrieval)
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Private helpers — one per routing outcome
# ---------------------------------------------------------------------------

def _refuse(reason: str) -> GovernanceDecision:
    """
    Build a REFUSE decision.

    TODO: return GovernanceDecision(
              routing=Routing.REFUSE,
              final_answer=REFUSE_MESSAGE,
              escalation_reason=reason,
              add_to_review_queue=False,
          )
    """
    raise NotImplementedError


def _escalate(classification: ClassificationResult) -> GovernanceDecision:
    """
    Build a full ESCALATE decision (answer withheld).

    TODO: return GovernanceDecision(
              routing=Routing.ESCALATE,
              final_answer=ESCALATE_MESSAGE,
              escalation_reason=f"stakes=high, topic={classification.topic}",
              add_to_review_queue=True,
          )
    """
    raise NotImplementedError


def _escalate_with_answer(
    retrieval: RetrievalResult,
    classification: ClassificationResult,
) -> GovernanceDecision:
    """
    Build an ESCALATE_WITH_ANSWER decision (answer returned with disclaimer).

    TODO: return GovernanceDecision(
              routing=Routing.ESCALATE_WITH_ANSWER,
              final_answer=retrieval.answer + ESCALATE_WITH_ANSWER_DISCLAIMER,
              escalation_reason=f"stakes=medium, topic={classification.topic}",
              add_to_review_queue=True,
          )
    """
    raise NotImplementedError


def _allow(retrieval: RetrievalResult) -> GovernanceDecision:
    """
    Build an ALLOW decision (answer returned as-is).

    TODO: return GovernanceDecision(
              routing=Routing.ALLOW,
              final_answer=retrieval.answer,
              add_to_review_queue=False,
          )
    """
    raise NotImplementedError
