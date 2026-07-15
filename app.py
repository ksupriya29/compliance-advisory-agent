"""
app.py — Streamlit UI for the Compliance Advisory & Triage Agent.

Tabs:
    1. 💬 Chat           — submit queries, view answers with citations and routing badge
    2. 🕐 Pending Review — table of escalated queries awaiting human review
    3. 📋 Audit Log      — full append-only audit trail with filters

Run:
    streamlit run app.py
"""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

# TODO: from src.graph import run_query
# TODO: from src.audit import read_all_records, read_pending_review

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

load_dotenv()  # load ANTHROPIC_API_KEY and CHROMA_PERSIST_DIR from .env

st.set_page_config(
    page_title="Compliance Advisory & Triage Agent",
    page_icon="⚖️",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

def init_session_state() -> None:
    """
    Initialise Streamlit session state keys on first load.

    TODO:
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []   # list of {"role", "content", "meta"}
    """
    pass  # TODO: implement


# ---------------------------------------------------------------------------
# Tab 1: Chat
# ---------------------------------------------------------------------------

def render_chat_tab() -> None:
    """
    Render the conversational chat interface.

    UI elements:
    - Scrollable message history (user / assistant bubbles)
    - Text input box pinned to the bottom
    - On submit: call run_query(), display answer + citations + routing badge
    - Routing badge colours:
        answered             → green
        escalated_with_answer → orange
        escalated            → red
        refused              → grey

    TODO:
        1. Display st.session_state.chat_history using st.chat_message()
        2. query = st.chat_input("Ask a compliance question…")
        3. if query:
               with st.spinner("Searching policies…"):
                   state = run_query(query)
               append to chat_history
               display answer, citations, and routing badge
    """
    st.header("💬 Compliance Chat")
    st.info("TODO: implement chat interface")

    # Placeholder — remove when implemented
    with st.form("chat_form"):
        query = st.text_area("Your compliance question:", height=100)
        submitted = st.form_submit_button("Submit")

    if submitted and query.strip():
        st.warning(
            "Pipeline not yet implemented. "
            "Run the graph build-out before using this tab."
        )


# ---------------------------------------------------------------------------
# Tab 2: Pending Human Review
# ---------------------------------------------------------------------------

def render_pending_review_tab() -> None:
    """
    Render a table of queries currently pending human review.

    Columns: timestamp, topic, stakes, routing, query (truncated), audit_id
    Add a "Mark Reviewed" button per row (future feature — just shown as TODO).

    TODO:
        1. records = read_pending_review()
        2. if not records: st.info("No queries pending review.")
        3. else: st.dataframe(pd.DataFrame(records)[PENDING_COLUMNS])
    """
    st.header("🕐 Pending Human Review")

    # TODO: replace placeholder with real data
    st.info("TODO: load pending records from audit_log.jsonl via read_pending_review()")

    st.caption(
        "Queries with stakes=medium are shown here with their draft answer. "
        "Queries with stakes=high are shown without an answer."
    )


# ---------------------------------------------------------------------------
# Tab 3: Audit Log
# ---------------------------------------------------------------------------

def render_audit_log_tab() -> None:
    """
    Render the full audit log with search/filter controls.

    Controls:
    - Topic filter (multiselect: DPO / AML / Legal / Other)
    - Stakes filter (multiselect: low / medium / high)
    - Routing filter (multiselect)
    - Free-text search over query field
    - Date range picker

    Table columns: timestamp, id, topic, stakes, routing, query (truncated)
    Expandable row detail: full answer, citations, escalation_reason.

    TODO:
        1. records = read_all_records()
        2. apply sidebar filters
        3. st.dataframe(filtered_df)
        4. for each record, st.expander with full detail
    """
    st.header("📋 Audit Log")

    # TODO: replace placeholder with real data
    st.info("TODO: load all records from audit_log.jsonl via read_all_records()")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.multiselect("Topic", ["DPO", "AML", "Legal", "Other"], key="filter_topic")
    with col2:
        st.multiselect("Stakes", ["low", "medium", "high"], key="filter_stakes")
    with col3:
        st.multiselect(
            "Routing",
            ["answered", "refused", "escalated", "escalated_with_answer"],
            key="filter_routing",
        )

    st.caption("Filters will be applied once the pipeline is implemented.")


# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point — renders tab layout."""
    init_session_state()

    st.title("⚖️ Compliance Advisory & Triage Agent")
    st.caption(
        "Grounded in your internal policy documents · "
        "Powered by Claude claude-sonnet-4-6 · "
        "Audit-logged · Human-in-the-loop escalation"
    )

    tab_chat, tab_review, tab_audit = st.tabs(
        ["💬 Chat", "🕐 Pending Review", "📋 Audit Log"]
    )

    with tab_chat:
        render_chat_tab()

    with tab_review:
        render_pending_review_tab()

    with tab_audit:
        render_audit_log_tab()


if __name__ == "__main__":
    main()
