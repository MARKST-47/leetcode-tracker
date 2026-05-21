# dashboard.py
import datetime
import sqlite3
import streamlit as st
import pandas as pd

DB_PATH = "tracker.db"

# Page Configuration for a modern look
st.set_page_config(
    page_title="LeetCode Spaced Repetition Tracker",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling to make it look clean and visually appealing
st.markdown("""
    <style>
    .metric-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
        text-align: center;
    }
    .stDataFrame {
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def load_metrics():
    """Calculates top-level overview data."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Total solved
        cursor.execute("SELECT COUNT(*) FROM problems")
        total_solved = cursor.fetchone()[0]
        
        # Solved today
        cursor.execute("SELECT COUNT(*) FROM problems WHERE last_solved >= ?", (today_start,))
        solved_today = cursor.fetchone()[0]
        
        # Due for review
        cursor.execute("SELECT COUNT(*) FROM problems WHERE next_review <= ?", (now,))
        due_count = cursor.fetchone()[0]
        
    return total_solved, solved_today, due_count

def load_problems(due_only=False):
    """Loads problems into a pandas DataFrame for pretty display."""
    query = "SELECT id, title, difficulty, tags, last_solved, next_review, interval, repetitions, notes FROM problems"
    if due_only:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query += f" WHERE next_review <= '{now}'"
    
    with get_db_connection() as conn:
        df = pd.read_sql_query(query, conn)
        
    # Clean up dates for user viewing
    if not df.empty:
        df['last_solved'] = pd.to_datetime(df['last_solved']).dt.strftime('%Y-%m-%d %H:%M')
        df['next_review'] = pd.to_datetime(df['next_review']).dt.strftime('%Y-%m-%d')
    return df

st.title("🧠 LeetCode Spaced Repetition Companion")
st.subheader("Mastering algorithms through active recall.")
st.markdown("---")

# 1. Top Level Metrics Layout
total, today, due = load_metrics()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Total Problems Tracked", value=total)
with col2:
    st.metric(label="Solved Today", value=today, delta=f"+{today}" if today > 0 else None)
with col3:
    st.metric(label="Reviews Due Today", value=due, delta=f"{due} pending" if due > 0 else "All caught up!", delta_color="inverse" if due > 0 else "normal")

st.markdown("---")

# 2. Daily Active Recall Queue Section
st.header("📋 Today's Review Queue")
due_df = load_problems(due_only=True)

if due_df.empty:
    st.success("🎉 Incredible job! Your review queue is completely empty for today.")
else:
    st.write("These problems are due for spacing intervals. Re-solve them to lock down the patterns.")
    
    # Format difficulty styling cleanly
    def color_difficulty(val):
        if val == 'Easy': return 'color: green; font-weight: bold;'
        elif val == 'Medium': return 'color: orange; font-weight: bold;'
        elif val == 'Hard': return 'color: red; font-weight: bold;'
        return ''
        
    st.dataframe(
        due_df[['id', 'title', 'difficulty', 'tags', 'interval', 'repetitions', 'notes']].style.map(color_difficulty, subset=['difficulty']),
        use_container_width=True,
        hide_index=True
    )

st.markdown("---")

# 3. Interactive Sidebar to update notes manually
st.sidebar.header("Update Problem Record")
st.sidebar.write("Refine parameters or update details after a manual review:")

all_df = load_problems(due_only=False)

if not all_df.empty:
    problem_options = all_df.apply(lambda row: f"{row['id']} - {row['title']}", axis=1).tolist()
    selected_problem_str = st.sidebar.selectbox("Select Problem", problem_options)
    selected_id = int(selected_problem_str.split(" - ")[0])
    
    current_row = all_df[all_df['id'] == selected_id].iloc[0]
    
    # Input options for editing notes
    new_notes = st.sidebar.text_area("Approach Notes / Intuition Key", value=current_row['notes'])
    quality = st.sidebar.slider(
        "Performance Rating (SM-2)", 
        min_value=1, max_value=5, value=3,
        help="1=Forgot totally, 3=Solved with major hiccups, 5=Flawless instant solution"
    )
    
    if st.sidebar.button("Save Updates"):
        # Make a background patch call to your backend architecture or execute SQLite safely directly
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # If performance rating is lower than 3, adjust review interval schedules instantly
            now = datetime.datetime.now()
            from scheduler import calculate_next_review
            
            cursor.execute("SELECT interval, ease_factor, repetitions FROM problems WHERE id = ?", (selected_id,))
            interval, ef, reps = cursor.fetchone()
            
            new_interval, new_ef, new_reps = calculate_next_review(interval, ef, reps, quality)
            next_review_date = now + datetime.timedelta(days=new_interval)
            
            cursor.execute("""
                UPDATE problems 
                SET notes = ?, interval = ?, ease_factor = ?, repetitions = ?, next_review = ?
                WHERE id = ?
            """, (new_notes, new_interval, new_ef, new_reps, next_review_date, selected_id))
            conn.commit()
            
        st.sidebar.success("Problem specs patched successfully!")
        st.rerun()
else:
    st.sidebar.info("No problems logged yet. Complete a submission on LeetCode to populate metrics!")

# 4. Master Problem History View
st.header("🗄️ Full Database History")
if not all_df.empty:
    st.dataframe(all_df, use_container_width=True, hide_index=True)
else:
    st.info("Your database workspace is currently empty.")