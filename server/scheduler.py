import datetime
from typing import Tuple

def calculate_next_review(current_interval: int, ease_factor: float, repetitions: int, quality: int) -> Tuple[int, float, int]:
    """
    Implements the SuperMemo-2 (SM-2) algorithm for Spaced Repetition.
    
    Parameters:
    - current_interval (int): Number of days since the last review.
    - ease_factor (float): The difficulty multiplier for spacing out reviews (starts at 2.5).
    - repetitions (int): How many consecutive times the problem was successfully reviewed.
    - quality (int): Performance score from 0 to 5:
        5: Flawless solution, optimal approach found instantly.
        4: Solved with minor hesitation or optimal approach took some refinement.
        3: Solved, but struggled significantly or picked a suboptimal approach.
        2: Failed to solve, but the solution made complete sense upon reading.
        1: Failed to solve, required intense studying of the editorial/discussion.
        0: Complete blackout, no familiarity with the concept.
        
    Returns:
    - Tuple[int, float, int]: (new_interval, new_ease_factor, new_repetitions)
    """
    # If user struggled heavily or failed (quality < 3), reset repetitions and interval
    if quality < 3:
        new_repetitions = 0
        new_interval = 1  # Review the next day
    else:
        if repetitions == 0:
            new_interval = 1  # First review after initial learning
        elif repetitions == 1:
            new_interval = 6  # Second review after 6 days
        else:
            new_interval = int(current_interval * ease_factor)  # Subsequent reviews spaced by ease factor
        new_repetitions = repetitions + 1
    
    # Update the ease factor based on the user's performance(From SM-2 algorithm)
    new_ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    if new_ease_factor < 1.3:
        new_ease_factor = 1.3  # Minimum ease factor to prevent too short intervals
        
    return new_interval, new_ease_factor, new_repetitions