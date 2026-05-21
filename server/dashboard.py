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
    initial_sidebar_state="collapsed" # Maximizes horizontal workspace immediately
)

# Tight CSS to compress padding, margins, and excess whitespace
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; max-width: 95%; }
    div.stForm { padding: 10px; border-radius: 8px; }
    h1 { margin-bottom: 0rem; padding-bottom: 0rem; font-size: 2rem !important; }
    h2 { margin-top: 0.5rem; margin-bottom: 0.5rem; font-size: 1.3rem !important; }
    h3 { font-size: 1.1rem !important; }
    .stMetric { background-color: #1e293b; padding: 8px 12px; border-radius: 6px; color: white; }
    div[data-testid="stVerticalBlock"] > div { margin-bottom: -0.3rem; }
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
        due = conn.execute("SELECT COUNT(*) FROM problems WHERE next_review <= ?", (now,)).fetchone()[0]
        
        # Streak Tracker
        all_dates = conn.execute("SELECT DISTINCT date(last_solved) as solve_date FROM problems ORDER BY solve_date DESC").fetchall()
        dates_list = [datetime.datetime.strptime(x['solve_date'], "%Y-%m-%d").date() for x in all_dates]
        streak = 0
        check_date = datetime.date.today()
        if dates_list and (dates_list[0] == check_date or dates_list[0] == check_date - datetime.timedelta(days=1)):
            for d in dates_list:
                if d == check_date: streak += 1; check_date -= datetime.timedelta(days=1)
                elif d == check_date + datetime.timedelta(days=1): continue
                else: break
        
        due_df = pd.read_sql_query(f"SELECT title, difficulty, tags, interval, repetitions, notes FROM problems WHERE next_review <= '{now}'", conn)
        history_df = pd.read_sql_query("SELECT title, difficulty, tags, last_solved, next_review, interval, repetitions, notes FROM problems ORDER BY last_solved DESC", conn)
        
    if not history_df.empty:
        history_df['last_solved'] = pd.to_datetime(history_df['last_solved']).dt.strftime('%m-%d %H:%M')
        history_df['next_review'] = pd.to_datetime(history_df['next_review']).dt.strftime('%m-%d')
        
    return total, solved_today, due, streak, due_df, history_df

def color_difficulty(val):
    if val == 'Easy': return 'color: #22c55e; font-weight: bold;'
    elif val == 'Medium': return 'color: #eab308; font-weight: bold;'
    elif val == 'Hard': return 'color: #ef4444; font-weight: bold;'
    return ''

# --- Load Application State ---
total, today, due, streak, due_df, history_df = fetch_dashboard_data()

# Header banner row
st.title("🧠 LeetCode Spaced Repetition Workstation")
st.markdown("---")

# Compact Metric strip layout
m1, m2, m3, m4 = st.columns(4)
with m1: st.metric("🔥 Streak", f"{streak} Days")
with m2: st.metric("📋 Total Tracked", total)
with m3: st.metric("✅ Solved Today", today)
with m4: st.metric("⏳ Queue Pending", due, delta=f"{due} Due" if due > 0 else None, delta_color="inverse")

st.markdown("##")

# Side-by-side Layout to maximize spacing use
data_column, control_column = st.columns([2.2, 1])

with data_column:
    # Use clean tab layouts to prevent vertical page bloat
    tab1, tab2 = st.tabs(["🗓️ Active Review Queue", "🗄️ System Database Log"])
    
    with tab1:
        if due_df.empty:
            st.success("🎉 Review queue is empty! Patterns locked down.")
        else:
            st.dataframe(
                due_df.style.map(color_difficulty, subset=['difficulty']),
                use_container_width=True, hide_index=True, height=280
            )
            
    with tab2:
        if not history_df.empty:
            st.dataframe(
                history_df.style.map(color_difficulty, subset=['difficulty']),
                use_container_width=True, hide_index=True, height=350
            )
        else:
            st.info("System workspace is currently empty.")

with control_column:
    st.subheader("⚙️ Workspace Operations")
    
    if not history_df.empty:
        problem_list = history_df['title'].unique().tolist()
        selected_title = st.selectbox("Select Target Problem:", problem_list)
        
        current_row = history_df[history_df['title'] == selected_title].iloc[0]
        
        # Sub-Action 1: Clean Edit Panel
        with st.expander("📝 Edit Notes / SM-2 Interval", expanded=True):
            updated_notes = st.text_area("Intuition Keys:", value=current_row['notes'], height=70)
            quality = st.slider("Performance Score:", 1, 5, 3, help="5=Perfect, 1=Total blackout")
            
            if st.button("Save Entry Modifications", use_container_width=True):
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT interval, ease_factor, repetitions FROM problems WHERE title = ?", (selected_title,))
                    interval, ef, reps = cursor.fetchone()
                    
                    from scheduler import calculate_next_review
                    new_interval, new_ef, new_reps = calculate_next_review(interval, ef, reps, quality)
                    next_review_date = datetime.datetime.now() + datetime.timedelta(days=new_interval)
                    
                    conn.execute("""
                        UPDATE problems SET notes = ?, interval = ?, ease_factor = ?, repetitions = ?, next_review = ?
                        WHERE title = ?
                    """, (updated_notes, new_interval, new_ef, new_reps, next_review_date, selected_title))
                    conn.commit()
                st.success("Record modified!")
                st.rerun()
                
        # Sub-Action 2: Clean Eraser Tool to clear duplicates or bad logs instantly
        with st.expander("⚠️ Danger Zone"):
            st.warning(f"Delete '{selected_title}' permanently?")
            if st.button("Confirm Delete Record", use_container_width=True, type="primary"):
                with get_db_connection() as conn:
                    conn.execute("DELETE FROM problems WHERE title = ?", (selected_title,))
                    conn.commit()
                st.success("Record deleted successfully.")
                st.rerun()
    else:
        st.info("Log records via LeetCode to display control properties.")