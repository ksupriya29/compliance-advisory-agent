"""
src/graph.py — LangGraph orchestration.

Wires the pipeline nodes into a StateGraph DAG:

    retrieve → classify → governance → audit → END

Each node receives the shared AgentState TypedDict and returns a partial
update dict that is merged into state by LangGraph.

Usage:
    from src.graph import build_graph
    graph = build_graph()
    result = graph.invoke({"query": "What is our data retention policy?"})
    print(result["final_answer"])
"""

from __future__ import annotations

from typing import Annotated, List, Optional, TypedDict

# TODO: from langgraph.graph import StateGraph, END
# TODO: from src.retrieve import retrieve, RetrievalResult
# TODO: from src.classify import classify, ClassificationResult
# TODO: from src.governance import apply_rules, GovernanceDecision
# TODO: from src.audit import append_audit_record


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
    retrieval: Optional[object]          # RetrievalResult

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

    TODO:
        result = retrieve(state["query"])
        return {"retrieval": result}
    """
    raise NotImplementedError


def classify_node(state: AgentState) -> dict:
    """
    Node: classify

    Classifies the query by topic and stakes using the generated answer as
    additional context.

    TODO:
        retrieval = state["retrieval"]
        answer_excerpt = (retrieval.answer or "")[:500]
        result = classify(state["query"], answer_excerpt)
        return {"classification": result}
    """
    raise NotImplementedError


def governance_node(state: AgentState) -> dict:
    """
    Node: governance

    Applies hard-coded governance rules and determines routing.

    TODO:
        decision = apply_rules(state["retrieval"], state["classification"])
        return {
            "decision": decision,
            "final_answer": decision.final_answer,
            "routing": decision.routing.value,
            "add_to_review_queue": decision.add_to_review_queue,
        }
    """
    raise NotImplementedError


def audit_node(state: AgentState) -> dict:
    """
    Node: audit

    Appends the full interaction to the audit log.

    TODO:
        audit_id = append_audit_record(
            query=state["query"],
            retrieval=state["retrieval"],
            classification=state["classification"],
            decision=state["decision"],
        )
        return {"audit_id": audit_id}
    """
    raise NotImplementedError


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

    TODO:
        1. workflow = StateGraph(AgentState)
        2. workflow.add_node("retrieve",   retrieve_node)
        3. workflow.add_node("classify",   classify_node)
        4. workflow.add_node("governance", governance_node)
        5. workflow.add_node("audit",      audit_node)
        6. workflow.set_entry_point("retrieve")
        7. workflow.add_edge("retrieve",   "classify")
        8. workflow.add_edge("classify",   "governance")
        9. workflow.add_edge("governance", "audit")
        10. workflow.add_edge("audit",     END)
        11. return workflow.compile()
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Module-level singleton (lazy-initialised)
# ---------------------------------------------------------------------------

_graph = None


def get_graph():
    """
    Return the compiled graph, building it on first call.

    TODO:
        global _graph
        if _graph is None:
            _graph = build_graph()
        return _graph
    """
    raise NotImplementedError


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

    TODO:
        graph = get_graph()
        return graph.invoke({"query": query})
    """
    raise NotImplementedError
