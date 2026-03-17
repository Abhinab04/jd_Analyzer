"""Skill extraction helpers.

This module provides simple keyword-based extraction from raw text.

The implementation is intentionally lightweight: it uses a small built-in skill list,
normalizes text, and pulls out skills that appear as whole words.

It is designed to be a starting point; you can replace it with an NLP/LLM-based
extractor or a larger skill ontology.
"""

import re
from typing import List, Optional, Set

# A small seed list of common technical skills/keywords used in many job descriptions.
# Extend this list as needed for your domain.
DEFAULT_SKILL_LIST = [
    "python",
    "java",
    "javascript",
    "typescript",
    "c#",
    "c++",
    "go",
    "rust",
    "sql",
    "nosql",
    "mongodb",
    "postgresql",
    "mysql",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "gcp",
    "rest",
    "graphql",
    "fastapi",
    "flask",
    "django",
    "spring",
    "node",
    "express",
    "react",
    "angular",
    "vue",
    "devops",
    "ci/cd",
    "terraform",
    "ansible",
    "linux",
    "bash",
    "powershell",
    "machine learning",
    "ml",
    "data science",
    "pandas",
    "numpy",
    "scikit-learn",
    "tensorflow",
    "pytorch",
    "git",
    "mongodb",
    "redis",
    "junit",
    "pytest",
    "testing",
    "rest api",
    "graphql api",
]


def normalize_text(text: str) -> str:
    """Normalize text for reliable matching."""
    return text.lower().replace("\n", " ").strip()


def extract_skills(text: str, skill_list: Optional[List[str]] = None) -> List[str]:
    """Extract skills from a block of text.

    This function performs simple keyword matching on an optimized skill list.

    Args:
        text: Raw text of a resume or job description.
        skill_list: Optional list of skills to search for. If omitted, uses DEFAULT_SKILL_LIST.

    Returns:
        A sorted list of unique skills found in the text (normalized to input skill casing).
    """

    if skill_list is None:
        skill_list = DEFAULT_SKILL_LIST

    normalized = normalize_text(text)

    found: Set[str] = set()

    # When searching for skills, do whole-word matching to avoid partial hits.
    for skill in skill_list:
        # Build a regex that matches the skill as a whole word; allow common separators.
        escaped = re.escape(skill.lower())
        pattern = r"(?<![a-z0-9_])" + escaped + r"(?![a-z0-9_])"
        if re.search(pattern, normalized):
            found.add(skill)

    # Preserve input order as much as possible by sorting based on skill_list order.
    ordered = [s for s in skill_list if s in found]
    return ordered
