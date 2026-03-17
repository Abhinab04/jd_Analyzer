"""Skill comparison utilities."""

from typing import List, Tuple


def compare_skills(resume_skills: List[str], jd_skills: List[str]) -> Tuple[List[str], List[str]]:
    """Compare resume skills to JD skills.

    Returns a tuple of (matched_skills, missing_skills).
    """

    resume_set = {s.lower() for s in resume_skills}
    jd_set = {s.lower() for s in jd_skills}

    matched = [s for s in jd_skills if s.lower() in resume_set]
    missing = [s for s in jd_skills if s.lower() not in resume_set]

    return matched, missing
