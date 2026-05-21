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
    initial_sidebar_state="collapsed"
)

# Ultra-compressed custom spatial properties styling sheet
st.markdown("""
    <style>
    .block-container { padding-top: 0.8rem; padding-bottom: 0.5rem; max-width: 96%; }
    h1 { margin-bottom: -0.5rem; padding-bottom: 0rem; font-size: 1.8rem !important; }
    h2 { margin-top: 0.3rem; margin-bottom: 0.3rem; font-size: 1.2rem !important; }
    .stMetric { background-color: #1e293b; padding: 6px 12px; border-radius: 6px; color: white; }
    div[data-testid="stVerticalBlock"] > div { margin-bottom: -0.5rem; }
    button[data-testid="baseButton-secondary"] { margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_dashboard_data():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    
    with get_db_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
        solved_today = conn.execute("SELECT COUNT(*) FROM problems WHERE last_solved >= ?", (today_start,)).fetchone()[0]
        
        # Smart Queue Fetcher: Evaluate reviews based ONLY on the absolute latest solve session entry of each problem name
        due_query = f"""
            SELECT p.id, p.title, p.difficulty, p.tags, p.interval, p.repetitions, p.notes
            FROM problems p
            INNER JOIN (
                SELECT title, MAX(last_solved) as max_solved 
                FROM problems GROUP BY title
            ) latest ON p.title = latest.title AND p.last_solved = latest.max_solved
            WHERE p.next_review <= '{now}'
        """
        due_df = pd.read_sql_query(due_query, conn)
        
        # Historical Data Frame loading down every submission chronologically matching user specifications
        history_df = pd.read_sql_query("SELECT id, title, difficulty, tags, last_solved, next_review, interval, notes FROM problems ORDER BY id DESC", conn)
        
        # Streak calculations based on unique chronological date clusters
        all_dates = conn.execute("SELECT DISTINCT date(last_solved) as solve_date FROM problems ORDER BY solve_date DESC").fetchall()
        dates_list = [datetime.datetime.strptime(x['solve_date'], "%Y-%m-%d").date() for x in all_dates]
        streak = 0
        check_date = datetime.date.today()
        if dates_list and (dates_list[0] == check_date or dates_list[0] == check_date - datetime.timedelta(days=1)):
            for d in dates_list:
                if d == check_date: streak += 1; check_date -= datetime.timedelta(days=1)
                elif d == check_date + datetime.timedelta(days=1): continue
                else: break
                
    if not history_df.empty:
        history_df['last_solved'] = pd.to_datetime(history_df['last_solved']).dt.strftime('%m-%d %H:%M')
        history_df['next_review'] = pd.to_datetime(history_df['next_review']).dt.strftime('%m-%d')
        
    return total, solved_today, len(due_df), streak, due_df, history_df

# Load System Values
total, today, due, streak, due_df, history_df = fetch_dashboard_data()

st.title("🧠 LeetCode Spaced Repetition Workstation")
st.markdown("---")

# Visual Metric Layout Panel Row
m1, m2, m3, m4 = st.columns(4)
with m1: st.metric("🔥 Streak", f"{streak} Days")
with m2: st.metric("📋 Total Submissions", total)
with m3: st.metric("✅ Solved Today", today)
with m4: st.metric("⏳ Queue Pending", due, delta=f"{due} Due" if due > 0 else None, delta_color="inverse")

st.markdown("##")

# Layout Segment Splitting Workspace
data_column, control_column = st.columns([2.3, 1])

with data_column:
    tab1, tab2 = st.tabs(["🗓️ Active Review Queue", "🗄️ Timeline Submission History Logs"])
    
    with tab1:
        if due_df.empty:
            st.success("🎉 Review queue is empty! Patterns locked down.")
        else:
            st.dataframe(due_df, width='stretch', hide_index=True, height=240)
            
    with tab2:
        if not history_df.empty:
            st.write("💡 *Check the box on any row below to queue it for modification or deletion operations.*")
            
            # Convert normal dataframe into a fully editable data matrix wrapper grid
            history_df.insert(0, "Select", False) # Prepend an interactive checkbox switch column
            edited_df = st.data_editor(
                history_df,
                width='stretch',
                hide_index=True,
                height=320,
                disabled=["id", "title", "difficulty", "tags", "last_solved", "next_review", "interval"]
            )
            
            # Harvest row lines where checkbox active state holds true
            selected_rows = edited_df[edited_df["Select"] == True]
        else:
            st.info("System timeline tracking log history is currently unpopulated.")
            selected_rows = pd.DataFrame()

with control_column:
    st.subheader("⚙️ Record Target Control Operations")
    
    if not selected_rows.empty:
        # Pull metadata context straight from the visually selected interactive grid checkbox row
        target_id = int(selected_rows.iloc[0]["id"])
        target_title = selected_rows.iloc[0]["title"]
        target_notes = selected_rows.iloc[0]["notes"]
        
        st.info(f"Target selected: **Row ID {target_id}** ({target_title})")
        
        # Action 1: Inline notes modifier patch matching selected ID row index
        with st.expander("📝 Edit Row Notes / Intuition", expanded=True):
            updated_notes = st.text_area("Intuition Track Update:", value=target_notes, height=70)
            if st.button("Save Notes Modifier", width='stretch'):
                with get_db_connection() as conn:
                    conn.execute("UPDATE problems SET notes = ? WHERE id = ?", (updated_notes, target_id))
                    conn.commit()
                st.success("Strategic insights patched!")
                st.rerun()
                
        # Action 2: Surgical target eraser block tool matching row unique primary key ID directly
        with st.expander("⚠️ Surgical Eraser Tool"):
            st.warning(f"Completely clear entry record row ID {target_id} from timeline history?")
            if st.button("Delete Selected Row ID", width='stretch', type="primary"):
                with get_db_connection() as conn:
                    conn.execute("DELETE FROM problems WHERE id = ?", (target_id,))
                    conn.commit()
                st.success(f"Row item {target_id} erased successfully!")
                st.rerun()
    else:
        st.info("Check a box on a history line item row to unlock data modifiers and specific deletion tools.")