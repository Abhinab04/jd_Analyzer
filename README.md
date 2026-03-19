# JD vs Resume Match Analyzer

A small Python-based tool that compares a resume to a job description and produces a structured JSON match analysis.

## 🔍 What it does
- Reads a **resume** and a **job description** from text files
- Extracts **skills** from each document
- Compares resume skills vs job requirements
- Computes a **match score** (0–100)
- Uses an **LLM (OpenAI)** to generate:
  - An experience gap analysis
  - Suggestions to improve the resume

## Repository Structure
```
jd_match_analyzer/
├ main.py
├ prompt_templates/
│   └ gap_analysis_prompt.txt
├ utils/
│   ├ skill_extractor.py
│   ├ skill_matcher.py
│   └ scoring.py
└ README.md
```

## 🚀 Getting Started
### 1) Install dependencies
```bash
python -m pip install -r requirements.txt
```

### 2) Prepare input files
The tool accepts the following inputs for both resume and JD:
- Local text files (`.txt`)
- PDF files (`.pdf`)
- Word documents (`.docx`)
- URLs (HTTP/HTTPS) pointing to any of the above

Example:
- `resume.txt`
- `jd.pdf`
- `https://example.com/resume.docx`

### 3) Set your Gemini API key (optional)
The tool uses **Gemini** for gap analysis + suggestions. Provide your key via an environment variable or a `.env` file.

#### Option A: environment variable
**Windows (PowerShell)**
```powershell
$env:GEMINI_API_KEY = "..."
```

#### Option B: `.env` file
Create a file named `.env` in the project folder with:
```
GEMINI_API_KEY=...
```

Then run the tool as usual. You can also specify a different file via `--env-file`.

### 4) Run the analyzer
```bash
python main.py --resume resume.txt --jd jd.txt
```

Example output:
```json
{
  "match_score": 72,
  "missing_skills": ["Docker", "Kubernetes"],
  "matched_skills": ["Python", "FastAPI", "SQL"],
  "experience_gap": "Needs 2+ years backend experience",
  "suggested_resume_improvements": [
    "Add backend API project metrics",
    "Mention cloud deployment experience"
  ]
}
```

## How it works
- Skill extraction uses a small keyword list (see `utils/skill_extractor.py`)
- Skill matching compares the JD required skills against the resume skills
- A simple match score is derived as: `(matched / required) * 100`
- OpenAI is used (if configured) to produce experience gap analysis and improvement suggestions

## Customization
- Add or update skills in `utils/skill_extractor.py` for better extraction
- Customize the LLM prompt in `prompt_templates/gap_analysis_prompt.txt`

