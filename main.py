import argparse
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from utils.skill_extractor import extract_skills
from utils.skill_matcher import compare_skills
from utils.scoring import compute_match_score


def _is_url(source: str) -> bool:
    return source.startswith("http://") or source.startswith("https://")


def _read_text_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    return path.read_text(encoding="utf-8")


def _read_pdf(path: Path) -> str:
    try:
        import pdfplumber
    except ImportError as e:
        raise RuntimeError("pdfplumber is required to read PDF files. Install via pip.") from e

    text = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text.append(page.extract_text() or "")
    return "\n".join(text)


def _read_docx(path: Path) -> str:
    try:
        import docx
    except ImportError as e:
        raise RuntimeError("python-docx is required to read DOCX files. Install via pip.") from e

    doc = docx.Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def _download_to_temp(url: str) -> Path:
    import tempfile
    import requests

    r = requests.get(url, timeout=30)
    r.raise_for_status()

    suffix = Path(url).suffix or ".txt"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(r.content)
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


from typing import Union


def load_text(source: Union[str, Path]) -> str:
    """Load text from a local file path or a URL.

    Supports:
    - plain text (.txt)
    - PDF (.pdf)
    - Word documents (.docx)
    - HTTP/HTTPS URLs (will be downloaded and parsed similarly based on extension)

    If the file type is unknown, it will attempt to read it as UTF-8 text.
    """

    if isinstance(source, Path):
        source = str(source)

    if _is_url(source):
        tmp_path = _download_to_temp(source)
        try:
            return load_text(str(tmp_path))
        finally:
            try:
                tmp_path.unlink()
            except Exception:
                pass

    path = Path(source)
    ext = path.suffix.lower()

    if ext in {".txt", ""}:
        return _read_text_file(path)
    if ext == ".pdf":
        return _read_pdf(path)
    if ext == ".docx":
        return _read_docx(path)

    # Fallback: try to read as UTF-8 text
    return _read_text_file(path)


def load_prompt_template() -> str:
    base = Path(__file__).resolve().parent
    template_file = base / "prompt_templates" / "gap_analysis_prompt.txt"
    if not template_file.exists():
        raise FileNotFoundError("Prompt template not found: " + str(template_file))
    return template_file.read_text(encoding="utf-8")


def _load_env_file(env_path: Path) -> None:
    """Load an .env file and set variables into os.environ if not already set."""

    if not env_path.exists():
        return

    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=env_path, override=False)
        return
    except ImportError:
        pass

    # Fallback simple parser if python-dotenv is not installed
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line or line.strip().startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def call_llm(prompt: str) -> Optional[Dict]:
    """Call Gemini to generate gap analysis + suggestions."""

    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        return None

    try:
        import google.generativeai as genai
    except ImportError:
        return None

    genai.configure(api_key=gemini_api_key)
    try:
        response = genai.chat.create(
            model="gemini-1.0",
            messages=[
                {"role": "system", "content": "You are an expert hiring assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_output_tokens=450,
        )

        # Response structure may vary; attempt to extract sensible text
        if hasattr(response, "last") and response.last:
            text = response.last
        else:
            candidates = getattr(response, "candidates", None)
            if candidates and len(candidates) > 0:
                text = candidates[0].get("content", "")
            else:
                text = ""

        return json.loads(text.strip())
    except Exception:
        return None


def parse_years_of_experience(text: str) -> Optional[int]:
    """Extract the first years-of-experience number found in a text.

    Looks for patterns like "3 years", "3+ years", "3 yrs".
    """

    match = re.search(r"(\d+)\s*\+?\s*(years|yrs)\b", text, flags=re.IGNORECASE)
    if not match:
        return None

    try:
        return int(match.group(1))
    except ValueError:
        return None


def summarize_missing_skills(missing_skills: List[str]) -> List[str]:
    """Generate fallback suggestions for missing skills."""
    if not missing_skills:
        return []
    return [f"Add experience with {skill}" for skill in missing_skills[:4]]


def summarize_experience_gap(jd_text: str, resume_text: str) -> str:
    """Generate a basic experience gap summary without using an LLM."""

    required = parse_years_of_experience(jd_text)
    candidate = parse_years_of_experience(resume_text)

    if required is None:
        return "Meets requirements"

    if candidate is None:
        return f"Needs {required}+ years experience"

    if candidate >= required:
        return "Meets requirements"

    missing = required - candidate
    return f"Needs {missing}+ more years experience"


def main() -> None:
    parser = argparse.ArgumentParser(description="JD vs Resume Match Analyzer")
    parser.add_argument("--resume", required=True, help="Path to resume text file or URL")
    parser.add_argument("--jd", required=True, help="Path to job description text file or URL")
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Optional path to an env file containing GEMINI_API_KEY",
    )
    args = parser.parse_args()

    # Load environment variables from file if provided
    if args.env_file:
        _load_env_file(Path(args.env_file))

    resume_text = load_text(args.resume)
    jd_text = load_text(args.jd)

    resume_skills = extract_skills(resume_text)
    jd_skills = extract_skills(jd_text)

    matched_skills, missing_skills = compare_skills(resume_skills, jd_skills)
    match_score = compute_match_score(matched_skills, jd_skills)

    # Attempt to use an LLM to generate rich analysis; fallback to a basic heuristic.
    prompt_template = load_prompt_template()
    filled_prompt = prompt_template.format(
        resume_text=resume_text,
        jd_text=jd_text,
        missing_skills=missing_skills,
    )

    llm_result = call_llm(filled_prompt)

    # Generate a basic experience gap summary even if the LLM is unavailable.
    experience_gap = summarize_experience_gap(jd_text, resume_text)
    suggested_resume_improvements: List[str] = []

    if llm_result:
        experience_gap = llm_result.get("experience_gap", experience_gap)
        suggested_resume_improvements = llm_result.get(
            "suggested_resume_improvements", []
        )

    if not suggested_resume_improvements:
        suggested_resume_improvements = summarize_missing_skills(missing_skills)

    # If experience is missing, ensure we offer at least one clear improvement suggestion.
    if experience_gap != "Meets requirements":
        suggestion = (
            "Highlight years of relevant experience to match the job requirements"
        )
        if suggestion not in suggested_resume_improvements:
            suggested_resume_improvements.insert(0, suggestion)

    output = {
        "match_score": match_score,
        "missing_skills": missing_skills,
        "matched_skills": matched_skills,
        "experience_gap": experience_gap,
        "suggested_resume_improvements": suggested_resume_improvements,
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
