from __future__ import annotations

import re
from typing import Dict, List, Optional

from .skill_extractor import extract_skills


def _extract_required_years(job_text: str) -> Optional[int]:
    match = re.search(r"(\d+)\s*\+?\s*(?:years|yrs)", job_text, flags=re.IGNORECASE)
    if not match:
        return None

    try:
        return int(match.group(1))
    except ValueError:
        return None


def _role_similarity(target_role: str, job_title: str) -> float:
    target_tokens = {token for token in re.split(r"\W+", target_role.lower()) if token}
    title_tokens = {token for token in re.split(r"\W+", job_title.lower()) if token}

    if not target_tokens or not title_tokens:
        return 0.0

    overlap = len(target_tokens.intersection(title_tokens))
    return overlap / len(target_tokens)


def _skill_similarity(resume_skills: List[str], job_skills: List[str]) -> float:
    resume_set = {skill.lower() for skill in resume_skills}
    job_set = {skill.lower() for skill in job_skills}

    if not job_set:
        return 0.0

    matched = len(resume_set.intersection(job_set))
    return matched / len(job_set)


def _experience_fit(candidate_years: Optional[int], jd_years: Optional[int]) -> float:
    if jd_years is None:
        return 0.6

    if candidate_years is None:
        return 0.4

    if candidate_years >= jd_years:
        return 1.0

    diff = jd_years - candidate_years
    if diff == 1:
        return 0.7
    if diff == 2:
        return 0.5
    return 0.2


def rank_jobs(
    jobs: List[Dict],
    resume_skills: List[str],
    target_role: str,
    candidate_years_of_exp: Optional[int],
    top_n: int = 5,
) -> List[Dict]:
    scored_jobs = []

    for job in jobs:
        description = job.get("job_description", "")
        job_title = job.get("job_title", "")

        job_skills = extract_skills(f"{job_title}\n{description}")
        required_years = _extract_required_years(description)

        skill_score = _skill_similarity(resume_skills, job_skills)
        role_score = _role_similarity(target_role, job_title)
        exp_score = _experience_fit(candidate_years_of_exp, required_years)

        final_score = (0.60 * skill_score) + (0.25 * role_score) + (0.15 * exp_score)

        scored_jobs.append(
            {
                **job,
                "skills_required": job_skills,
                "_score": round(final_score, 4),
            }
        )

    scored_jobs.sort(key=lambda item: item["_score"], reverse=True)

    clean_jobs = []
    for item in scored_jobs[:top_n]:
        clean_jobs.append(
            {
                "job_title": item.get("job_title", ""),
                "company": item.get("company", ""),
                "location": item.get("location", ""),
                "job_description": item.get("job_description", ""),
                "skills_required": item.get("skills_required", []),
                "job_url": item.get("job_url", ""),
            }
        )

    return clean_jobs
