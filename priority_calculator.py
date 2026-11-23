"""
Priority Calculator Module for Smart Study Planner
Implements the prioritization algorithm defined in Criterion B: Design.
"""

from datetime import date, datetime
from typing import Union


def parse_date(date_input: Union[str, date, datetime]) -> date:
    """Parses a date string in YYYY-MM-DD format or returns the date object."""
    if isinstance(date_input, datetime):
        return date_input.date()
    if isinstance(date_input, date):
        return date_input
    if isinstance(date_input, str):
        return datetime.strptime(date_input.strip(), "%Y-%m-%d").date()
    raise ValueError(f"Invalid date format or type: {date_input}")


def calculate_urgency(deadline: Union[str, date], current_date: date = None) -> int:
    """
    Calculates urgency score (1 to 5) based on days remaining until deadline.
    
    Pseudocode rules:
    IF days_remaining <= 1 THEN urgency = 5
    ELSE IF days_remaining <= 3 THEN urgency = 4
    ELSE IF days_remaining <= 7 THEN urgency = 3
    ELSE IF days_remaining <= 14 THEN urgency = 2
    ELSE urgency = 1
    """
    if current_date is None:
        current_date = date.today()
        
    deadline_date = parse_date(deadline)
    days_remaining = (deadline_date - current_date).days

    if days_remaining <= 1:
        return 5
    elif days_remaining <= 3:
        return 4
    elif days_remaining <= 7:
        return 3
    elif days_remaining <= 14:
        return 2
    else:
        return 1


def calculate_workload(estimated_hours: float) -> int:
    """
    Calculates workload score (1 to 5) based on estimated completion time in hours.
    
    Pseudocode rules:
    IF estimated_hours >= 6 THEN workload = 5
    ELSE IF estimated_hours >= 4 THEN workload = 4
    ELSE IF estimated_hours >= 2 THEN workload = 3
    ELSE IF estimated_hours >= 1 THEN workload = 2
    ELSE workload = 1
    """
    try:
        hours = float(estimated_hours)
    except (ValueError, TypeError):
        raise ValueError("estimated_hours must be a valid number greater than 0")

    if hours >= 6.0:
        return 5
    elif hours >= 4.0:
        return 4
    elif hours >= 2.0:
        return 3
    elif hours >= 1.0:
        return 2
    else:
        return 1


def calculate_priority(
    deadline: Union[str, date],
    difficulty: int,
    importance: int,
    estimated_hours: float,
    current_date: date = None
) -> float:
    """
    Calculates the composite priority score according to the formula:
    priority_score = (0.4 * urgency) + (0.3 * importance) + (0.2 * difficulty) + (0.1 * workload)
    
    Validation:
    - difficulty: 1 to 5
    - importance: 1 to 5
    - estimated_hours: > 0
    - deadline: valid date
    
    Returns rounded priority score (2 decimal places).
    """
    # Validation checks
    try:
        difficulty_val = int(difficulty)
        importance_val = int(importance)
        hours_val = float(estimated_hours)
    except (ValueError, TypeError):
        raise ValueError("Difficulty and Importance must be integers, Estimated Hours must be a number.")

    if not (1 <= difficulty_val <= 5):
        raise ValueError("Difficulty must be between 1 and 5.")
    if not (1 <= importance_val <= 5):
        raise ValueError("Importance must be between 1 and 5.")
    if hours_val <= 0:
        raise ValueError("Estimated hours must be greater than 0.")

    urgency = calculate_urgency(deadline, current_date)
    workload = calculate_workload(hours_val)

    # Weighted calculation
    score = (0.4 * urgency) + (0.3 * importance_val) + (0.2 * difficulty_val) + (0.1 * workload)
    return round(score, 2)


def is_overdue(deadline: Union[str, date], current_date: date = None) -> bool:
    """Returns True if the deadline date is strictly before current_date."""
    if current_date is None:
        current_date = date.today()
    deadline_date = parse_date(deadline)
    return deadline_date < current_date


def days_remaining(deadline: Union[str, date], current_date: date = None) -> int:
    """Returns number of days remaining until deadline (can be negative if overdue)."""
    if current_date is None:
        current_date = date.today()
    deadline_date = parse_date(deadline)
    return (deadline_date - current_date).days
