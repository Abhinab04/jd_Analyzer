"""Scoring utilities for resume vs JD matching."""

from typing import List


def compute_match_score(matched_skills: List[str], required_skills: List[str]) -> int:
    """Compute a simple match score (0-100) based on required skills.

    The score is (matched / required) * 100, rounded to the nearest integer.
    If there are no required skills, returns 0.
    """

    total = len(required_skills)
    if total == 0:
        return 0

    score = (len(matched_skills) / total) * 100
    return int(round(score))
