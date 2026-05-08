from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

import requests  # type: ignore[import-not-found]

from .skill_extractor import extract_skills


@dataclass
class ResumeProfile:
    skills: List[str]
    role: str
    years_of_experience: Optional[int]
    experience_level: str


ROLE_KEYWORDS = {
    "Backend Developer": ["backend", "api", "fastapi", "django", "flask", "spring", "node", "express"],
    "Frontend Developer": ["frontend", "react", "angular", "vue", "javascript", "typescript", "ui"],
    "Full Stack Developer": ["full stack", "frontend", "backend", "react", "node"],
    "Data Scientist": ["data scientist", "machine learning", "pandas", "numpy", "tensorflow", "pytorch"],
    "Data Engineer": ["data engineer", "etl", "spark", "airflow", "pipeline", "warehouse"],
    "DevOps Engineer": ["devops", "docker", "kubernetes", "terraform", "ci/cd", "aws", "azure", "gcp"],
    "Mobile Developer": ["android", "ios", "react native", "flutter", "swift", "kotlin"],
}


def _is_url(source: str) -> bool:
    return source.startswith("http://") or source.startswith("https://")


def _read_text_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    return path.read_text(encoding="utf-8")


def _read_pdf(path: Path) -> str:
    import pdfplumber  # type: ignore[import-not-found]

    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages)


def _read_docx(path: Path) -> str:
    import docx  # type: ignore[import-not-found]

    doc = docx.Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def _download_to_temp(url: str) -> Path:
    import tempfile

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    suffix = Path(url).suffix or ".txt"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(response.content)
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


def load_resume_text(source: Union[str, Path]) -> str:
    if isinstance(source, Path):
        source = str(source)

    if _is_url(source):
        temp_path = _download_to_temp(source)
        try:
            return load_resume_text(temp_path)
        finally:
            try:
                temp_path.unlink()
            except OSError:
                pass

    path = Path(source)
    ext = path.suffix.lower()

    if ext in {".txt", ""}:
        return _read_text_file(path)
    if ext == ".pdf":
        return _read_pdf(path)
    if ext == ".docx":
        return _read_docx(path)

    return _read_text_file(path)


def extract_years_of_experience(text: str) -> Optional[int]:
    matches = re.findall(r"(\d+)\s*\+?\s*(?:years|yrs)", text, flags=re.IGNORECASE)
    if not matches:
        return None

    values = []
    for item in matches:
        try:
            values.append(int(item))
        except ValueError:
            continue

    return max(values) if values else None


def infer_experience_level(years_of_experience: Optional[int]) -> str:
    if years_of_experience is None:
        return "Mid"
    if years_of_experience < 2:
        return "Junior"
    if years_of_experience <= 5:
        return "Mid"
    return "Senior"


def infer_role(resume_text: str, extracted_skills: List[str]) -> str:
    text = resume_text.lower()
    skill_set = {skill.lower() for skill in extracted_skills}

    best_role = "Software Engineer"
    best_score = 0

    for role, keywords in ROLE_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in text:
                score += 2
            if keyword in skill_set:
                score += 1

        if score > best_score:
            best_score = score
            best_role = role

    return best_role


def parse_resume(source: Union[str, Path]) -> ResumeProfile:
    text = load_resume_text(source)
    skills = extract_skills(text)
    years = extract_years_of_experience(text)
    role = infer_role(text, skills)
    level = infer_experience_level(years)

    return ResumeProfile(
        skills=skills,
        role=role,
        years_of_experience=years,
        experience_level=level,
    )
