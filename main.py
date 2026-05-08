import argparse
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from utils.skill_extractor import extract_skills
from utils.skill_matcher import compare_skills
from utils.scoring import compute_match_score
from utils.job_scraper import SeleniumJobScraper
from utils.job_filter import rank_jobs
from utils.resume_parser import parse_resume


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


def build_query(profile_role: str, profile_skills: List[str]) -> str:
    top_skills = profile_skills[:4]
    if top_skills:
        return f"{profile_role} {' '.join(top_skills)}"
    return profile_role


def build_search_query(profile_role: str, profile_skills: List[str]) -> str:
    if profile_skills:
        return profile_skills[0]

    role_parts = [part for part in re.split(r"\s+", profile_role.strip()) if part]
    if role_parts:
        return role_parts[0]

    return "python"


def run_job_recommendation(
    resume_source: str,
    platform: str,
    max_fetch: int,
    top_n: int,
    custom_query: Optional[str],
    location: str = "India",
) -> Dict:
    profile = parse_resume(resume_source)
    query = custom_query.strip() if custom_query else build_search_query(profile.role, profile.skills)

    scraper = SeleniumJobScraper(platform=platform, headless=True)
    jobs = scraper.fetch_jobs(query=query, total_results=max_fetch, location=location)

    recommended = rank_jobs(
        jobs=jobs,
        resume_skills=profile.skills,
        target_role=profile.role,
        candidate_years_of_exp=profile.years_of_experience,
        top_n=top_n,
    )
    return {"recommended_jobs": recommended}


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified JD analyzer and job recommendation tool")
    parser.add_argument("--resume", required=True, help="Path to resume text file or URL")
    parser.add_argument("--jd", help="Path to job description text file or URL (required in analyze mode)")
    parser.add_argument(
        "--mode",
        choices=["analyze", "recommend"],
        default=None,
        help="analyze: JD vs resume analysis, recommend: fetch and rank jobs using Selenium",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Optional path to an env file containing GEMINI_API_KEY",
    )
    parser.add_argument(
        "--platform",
        choices=["glassdoor", "nauki"],
        default="nauki",
        help="Job platform to scrape from (default: nauki)",
    )
    parser.add_argument(
        "--location",
        default="India",
        help="Location for job search (default: India)",
    )
    parser.add_argument("--max-fetch", type=int, default=35, help="Number of jobs to fetch (default: 35)")
    parser.add_argument("--top-n", type=int, default=5, help="Final number of recommended jobs (default: 5)")
    parser.add_argument("--query", default=None, help="Optional custom query for recommendation mode")
    parser.add_argument(
        "--output",
        default="jd_fetcher/output/recommended_jobs.json",
        help="Output JSON file path for recommendation mode",
    )
    args = parser.parse_args()

    # Load environment variables from file if provided
    if args.env_file:
        _load_env_file(Path(args.env_file))

    if args.mode is None:
        args.mode = "analyze" if args.jd else "recommend"

    if args.mode == "recommend":
        result = run_job_recommendation(
            resume_source=args.resume,
            platform=args.platform,
            max_fetch=max(1, args.max_fetch),
            top_n=max(3, min(5, args.top_n)),
            custom_query=args.query,
            location=args.location,
        )

        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = Path(__file__).resolve().parent / output_path

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if not args.jd:
        parser.error("--jd is required in analyze mode")

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
