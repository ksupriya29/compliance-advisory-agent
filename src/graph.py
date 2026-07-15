"""
src/graph.py — LangGraph orchestration.

Wires the pipeline nodes into a StateGraph DAG:

    retrieve → classify → governance → audit → END

Each node receives the shared AgentState TypedDict and returns a partial
update dict that is merged into state by LangGraph.

Usage:
    from src.graph import run_query
    graph = build_graph()
    result = graph.invoke({"query": "What is our data retention policy?"})
    print(result["final_answer"])
"""

from __future__ import annotations

from typing import Optional, TypedDict

from langgraph.graph import StateGraph, END

from src.retrieve import answer, AnswerResult
from src.classify import classify, ClassificationResult
from src.governance import apply_rules, GovernanceDecision
from src.audit import append_audit_record


# ---------------------------------------------------------------------------
# Shared state schema
# ---------------------------------------------------------------------------

class AgentState(TypedDict, total=False):
    """
    Mutable state passed between LangGraph nodes.

    All fields are optional (total=False) because each node only populates
    the fields it is responsible for.
    """
    # Input
    query: str

    # retrieve node output
    retrieval: Optional[object]          # AnswerResult

    # classify node output
    classification: Optional[object]     # ClassificationResult

    # governance node output
    decision: Optional[object]           # GovernanceDecision
    final_answer: str
    routing: str
    add_to_review_queue: bool

    # audit node output
    audit_id: str                        # UUID of the written audit record


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------

def retrieve_node(state: AgentState) -> dict:
    """
    Node: retrieve

    Runs semantic search + answer generation for state["query"].
    Calls answer() (not retrieve()) to get the full AnswerResult including
    the generated answer text and citations.
    """
    result = answer(state["query"])
    return {"retrieval": result}


def classify_node(state: AgentState) -> dict:
    """
    Node: classify

    Classifies the query by topic and stakes using the generated answer as
    additional context.
    """
    retrieval: AnswerResult = state["retrieval"]
    answer_excerpt = (retrieval.answer or "")[:500]
    result = classify(state["query"], answer_excerpt)
    return {"classification": result}


def governance_node(state: AgentState) -> dict:
    """
    Node: governance

    Applies hard-coded governance rules and determines routing.
    """
    decision = apply_rules(state["retrieval"], state["classification"])
    return {
        "decision": decision,
        "final_answer": decision.final_answer,
        "routing": decision.routing.value,
        "add_to_review_queue": decision.add_to_review_queue,
    }


def audit_node(state: AgentState) -> dict:
    """
    Node: audit

    Appends the full interaction to the audit log.
    """
    audit_id = append_audit_record(
        query=state["query"],
        retrieval=state["retrieval"],
        classification=state["classification"],
        decision=state["decision"],
    )
    return {"audit_id": audit_id}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph():
    """
    Build and compile the LangGraph StateGraph.

    Topology:
        START → retrieve → classify → governance → audit → END

    Returns:
        A compiled LangGraph runnable (call .invoke({"query": "..."}) on it).
    """
    workflow = StateGraph(AgentState)
    workflow.add_node("retrieve",   retrieve_node)
    workflow.add_node("classify",   classify_node)
    workflow.add_node("governance", governance_node)
    workflow.add_node("audit",      audit_node)
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve",   "classify")
    workflow.add_edge("classify",   "governance")
    workflow.add_edge("governance", "audit")
    workflow.add_edge("audit",      END)
    return workflow.compile()


# ---------------------------------------------------------------------------
# Module-level singleton (lazy-initialised)
# ---------------------------------------------------------------------------

_graph = None


def get_graph():
    """Return the compiled graph, building it on first call."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# ---------------------------------------------------------------------------
# Convenience wrapper
# ---------------------------------------------------------------------------

def run_query(query: str) -> AgentState:
    """
    Run a single query through the full pipeline and return the final state.

    Args:
        query: The user's compliance question.

    Returns:
        AgentState dict with all fields populated.
    """
    graph = get_graph()
    return graph.invoke({"query": query})
