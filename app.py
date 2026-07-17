"""
app.py -- Streamlit UI for the Compliance Advisory & Triage Agent.

Tabs:
    1. Chat           -- submit queries, view answers with citations and routing badge
    2. Pending Review -- table of escalated queries awaiting human review
    3. Audit Log      -- full append-only audit trail with filters

Run:
    streamlit run app.py
"""

from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.graph import run_query
from src.audit import read_all_records, read_pending_review

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

load_dotenv()


def _ensure_db_ready() -> None:
    """
    Guarantee the ChromaDB vector store is populated before any query runs.

    Called once per Streamlit process via st.cache_resource so it only
    executes on cold start, not on every page reload.

    Recovery logic (in order):
        1. If the collection is healthy and non-empty  → nothing to do.
        2. If the collection is empty (DB wiped/first run) → ingest.
        3. If ChromaDB raises ANY exception (corrupt DB, version mismatch,
           seq_id type error, etc.) → delete data/chroma_db/ entirely and
           re-ingest from scratch.  This handles the 'object of type int has
           no len()' SQLite seq_id corruption automatically.
    """
    import shutil
    from pathlib import Path
    from src.ingest import (
        get_chroma_client,
        get_or_create_collection,
        ingest_all,
        CHROMA_PERSIST_DIR,
    )

    def _ingest_fresh() -> None:
        summary = ingest_all()
        st.toast(
            f"Policy DB built: {summary['files']} files, {summary['chunks']} chunks",
            icon="📚",
        )

    try:
        client = get_chroma_client()
        collection = get_or_create_collection(client)
        count = int(collection.count())
        if count == 0:
            # Empty collection — first deploy or DB was wiped
            _ingest_fresh()
    except Exception:
        # Corrupt / incompatible DB — delete and rebuild
        try:
            if Path(CHROMA_PERSIST_DIR).exists():
                shutil.rmtree(str(CHROMA_PERSIST_DIR))
        except Exception:
            pass  # best-effort; ingest_all will recreate it
        _ingest_fresh()


@st.cache_resource(show_spinner="Initialising policy database…")
def _bootstrap_db() -> None:
    """Thin cache wrapper so _ensure_db_ready() runs only once per process."""
    _ensure_db_ready()


# Run DB bootstrap before anything else touches ChromaDB.
_bootstrap_db()

