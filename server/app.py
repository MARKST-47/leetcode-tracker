import datetime
import sqlite3
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from scheduler import calculate_next_review

app = FastAPI(title="Leetcode Spaced Repetition Companion Server")
DB_PATH = "tracker.db"

class SubmissionPayload(BaseModel):
    problem_id: int
    title: str
    difficulty: str
    tags: List[str]
    runtime_percentile: Optional[float] = 0.0
    memory_percentile: Optional[float] = 0.0
    lang: str
    notes: Optional[str] = ""
    quality_score: Optional[int] = 3  # Default to an average passing score if not provided

class UpdateNotesPayload(BaseModel):
    notes: str
    quality_score: int
    
# Database initialization
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS problems (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                difficulty TEXT,
                tags TEXT,
                last_solved TIMESTAMP,
                next_review TIMESTAMP,
                interval INTEGER DEFAULT 1,
                ease_factor REAL DEFAULT 2.5,
                repetitions INTEGER DEFAULT 0,
                notes TEXT DEFAULT '',
                runtime_percentile REAL,
                memory_percentile REAL,
                lang TEXT
            )
        """)
        conn.commit()
        
init_db()

@app.post("/log-submission")
async def log_submission(payload: SubmissionPayload):
    now = datetime.datetime.now()
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Look up by unique text title to grab spacing history accurately
        cursor.execute(
            "SELECT interval, ease_factor, repetitions FROM problems WHERE title = ?", 
            (payload.title,)
        )
        row = cursor.fetchone()
        
        if row:
            current_interval, ease_factor, repetitions = row
        else:
            current_interval, ease_factor, repetitions = 1, 2.5, 0
            
        new_interval, new_ef, new_reps = calculate_next_review(
            current_interval, ease_factor, repetitions, payload.quality_score
        )
        
        next_review_date = now + datetime.timedelta(days=new_interval)
        tags_str = ",".join(payload.tags)
        
        # Use INSERT OR REPLACE / ON CONFLICT on the unique title constraint
        cursor.execute("""
            INSERT INTO problems (
                title, difficulty, tags, last_solved, next_review, 
                interval, ease_factor, repetitions, notes, runtime_percentile, memory_percentile, lang
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(title) DO UPDATE SET
                last_solved = excluded.last_solved,
                next_review = excluded.next_review,
                interval = excluded.interval,
                ease_factor = excluded.ease_factor,
                repetitions = excluded.repetitions,
                runtime_percentile = excluded.runtime_percentile,
                memory_percentile = excluded.memory_percentile,
                lang = excluded.lang,
                notes = CASE WHEN excluded.notes != '' THEN excluded.notes ELSE problems.notes END
        """, (
            payload.title, payload.difficulty, tags_str, 
            now, next_review_date, new_interval, new_ef, new_reps, 
            payload.notes, payload.runtime_percentile, payload.memory_percentile, payload.lang
        ))
        conn.commit()
        
    return {"status": "logged", "problem": payload.title}

@app.get("/daily-suggestions")
async def get_daily_suggestions():
    """
    Fetches problems that are currently due or past due for active recall.
    """
    now = datetime.datetime.now()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row  # Returns query rows mapping like python dictionaries
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, difficulty, tags, next_review, interval FROM problems WHERE next_review <= ? ORDER BY next_review ASC", 
            (now,)
        )
        due_problems = [dict(row) for row in cursor.fetchall()]
        
    return {"review_queue": due_problems}

@app.patch("/update-problem/{problem_id}")
async def update_problem_review(problem_id: int, payload: UpdateNotesPayload):
    """
    Optional manual refinement endpoint to update notes or recalculate spacing 
    manually after executing a scheduled review session.
    """
    now = datetime.datetime.now()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT interval, ease_factor, repetitions FROM problems WHERE id = ?", (problem_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Problem record not found.")
            
        current_interval, ease_factor, repetitions = row
        new_interval, new_ef, new_reps = calculate_next_review(
            current_interval, ease_factor, repetitions, payload.quality_score
        )
        next_review_date = now + datetime.timedelta(days=new_interval)
        
        cursor.execute("""
            UPDATE problems SET 
                notes = ?, 
                interval = ?, 
                ease_factor = ?, 
                repetitions = ?, 
                next_review = ?
            WHERE id = ?
        """, (payload.notes, new_interval, new_ef, new_reps, next_review_date, problem_id))
        conn.commit()
        
    return {"status": "updated", "next_review_date": next_review_date.strftime("%Y-%m-%d")}