# dashboard.py
import datetime
import sqlite3
import streamlit as st
import pandas as pd

DB_PATH = "tracker.db"

st.set_page_config(
    page_title="LeetCode SR Hub",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Outfit:wght@300;400;500;600;700&display=swap');

/* ── Base ────────────────────────────────────────────────── */
html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }

/* Fix heading-cut: Streamlit's sticky toolbar is ~58px. 4rem clears it safely. */
.block-container {
    padding-top: 4rem !important;
    padding-bottom: 2rem !important;
    max-width: 97% !important;
}
[data-testid="stAppViewBlockContainer"] > div:first-child { padding-top: 0 !important; }

/* ── Page header ─────────────────────────────────────────── */
.sr-header {
    display: flex; align-items: center; gap: 14px;
    padding: 18px 22px;
    background: linear-gradient(135deg, #0f172a 0%, #1a2744 60%, #0f2027 100%);
    border: 1px solid #1e3a5f; border-radius: 12px; margin-bottom: 18px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(99,179,237,0.07);
}
.sr-header-icon { font-size: 2.2rem; line-height: 1; }
.sr-header-text h1 {
    margin: 0 !important; padding: 0 !important;
    font-size: 1.65rem !important; font-weight: 700 !important;
    color: #f1f5f9 !important; letter-spacing: -0.02em; line-height: 1.15 !important;
}
.sr-header-text p {
    margin: 3px 0 0 0; font-size: 0.8rem;
    color: #64748b; font-weight: 400; letter-spacing: 0.03em;
}
.sr-header-badge {
    margin-left: auto;
    background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3);
    color: #4ade80; padding: 4px 12px; border-radius: 20px;
    font-size: 0.72rem; font-family: 'JetBrains Mono', monospace;
    font-weight: 600; letter-spacing: 0.05em; white-space: nowrap;
}

/* ── Metric cards ────────────────────────────────────────── */
[data-testid="metric-container"] {
    background: #1e293b; border: 1px solid #334155;
    border-radius: 10px; padding: 14px 18px !important;
    transition: border-color 0.2s, box-shadow 0.2s;
}
[data-testid="metric-container"]:hover {
    border-color: #475569; box-shadow: 0 0 0 1px rgba(56,189,248,0.08);
}
[data-testid="stMetricLabel"] {
    font-size: 0.72rem !important; color: #64748b !important;
    font-weight: 500 !important; letter-spacing: 0.05em; text-transform: uppercase;
}
[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 2rem !important; font-weight: 600 !important;
    color: #f1f5f9 !important; line-height: 1.1 !important;
}
[data-testid="stMetricDelta"] {
    font-family: 'JetBrains Mono', monospace !important; font-size: 0.72rem !important;
}

/* ── Controls panel label ────────────────────────────────── */
.sr-section-title {
    font-size: 0.68rem; font-weight: 600; letter-spacing: 0.12em;
    text-transform: uppercase; color: #475569;
    padding: 8px 0 8px 2px; border-bottom: 1px solid #1e293b; margin-bottom: 10px;
}

/* ── Tabs ────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tab"] {
    font-size: 0.82rem; font-weight: 500;
    color: #64748b; padding: 6px 14px; letter-spacing: 0.02em;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] { color: #38bdf8 !important; font-weight: 600; }
[data-testid="stTabs"] [role="tablist"] { border-bottom: 1px solid #1e293b; }

/* ── Buttons ─────────────────────────────────────────────── */
[data-testid="baseButton-secondary"] {
    background: #1e293b !important; border: 1px solid #334155 !important;
    color: #94a3b8 !important; font-size: 0.82rem !important;
    font-weight: 500 !important; border-radius: 7px !important; transition: all 0.15s !important;
}
[data-testid="baseButton-secondary"]:hover {
    background: #334155 !important; border-color: #475569 !important; color: #f1f5f9 !important;
}
[data-testid="baseButton-primary"] { border-radius: 7px !important; font-size: 0.82rem !important; font-weight: 600 !important; }

