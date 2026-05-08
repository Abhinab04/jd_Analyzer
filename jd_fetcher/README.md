# JD Fetcher (Resume → Recommended Jobs)

This module fetches jobs from **one portal** (Adzuna API), ranks them against a resume profile, and returns structured JSON recommendations.

## Implemented Architecture
Resume Input  
→ Resume Parsing (skills, role, experience)  
→ Query Generator  
→ Adzuna Job Fetcher (API)  
→ Relevance Filter (skills + role + experience)  
→ Structured Output JSON

## Folder Structure
```text
jd_match_analyzer/
├ main.py
├ utils/
│   ├ adzuna_client.py
│   ├ resume_parser.py
│   └ job_filter.py
└ jd_fetcher/
  ├ job_fetcher/
  │   ├ __init__.py
  │   └ api_client.py
  ├ output/
  │   └ .gitkeep
  ├ job_portal_research.md
  └ README.md
```

## Why this portal?
Portal selected: **Adzuna API**  
Reasoning summary is in `job_portal_research.md`.

## Setup
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set Adzuna credentials:

PowerShell:
```powershell
$env:ADZUNA_APP_ID="your_app_id"
$env:ADZUNA_APP_KEY="your_app_key"
```

## Run
From `jd_match_analyzer`:
```bash
python main.py --resume resume.txt --country in --max-fetch 35 --top-n 5
```

Optional flags:
- `--resume` path or URL (`.txt`, `.pdf`, `.docx`)
- `--query` custom query override
- `--output` custom output path
- `--top-n` is clamped to 3–5

## Input
```json
{
  "resume": "resume.pdf / resume.txt"
}
```

## Output (example)
```json
{
  "recommended_jobs": [
    {
      "job_title": "Backend Developer",
      "company": "XYZ Corp",
      "location": "Bangalore",
      "job_description": "Full JD text...",
      "skills_required": ["Python", "FastAPI", "Docker"],
      "job_url": "https://..."
    }
  ]
}
```

## Notes
- The system fetches up to **35 jobs** from the chosen portal and returns top **3–5** most relevant jobs.
- Existing `jd_match_analyzer` files are untouched; this is a standalone extension module.