st.set_page_config(
    page_title="Compliance Advisory & Triage Agent",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
/* ── Base ── */
[data-testid="stAppViewContainer"] {
    background: #0f1117;
    color: #e2e8f0;
}
[data-testid="stSidebar"] {
    background: #1a1d27;
    border-right: 1px solid #2d3148;
}
[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}

/* ── Tab bar ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: #1a1d27;
    border-radius: 12px;
    padding: 6px;
    border: 1px solid #2d3148;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: 600;
    font-size: 0.9rem;
    color: #94a3b8;
    background: transparent;
    border: none;
}
.stTabs [aria-selected="true"] {
    background: #2563eb !important;
    color: #ffffff !important;
}

/* ── Chat bubbles ── */
[data-testid="stChatMessage"] {
    border-radius: 14px;
    padding: 4px 8px;
    margin-bottom: 6px;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: #1e2235;
    border: 1px solid #2d3148;
    border-radius: 12px;
    padding: 16px 20px;
}
[data-testid="stMetricLabel"] { color: #94a3b8 !important; font-size: 0.8rem; }
[data-testid="stMetricValue"] { color: #e2e8f0 !important; font-size: 1.6rem; font-weight: 700; }

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    border: 1px solid #2d3148;
    overflow: hidden;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #1e2235;
    border: 1px solid #2d3148;
    border-radius: 10px;
    margin-bottom: 8px;
}

/* ── Input ── */
[data-testid="stTextInput"] input,
[data-testid="stChatInput"] textarea {
    background: #1e2235 !important;
    border: 1px solid #2d3148 !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
}

/* ── Buttons ── */
.stButton > button {
    background: #2563eb;
    color: #fff;
    border: none;
    border-radius: 8px;
    font-weight: 600;
}
.stButton > button:hover {
    background: #1d4ed8;
}

/* ── Divider ── */
hr { border-color: #2d3148 !important; }

/* ── Spinner text ── */
.stSpinner > div { color: #94a3b8 !important; }

/* ── Info / warning boxes ── */
[data-testid="stAlert"] {
    border-radius: 10px;
    border-left-width: 4px;
}

/* ── Caption ── */
.stCaption { color: #64748b !important; }

/* ── Section headers ── */
h1 { color: #f1f5f9 !important; font-weight: 800 !important; }
h2 { color: #e2e8f0 !important; font-weight: 700 !important; }
h3 { color: #cbd5e1 !important; font-weight: 600 !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Routing badge helpers
# ---------------------------------------------------------------------------

_BADGE: dict[str, tuple[str, str]] = {
    "answered":              ("Answered",              "#16a34a", "#dcfce7", "#14532d"),
    "escalated_with_answer": ("Escalated + Answer",    "#d97706", "#fef3c7", "#78350f"),
    "escalated":             ("Escalated",             "#dc2626", "#fee2e2", "#7f1d1d"),
    "refused":               ("Refused",               "#6b7280", "#f3f4f6", "#1f2937"),
}

_STAKES_STYLE: dict[str, tuple[str, str]] = {
    "low":    ("#16a34a", "#dcfce7"),
    "medium": ("#d97706", "#fef3c7"),
    "high":   ("#dc2626", "#fee2e2"),
}

_TOPIC_STYLE: dict[str, tuple[str, str]] = {
    "DPO":   ("#2563eb", "#dbeafe"),
    "AML":   ("#7c3aed", "#ede9fe"),
    "Legal": ("#0891b2", "#cffafe"),
    "Other": ("#6b7280", "#f3f4f6"),
}


def _badge_html(routing: str) -> str:
    label, border, bg, text = _BADGE.get(routing, (routing, "#6b7280", "#f3f4f6", "#1f2937"))
    icon = {"answered": "✓", "escalated_with_answer": "~", "escalated": "!", "refused": "x"}.get(routing, "?")
    return (
        f'<span style="display:inline-flex;align-items:center;gap:4px;'
        f'background:{bg};color:{text};border:1.5px solid {border};'
        f'padding:3px 10px;border-radius:20px;font-size:0.78rem;font-weight:700;'
        f'letter-spacing:0.02em;">'
        f'<span style="font-size:0.85em;">{icon}</span> {label}</span>'
    )


def _topic_chip(topic: str) -> str:
    border, bg = _TOPIC_STYLE.get(topic, ("#6b7280", "#f3f4f6"))
    return (
        f'<span style="display:inline-block;background:{bg};color:{border};'
        f'border:1.5px solid {border};padding:2px 9px;border-radius:20px;'
        f'font-size:0.75rem;font-weight:700;margin-left:6px;">{topic}</span>'
    )


def _stakes_chip(stakes: str) -> str:
    border, bg = _STAKES_STYLE.get(stakes, ("#6b7280", "#f3f4f6"))
    return (
        f'<span style="display:inline-block;background:{bg};color:{border};'
        f'border:1.5px solid {border};padding:2px 9px;border-radius:20px;'
        f'font-size:0.75rem;font-weight:700;margin-left:4px;">stakes: {stakes}</span>'
    )


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar() -> str:
    """Render sidebar nav; return active page name."""
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:20px 0 10px;">
            <div style="font-size:2.4rem;">⚖️</div>
            <div style="font-size:1rem;font-weight:800;color:#f1f5f9;margin-top:4px;">
                Compliance Agent
            </div>
            <div style="font-size:0.72rem;color:#64748b;margin-top:2px;">
                Audit-logged · Human-in-the-loop
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        records = read_all_records()
        pending = read_pending_review()
        total   = len(records)
        n_ans   = sum(1 for r in records if r.get("routing") == "answered")
        n_esc   = sum(1 for r in records if str(r.get("routing","")).startswith("escalated"))
        n_ref   = sum(1 for r in records if r.get("routing") == "refused")

        st.markdown("""
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px;">
        """ + "".join([
            f'<div style="background:#1e2235;border:1px solid #2d3148;border-radius:10px;'
            f'padding:10px;text-align:center;">'
            f'<div style="font-size:1.3rem;font-weight:800;color:{c};">{v}</div>'
            f'<div style="font-size:0.68rem;color:#64748b;margin-top:2px;">{l}</div></div>'
            for v, l, c in [
                (total,  "Total",     "#e2e8f0"),
                (n_ans,  "Answered",  "#16a34a"),
                (n_esc,  "Escalated", "#d97706"),
                (n_ref,  "Refused",   "#dc2626"),
            ]
        ]) + "</div>", unsafe_allow_html=True)

        if pending:
            st.markdown(
                f'<div style="background:#7c3aed22;border:1px solid #7c3aed55;'
                f'border-radius:8px;padding:8px 12px;font-size:0.8rem;color:#a78bfa;">'
                f'  {len(pending)} item(s) awaiting review</div>',
                unsafe_allow_html=True,
            )
            st.markdown("")

        st.divider()
        st.markdown(
            '<div style="font-size:0.7rem;color:#475569;text-align:center;padding-top:4px;">'
            'Powered by llama-3.1-8b · Groq<br>'
            'Vector DB: ChromaDB · Local embeddings'
            '</div>',
            unsafe_allow_html=True,
        )
    return ""


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def init_session_state() -> None:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []



# ---------------------------------------------------------------------------
# Tab 1: Chat
# ---------------------------------------------------------------------------

def _render_answer_meta(meta: dict) -> None:
    """Render routing badge, topic/stakes chips, citations, audit ID."""
    routing  = meta.get("routing", "")
    citations = meta.get("citations", [])
    topic    = meta.get("topic", "")
    stakes   = meta.get("stakes", "")
    audit_id = meta.get("audit_id", "")

    chips = _badge_html(routing) + _topic_chip(topic) + _stakes_chip(stakes)
    st.markdown(
        f'<div style="margin-top:8px;margin-bottom:4px;">{chips}</div>',
        unsafe_allow_html=True,
    )

    if routing in ("answered", "escalated_with_answer"):
        if citations:
            cite_html = " &nbsp;·&nbsp; ".join(
                f'<code style="background:#1e3a5f;color:#93c5fd;'
                f'border-radius:4px;padding:1px 6px;font-size:0.75rem;">{c}</code>'
                for c in citations
            )
            st.markdown(
                f'<div style="margin-top:4px;font-size:0.8rem;color:#64748b;">'
                f'<span style="font-weight:600;color:#94a3b8;">Citations:</span> '
                f'{cite_html}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="font-size:0.8rem;color:#64748b;margin-top:4px;">'
                'Citations: --</div>',
                unsafe_allow_html=True,
            )

    if audit_id:
        st.markdown(
            f'<div style="font-size:0.7rem;color:#475569;margin-top:6px;">'
            f'Audit record: <code style="color:#64748b;">{audit_id}</code></div>',
            unsafe_allow_html=True,
        )


def render_chat_tab() -> None:
    """Render the Chat tab with message history and pinned input."""

    # Header
    st.markdown("""
    <div style="background:linear-gradient(135deg,#1e3a5f,#1e2235);
        border:1px solid #2d3148;border-radius:14px;padding:20px 24px;margin-bottom:20px;">
        <div style="font-size:1.3rem;font-weight:800;color:#f1f5f9;">
            Compliance Chat
        </div>
        <div style="font-size:0.85rem;color:#94a3b8;margin-top:4px;">
            Answers are grounded exclusively in your ingested policy documents.
            No general knowledge. Every interaction is audit-logged.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Suggested questions (only shown when chat is empty)
    if not st.session_state.chat_history:
        st.markdown(
            '<div style="font-size:0.8rem;color:#64748b;margin-bottom:8px;'
            'font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">'
            'Try asking</div>',
            unsafe_allow_html=True,
        )
        suggestions = [
            "What is the retention period for customer KYC records?",
            "What are the GDPR obligations for data breach notification?",
            "What are the SAR filing requirements?",
            "How long must employee records be kept?",
        ]
        cols = st.columns(2)
        for i, s in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(s, key=f"sug_{i}", use_container_width=True):
                    st.session_state.chat_history.append(
                        {"role": "user", "content": s, "meta": None}
                    )
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

    # Message history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("meta"):
                _render_answer_meta(msg["meta"])

    # Input
    query = st.chat_input("Ask a compliance question...")

    # Handle suggestion clicks that populated history without an answer yet
    if (
        not query
        and st.session_state.chat_history
        and st.session_state.chat_history[-1]["role"] == "user"
        and st.session_state.chat_history[-1].get("meta") is None
        and len(st.session_state.chat_history) % 2 == 1
    ):
        query = st.session_state.chat_history[-1]["content"]
        st.session_state.chat_history.pop()

    if query:
        with st.chat_message("user"):
            st.markdown(query)
        st.session_state.chat_history.append(
            {"role": "user", "content": query, "meta": None}
        )

        with st.chat_message("assistant"):
            with st.spinner("Searching policies..."):
                try:
                    state = run_query(query)
                except Exception as exc:
                    st.error(f"Pipeline error: {exc}")
                    return

            final_answer = state["final_answer"]
            routing      = state["routing"]
            citations    = state["retrieval"].citations
            topic        = state["classification"].topic
            stakes       = state["classification"].stakes
            audit_id     = state.get("audit_id", "")

            # Style box around the answer body
            box_colour = {
                "answered":              "#1e3a2f",
                "escalated_with_answer": "#3a2e1e",
                "escalated":             "#3a1e1e",
                "refused":               "#1e2235",
            }.get(routing, "#1e2235")
            border_colour = {
                "answered":              "#16a34a",
                "escalated_with_answer": "#d97706",
                "escalated":             "#dc2626",
                "refused":               "#475569",
            }.get(routing, "#475569")

            st.markdown(
                f'<div style="background:{box_colour};border-left:3px solid {border_colour};'
                f'border-radius:0 10px 10px 0;padding:14px 18px;margin:4px 0;">'
                f'{final_answer}</div>',
                unsafe_allow_html=True,
            )

            meta = {
                "routing": routing, "citations": citations,
                "topic": topic, "stakes": stakes, "audit_id": audit_id,
            }
            _render_answer_meta(meta)

        st.session_state.chat_history.append(
            {"role": "assistant", "content": final_answer, "meta": meta}
        )



# ---------------------------------------------------------------------------
# Tab 2: Pending Human Review
# ---------------------------------------------------------------------------

def render_pending_review_tab() -> None:
    """Render a card-based list of queries pending human review."""

    st.markdown("""
    <div style="background:linear-gradient(135deg,#2e1a47,#1e2235);
        border:1px solid #4c1d95;border-radius:14px;padding:20px 24px;margin-bottom:20px;">
        <div style="font-size:1.3rem;font-weight:800;color:#f1f5f9;">
            Pending Human Review
        </div>
        <div style="font-size:0.85rem;color:#a78bfa;margin-top:4px;">
            High-stakes queries are withheld from users until a compliance officer reviews them.
            Medium-stakes queries are answered with a disclaimer and flagged here.
        </div>
    </div>
    """, unsafe_allow_html=True)

    records = read_pending_review()

    if not records:
        st.markdown("""
        <div style="background:#1e2235;border:1px solid #2d3148;border-radius:12px;
            padding:40px;text-align:center;">
            <div style="font-size:2rem;">✓</div>
            <div style="color:#16a34a;font-weight:700;font-size:1.1rem;margin-top:8px;">
                Queue is clear
            </div>
            <div style="color:#64748b;font-size:0.85rem;margin-top:4px;">
                No queries are currently awaiting review.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Summary bar
    n_high = sum(1 for r in records if r.get("stakes") == "high")
    n_med  = sum(1 for r in records if r.get("stakes") == "medium")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total pending",   len(records))
    c2.metric("High stakes",     n_high)
    c3.metric("Medium stakes",   n_med)

    st.divider()

    # Table view
    df = pd.DataFrame(records)
    display = df.copy()
    display["query"] = display["query"].str[:100] + "..."
    cols = [c for c in ["timestamp", "topic", "stakes", "routing", "query", "id"] if c in display.columns]
    st.dataframe(display[cols], use_container_width=True, hide_index=True)

    st.divider()
    st.markdown(
        '<div style="font-size:0.85rem;font-weight:700;color:#a78bfa;margin-bottom:12px;">'
        'Record details</div>',
        unsafe_allow_html=True,
    )

    # Cards — most recent first
    for record in sorted(records, key=lambda r: r.get("timestamp",""), reverse=True):
        ts      = record.get("timestamp", "")[:19].replace("T", " ")
        routing = record.get("routing", "")
        stakes  = record.get("stakes", "")
        topic   = record.get("topic", "")

        border = "#dc2626" if stakes == "high" else "#d97706"
        label  = (
            f"{ts}  |  {topic}  |  "
            + record.get("query", "")[:70]
        )

        with st.expander(label):
            col_l, col_r = st.columns([2, 1])
            with col_l:
                st.markdown(f"**Query**")
                st.markdown(
                    f'<div style="background:#0f1117;border:1px solid #2d3148;'
                    f'border-radius:8px;padding:10px 14px;color:#cbd5e1;">'
                    f'{record.get("query","")}</div>',
                    unsafe_allow_html=True,
                )
                answer = record.get("answer", "")
                if answer:
                    st.markdown("<br>**Draft answer**", unsafe_allow_html=True)
                    st.markdown(
                        f'<div style="background:#1e2e1e;border-left:3px solid #d97706;'
                        f'border-radius:0 8px 8px 0;padding:12px 16px;color:#e2e8f0;'
                        f'font-size:0.9rem;">{answer}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div style="background:#2a1e1e;border:1px solid #7f1d1d;'
                        'border-radius:8px;padding:10px 14px;color:#fca5a5;font-size:0.85rem;">'
                        'Answer withheld -- high-stakes escalation pending review.</div>',
                        unsafe_allow_html=True,
                    )

            with col_r:
                st.markdown(
                    _badge_html(routing) + "&nbsp;" + _topic_chip(topic) + "&nbsp;" + _stakes_chip(stakes),
                    unsafe_allow_html=True,
                )
                st.markdown("")
                cites = record.get("citations", [])
                if cites:
                    st.markdown("**Citations**")
                    for c in cites:
                        st.markdown(
                            f'<code style="background:#1e3a5f;color:#93c5fd;'
                            f'border-radius:4px;padding:2px 7px;font-size:0.75rem;'
                            f'display:inline-block;margin:2px 0;">{c}</code>',
                            unsafe_allow_html=True,
                        )
                reason = record.get("escalation_reason")
                if reason:
                    st.markdown(
                        f'<div style="margin-top:8px;font-size:0.78rem;color:#94a3b8;">'
                        f'<span style="font-weight:600;">Reason:</span> {reason}</div>',
                        unsafe_allow_html=True,
                    )
                st.markdown(
                    f'<div style="margin-top:10px;font-size:0.7rem;color:#475569;">'
                    f'ID: <code style="color:#64748b;">{record.get("id","")[:16]}...</code><br>'
                    f'{ts}</div>',
                    unsafe_allow_html=True,
                )



# ---------------------------------------------------------------------------
# Tab 3: Audit Log
# ---------------------------------------------------------------------------

def render_audit_log_tab() -> None:
    """Render full audit log with filter controls and record detail cards."""

    st.markdown("""
    <div style="background:linear-gradient(135deg,#1a2e1a,#1e2235);
        border:1px solid #14532d;border-radius:14px;padding:20px 24px;margin-bottom:20px;">
        <div style="font-size:1.3rem;font-weight:800;color:#f1f5f9;">
            Audit Log
        </div>
        <div style="font-size:0.85rem;color:#86efac;margin-top:4px;">
            Append-only record of every query processed by the pipeline.
            Tamper-evident -- stored in <code style="color:#4ade80;">data/audit_log.jsonl</code>.
        </div>
    </div>
    """, unsafe_allow_html=True)

    records = read_all_records()

    if not records:
        st.info("No audit records yet. Submit a query in the Chat tab to get started.")
        return

    df = pd.DataFrame(records)
    total = len(df)

    # ── Metrics ──────────────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total",     total)
    m2.metric("Answered",  int((df["routing"] == "answered").sum()))
    m3.metric("Escalated", int(df["routing"].str.startswith("escalated").sum()))
    m4.metric("Refused",   int((df["routing"] == "refused").sum()))

    st.divider()

    # ── Filter bar ────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;'
        'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">Filters</div>',
        unsafe_allow_html=True,
    )
    fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 3])
    with fc1:
        sel_topic = st.multiselect(
            "Topic", sorted(df["topic"].unique().tolist()), key="filter_topic"
        )
    with fc2:
        sel_stakes = st.multiselect(
            "Stakes", ["low", "medium", "high"], key="filter_stakes"
        )
    with fc3:
        sel_routing = st.multiselect(
            "Routing",
            ["answered", "refused", "escalated", "escalated_with_answer"],
            key="filter_routing",
        )
    with fc4:
        search = st.text_input(
            "Search queries", placeholder="e.g. GDPR, SAR, retention..."
        )

    # ── Apply filters ─────────────────────────────────────────────────────────
    filtered = df.copy()
    if sel_topic:
        filtered = filtered[filtered["topic"].isin(sel_topic)]
    if sel_stakes:
        filtered = filtered[filtered["stakes"].isin(sel_stakes)]
    if sel_routing:
        filtered = filtered[filtered["routing"].isin(sel_routing)]
    if search:
        filtered = filtered[
            filtered["query"].str.contains(search, case=False, na=False)
        ]

    st.markdown(
        f'<div style="font-size:0.8rem;color:#64748b;margin:8px 0;">'
        f'Showing {len(filtered)} of {total} records</div>',
        unsafe_allow_html=True,
    )

    # ── Table ─────────────────────────────────────────────────────────────────
    display = filtered.copy()
    display["query"] = display["query"].str[:90] + "..."
    show_cols = [c for c in ["timestamp","id","topic","stakes","routing","query"]
                 if c in display.columns]
    st.dataframe(display[show_cols], use_container_width=True, hide_index=True)

    st.divider()
    st.markdown(
        '<div style="font-size:0.85rem;font-weight:700;color:#86efac;margin-bottom:12px;">'
        'Record details (50 most recent)</div>',
        unsafe_allow_html=True,
    )

    # ── Detail cards ──────────────────────────────────────────────────────────
    for _, row in filtered.sort_values("timestamp", ascending=False).head(50).iterrows():
        ts      = str(row.get("timestamp", ""))[:19].replace("T", " ")
        routing = str(row.get("routing", ""))
        stakes  = str(row.get("stakes", ""))
        topic   = str(row.get("topic", ""))
        label   = f"{ts}  |  {topic}  |  {routing}  |  {str(row.get('query',''))[:70]}"

        with st.expander(label):
            col_l, col_r = st.columns([2, 1])
            with col_l:
                st.markdown("**Query**")
                st.markdown(
                    f'<div style="background:#0f1117;border:1px solid #2d3148;'
                    f'border-radius:8px;padding:10px 14px;color:#cbd5e1;">'
                    f'{row.get("query","")}</div>',
                    unsafe_allow_html=True,
                )
                answer = str(row.get("answer", ""))
                if answer:
                    box_bg = {
                        "answered":              "#1e3a2f",
                        "escalated_with_answer": "#3a2e1e",
                        "escalated":             "#3a1e1e",
                        "refused":               "#1e2235",
                    }.get(routing, "#1e2235")
                    box_border = {
                        "answered":              "#16a34a",
                        "escalated_with_answer": "#d97706",
                        "escalated":             "#dc2626",
                        "refused":               "#475569",
                    }.get(routing, "#475569")
                    st.markdown("<br>**Answer**", unsafe_allow_html=True)
                    st.markdown(
                        f'<div style="background:{box_bg};border-left:3px solid {box_border};'
                        f'border-radius:0 8px 8px 0;padding:12px 16px;color:#e2e8f0;'
                        f'font-size:0.9rem;">{answer}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div style="color:#64748b;font-size:0.85rem;margin-top:8px;">'
                        'No answer -- refused or escalated without answer.</div>',
                        unsafe_allow_html=True,
                    )

            with col_r:
                st.markdown(
                    _badge_html(routing) + "&nbsp;" + _topic_chip(topic) + "&nbsp;" + _stakes_chip(stakes),
                    unsafe_allow_html=True,
                )
                st.markdown("")
                cites = row.get("citations", [])
                if isinstance(cites, list) and cites:
                    st.markdown("**Citations**")
                    for c in cites:
                        st.markdown(
                            f'<code style="background:#1e3a5f;color:#93c5fd;'
                            f'border-radius:4px;padding:2px 7px;font-size:0.75rem;'
                            f'display:inline-block;margin:2px 0;">{c}</code>',
                            unsafe_allow_html=True,
                        )
                reason = row.get("escalation_reason")
                if reason and str(reason) != "None":
                    st.markdown(
                        f'<div style="margin-top:8px;font-size:0.78rem;color:#94a3b8;">'
                        f'<span style="font-weight:600;">Reason:</span> {reason}</div>',
                        unsafe_allow_html=True,
                    )
                st.markdown(
                    f'<div style="margin-top:10px;font-size:0.7rem;color:#475569;">'
                    f'ID: <code style="color:#64748b;">{str(row.get("id",""))[:16]}...</code><br>'
                    f'{ts} UTC</div>',
                    unsafe_allow_html=True,
                )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    init_session_state()
    render_sidebar()

    st.markdown("""
    <div style="margin-bottom:6px;">
        <span style="font-size:1.7rem;font-weight:900;color:#f1f5f9;">
            Compliance Advisory &amp; Triage Agent
        </span><br>
        <span style="font-size:0.82rem;color:#64748b;">
            Grounded in your policy documents &nbsp;·&nbsp;
            Audit-logged &nbsp;·&nbsp; Human-in-the-loop escalation
        </span>
    </div>
    """, unsafe_allow_html=True)

    tab_chat, tab_review, tab_audit = st.tabs(
        ["  Chat  ", "  Pending Review  ", "  Audit Log  "]
    )

    with tab_chat:
        render_chat_tab()
    with tab_review:
        render_pending_review_tab()
    with tab_audit:
        render_audit_log_tab()


if __name__ == "__main__":
    main()