/* ── Alert / info / success boxes ───────────────────────── */
[data-testid="stAlert"] { border-radius: 8px; font-size: 0.83rem; padding: 10px 14px !important; }

/* ── Expanders ───────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #1e293b !important; border-radius: 8px !important; background: #0f172a !important;
}
[data-testid="stExpander"] summary {
    font-size: 0.83rem !important; font-weight: 500 !important;
    color: #94a3b8 !important; padding: 8px 12px !important;
}

/* ── Text area ───────────────────────────────────────────── */
[data-testid="stTextArea"] textarea {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.77rem !important; background: #1e293b !important;
    border-color: #334155 !important; color: #e2e8f0 !important; border-radius: 7px !important;
}

/* ── Typography ──────────────────────────────────────────── */
h2, h3 { font-size: 0.95rem !important; font-weight: 600 !important; color: #94a3b8 !important; margin-top: 0 !important; }
hr { border-color: #1e293b !important; margin: 10px 0 !important; }
[data-testid="stCaptionContainer"] { color: #475569 !important; font-size: 0.76rem !important; }
</style>
""", unsafe_allow_html=True)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def calculate_streak(conn) -> int:
    """
    Returns the current solve-day streak.

    Bug fixed: the original had a dead `elif d == check_date + timedelta(days=1)`
    branch. Because dates_list is sorted DESC and we decrement check_date on every
    match, that condition can never be True for consecutive dates. Removed it so
    the loop breaks correctly on any gap.
    """
    rows = conn.execute(
        "SELECT DISTINCT date(last_solved) AS solve_date FROM problems ORDER BY solve_date DESC"
    ).fetchall()
    dates_list = [
        datetime.datetime.strptime(r["solve_date"], "%Y-%m-%d").date() for r in rows
    ]

    if not dates_list:
        return 0

    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    # Streak is only active if the user solved something today or yesterday.
    if dates_list[0] not in (today, yesterday):
        return 0

    streak = 0
    check_date = dates_list[0]  # Start from the most recent solve date.
    for d in dates_list:
        if d == check_date:
            streak += 1
            check_date -= datetime.timedelta(days=1)
        else:
            break  # Gap found — streak ends.

    return streak


def fetch_dashboard_data():
    now = datetime.datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    with get_db_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
        solved_today = conn.execute(
            "SELECT COUNT(*) FROM problems WHERE last_solved >= ?", (today_start,)
        ).fetchone()[0]

        streak = calculate_streak(conn)

        # Bug fixed: previously used an f-string to interpolate `now` into the SQL,
        # which is bad practice. Now uses a parameterized query.
        # Also: the INNER JOIN ensures we only evaluate the latest solve per problem,
        # preventing a problem solved 5 times from appearing 5 times in the queue.
        due_df = pd.read_sql_query(
            """
            SELECT p.id, p.title, p.difficulty, p.tags, p.interval, p.repetitions, p.notes
            FROM problems p
            INNER JOIN (
                SELECT title, MAX(last_solved) AS max_solved
                FROM problems
                GROUP BY title
            ) latest
              ON p.title = latest.title
             AND p.last_solved = latest.max_solved
            WHERE p.next_review <= ?
            ORDER BY p.next_review ASC
            """,
            conn,
            params=(now,),
        )

        history_df = pd.read_sql_query(
            """
            SELECT id, title, difficulty, tags, last_solved, next_review, interval, notes
            FROM problems
            ORDER BY id DESC
            """,
            conn,
        )

    if not history_df.empty:
        history_df["last_solved"] = pd.to_datetime(history_df["last_solved"]).dt.strftime("%m-%d %H:%M")
        history_df["next_review"] = pd.to_datetime(history_df["next_review"]).dt.strftime("%m-%d")

    return total, solved_today, len(due_df), streak, due_df, history_df


# ── Load data ────────────────────────────────────────────────────────────────
total, today_count, due, streak, due_df, history_df = fetch_dashboard_data()

# ── Header ───────────────────────────────────────────────────────────────────
# Using a custom HTML block instead of st.title() so the heading is never
# clipped by Streamlit's sticky toolbar regardless of screen DPI or zoom level.
now_str = datetime.datetime.now().strftime("%a %d %b · %H:%M")
st.markdown(f"""
<div class="sr-header">
    <div class="sr-header-icon">🧠</div>
    <div class="sr-header-text">
        <h1>LeetCode Spaced Repetition</h1>
        <p>Active recall scheduler · SM-2 algorithm</p>
    </div>
    <div class="sr-header-badge">● LIVE · {now_str}</div>
</div>
""", unsafe_allow_html=True)

# ── Metric row ────────────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("🔥 Day Streak", f"{streak}", help="Consecutive days with at least one submission")
with m2:
    st.metric("📋 Total Submissions", total, help="All logged submission rows")
with m3:
    st.metric("✅ Solved Today", today_count)
with m4:
    st.metric(
        "⏳ Due for Review", due,
        delta=f"{due} overdue" if due > 0 else "all clear",
        delta_color="inverse",
        help="Problems whose next_review date has passed",
    )

st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

# ── Main layout ───────────────────────────────────────────────────────────────
data_col, ctrl_col = st.columns([2.4, 1])

with data_col:
    tab1, tab2 = st.tabs(["🗓️  Review Queue", "🗄️  Submission History"])

    with tab1:
        if due_df.empty:
            st.success("🎉 Queue empty — all patterns locked in. Come back tomorrow!")
        else:
            st.caption(f"{due} problem{'s' if due != 1 else ''} awaiting active recall · sorted by urgency")
            st.dataframe(due_df, use_container_width=True, hide_index=True, height=260)

    with tab2:
        if not history_df.empty:
            st.caption("💡 Check a row's box to load it into the controls panel →")
            history_df.insert(0, "✔", False)
            edited_df = st.data_editor(
                history_df,
                use_container_width=True,
                hide_index=True,
                height=340,
                column_config={"✔": st.column_config.CheckboxColumn(width="small")},
                disabled=["id", "title", "difficulty", "tags", "last_solved", "next_review", "interval"],
            )
            selected_rows = edited_df[edited_df["✔"] == True]
        else:
            st.info("No history yet — solve a problem and the logger will populate this.")
            selected_rows = pd.DataFrame()

with ctrl_col:
    st.markdown('<div class="sr-section-title">⚙ Controls</div>', unsafe_allow_html=True)

    if not selected_rows.empty:
        target_id    = int(selected_rows.iloc[0]["id"])
        target_title = selected_rows.iloc[0]["title"]
        target_notes = selected_rows.iloc[0]["notes"] or ""

        st.info(f"**#{target_id}** · {target_title}")

        with st.expander("📝 Edit Notes", expanded=True):
            updated_notes = st.text_area(
                "notes",
                value=target_notes,
                height=110,
                label_visibility="collapsed",
                placeholder="e.g. Two-pointer O(n) · watch left == right edge case",
            )
            if st.button("💾  Save Notes", use_container_width=True):
                with get_db_connection() as conn:
                    conn.execute(
                        "UPDATE problems SET notes = ? WHERE id = ?",
                        (updated_notes, target_id),
                    )
                    conn.commit()
                st.success("Saved!")
                st.rerun()

        st.markdown("<div style='margin-top:6px'></div>", unsafe_allow_html=True)

        with st.expander("⚠️  Delete Entry"):
            st.warning(f"Remove row **{target_id}** permanently?")
            if st.button("🗑  Delete Row", use_container_width=True, type="primary"):
                with get_db_connection() as conn:
                    conn.execute("DELETE FROM problems WHERE id = ?", (target_id,))
                    conn.commit()
                st.success(f"Row {target_id} removed.")
                st.rerun()
    else:
        st.markdown("""
        <div style='
            background:#0f172a; border:1px dashed #1e293b; border-radius:10px;
            padding:28px 16px; text-align:center; color:#334155;
            font-size:0.8rem; line-height:1.7;
        '>
            ← Check a row in<br>the History tab to load<br>edit &amp; delete tools
        </div>
        """, unsafe_allow_html=True)
