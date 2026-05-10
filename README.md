# JD Match Analyzer

A comprehensive Python-based tool that compares resumes with job descriptions and recommends matching job opportunities from various job platforms.

## 🎯 Features
- **Dual Mode Operation**:
  - **Analyze Mode**: Compare a resume against a job description to identify gaps and missing skills
  - **Recommend Mode**: Fetch and rank jobs from popular job platforms based on resume profile
- **Multi-Source Resume/JD Support**:
  - Local text files (`.txt`)
  - PDF files (`.pdf`)
  - Word documents (`.docx`)
  - HTTP/HTTPS URLs
- **Skill Extraction & Matching**: Automatically extract skills and find matches/gaps between resume and job requirements
- **Match Scoring**: Compute a match score (0–100) showing how well the resume fits the job
- **Experience Gap Analysis**: Identify experience level discrepancies using heuristics and optional LLM integration
- **Job Scraping & Ranking**:
  - Supports **Glassdoor** and **Naukri** platforms
  - Selenium-based web scraping for reliable job fetching
  - Intelligent job ranking based on resume profile
- **LLM Integration** (Optional): Use Google Gemini API for richer gap analysis and improvement suggestions
- **Command-Line Interface**: Flexible CLI with multiple configuration options

## 📁 Repository Structure
```
jd_match_analyzer/
├── main.py                          # Entry point for the CLI tool
├── requirements.txt                 # Python dependencies
├── .env                            # Environment variables (GEMINI_API_KEY)
├── resume.txt                      # Sample resume file
├── jd.txt                          # Sample job description file
├── README.md                       # This file
├── DOCUMENTATION.md                # Detailed implementation documentation
├── TEST_REPORT.md                  # Test results and validation
├── SELENIUM_USAGE.md               # Web scraping usage guide
├── prompt_templates/
│   └── gap_analysis_prompt.txt     # LLM prompt template for gap analysis
├── utils/
│   ├── __init__.py
│   ├── resume_parser.py            # Parse resume and extract profile info
│   ├── skill_extractor.py          # Extract skills from text
│   ├── skill_matcher.py            # Compare skills between resume and JD
│   ├── scoring.py                  # Compute match scores
│   ├── job_scraper.py              # Selenium web scraper for job platforms
│   ├── job_filter.py               # Rank and filter jobs
│   └── adzuna_client.py            # Job data aggregation utilities
├── jd_fetcher/
│   ├── README.md
│   ├── requirements.txt
│   ├── job_fetcher/
│   │   ├── __init__.py
│   │   └── api_client.py           # API integration utilities
│   └── output/
│       └── recommended_jobs.json   # Sample output file
└── __pycache__/                    # Python bytecode cache
```

## 🚀 Getting Started

### 1) Install Dependencies
```bash
pip install -r requirements.txt
```

**Required packages:**
- `google-generativeai` - Google Gemini API (optional, for LLM features)
- `requests` - HTTP requests
- `python-docx` - DOCX file parsing
- `pdfplumber` - PDF text extraction
- `python-dotenv` - Environment variable management
- `selenium` - Web browser automation
- `webdriver-manager` - ChromeDriver management

### 2) Set Up Your Gemini API Key (Optional)
The tool can use **Google Gemini** for enhanced gap analysis and improvement suggestions.

#### Option A: Via Environment Variable
**Windows (PowerShell)**
```powershell
$env:GEMINI_API_KEY = "your-api-key-here"
```

**Linux/Mac**
```bash
export GEMINI_API_KEY="your-api-key-here"
```

#### Option B: Via `.env` File
Create a `.env` file in the project directory:
```
GEMINI_API_KEY=your-api-key-here
```

You can specify a custom env file path with the `--env-file` argument.

### 3) Prepare Input Files
Both resume and job description can be provided as:
- Local file paths: `resume.txt`, `job.pdf`, `description.docx`
- HTTP/HTTPS URLs: `https://example.com/resume.pdf`

## 📋 Usage

### Analyze Mode: Compare Resume vs Job Description
```bash
# Basic usage
python main.py --resume resume.txt --jd jd.txt --mode analyze

# Using PDFs and URLs
python main.py --resume https://example.com/resume.pdf --jd job_description.docx --mode analyze
```

**Output:**
```json
{
  "match_score": 72,
  "missing_skills": ["Docker", "Kubernetes"],
  "matched_skills": ["Python", "FastAPI", "SQL"],
  "experience_gap": "Needs 2+ years backend experience",
  "suggested_resume_improvements": [
    "Highlight years of relevant experience to match the job requirements",
    "Add experience with Docker",
    "Add experience with Kubernetes"
  ]
}
```

### Recommend Mode: Fetch & Rank Jobs
```bash
# Fetch jobs from Naukri (default platform)
python main.py --resume resume.txt --mode recommend

# Use Glassdoor platform with custom location
python main.py --resume resume.txt --mode recommend --platform glassdoor --location "Bangalore"

# Custom search query
python main.py --resume resume.txt --mode recommend --query "Python Developer" --max-fetch 50 --top-n 5

# Save results to custom file
python main.py --resume resume.txt --mode recommend --output custom_results.json
```

**Output:**
```json
{
  "recommended_jobs": [
    {
      "job_title": "Senior Python Developer",
      "company": "Tech Company",
      "location": "Bangalore, India",
      "job_description": "Looking for...",
      "job_url": "https://...",
      "match_score": 0.85,
      "matched_skills": ["Python", "Django"],
      "missing_skills": ["Kubernetes"]
    }
  ]
}
```

## 🔧 Command-Line Arguments

| Argument | Required | Description | Default |
|----------|----------|-------------|---------|
| `--resume` | Yes | Path to resume or URL | - |
| `--jd` | No | Path to job description (required in analyze mode) | - |
| `--mode` | No | Operation mode: `analyze` or `recommend` | Auto-detect |
| `--platform` | No | Job platform: `glassdoor` or `nauki` | `nauki` |
| `--location` | No | Job search location | `India` |
| `--max-fetch` | No | Number of jobs to fetch | `35` |
| `--top-n` | No | Top N recommendations to return | `5` |
| `--query` | No | Custom search query for recommendation mode | Auto-generated from resume |
| `--output` | No | Output JSON file path for recommendations | `jd_fetcher/output/recommended_jobs.json` |
| `--env-file` | No | Path to `.env` file with API keys | `.env` |

## 🔍 How It Works

### Analysis Pipeline
1. **Input Loading**: Read resume and JD from various file formats or URLs
2. **Resume Parsing**: Extract profile info (role, skills, years of experience)
3. **Skill Extraction**: Identify and categorize skills from both documents
4. **Skill Matching**: Compare resume skills against job requirements
5. **Score Computation**: Calculate match percentage
6. **Gap Analysis**: Generate experience gap using heuristics or LLM
7. **Recommendations**: Suggest improvements to bridge the gap

### Job Recommendation Pipeline
1. **Resume Parsing**: Extract candidate profile and top skills
2. **Query Building**: Generate search query from resume profile
3. **Web Scraping**: Use Selenium to fetch jobs from selected platform
4. **Job Ranking**: Rank jobs based on skill match and experience alignment
5. **Output**: Save top N recommendations as JSON

### Key Components

**Resume Parser** (`utils/resume_parser.py`)
- Extracts role, skills, and years of experience from resume text
- Returns a structured profile for analysis

**Skill Extractor** (`utils/skill_extractor.py`)
- Identifies technical skills from text using pattern matching
- Customizable skill keywords database

**Skill Matcher** (`utils/skill_matcher.py`)
- Compares resume skills against job requirement skills
- Returns matched skills and missing skills lists

**Scoring** (`utils/scoring.py`)
- Computes match score as: `(matched_skills_count / required_skills_count) * 100`
- Ranges from 0–100

**Job Scraper** (`utils/job_scraper.py`)
- Selenium-based web scraper for Glassdoor and Naukri
- Handles dynamic content loading and pagination
- Runs in headless mode for efficiency

**Job Filter** (`utils/job_filter.py`)
- Ranks jobs based on resume profile and skill match
- Returns top N recommended jobs

## ⚙️ Advanced Usage

### Batch Analysis
```bash
# Analyze multiple JDs against a resume
for jd in job1.txt job2.txt job3.txt; do
  python main.py --resume resume.txt --jd "$jd" >> results.jsonl
done
```

### Custom Skill Database
Edit `utils/skill_extractor.py` to add or modify the skills database for better accuracy.

### Custom LLM Prompt
Modify `prompt_templates/gap_analysis_prompt.txt` to customize the gap analysis prompt template.

### Headless Mode for Job Scraping
The tool runs Selenium in headless mode by default (no visible browser window). To debug, edit `utils/job_scraper.py` and set `headless=False`.

## 📊 Testing

Run the included test suite:
```bash
python -m pytest tests/  # If tests directory exists
```

See `TEST_REPORT.md` for detailed test results and validation status.

## 🔗 Integration Points

The tool integrates with:
- **Glassdoor**: Web scraping via Selenium
- **Naukri**: Web scraping via Selenium
- **Google Gemini API**: Optional LLM for gap analysis (requires API key)
- **File System**: Reads from local files and URLs

## 🐛 Troubleshooting

**Issue: ChromeDriver not found**
- Solution: `webdriver-manager` automatically handles this. Ensure it's installed: `pip install webdriver-manager`

**Issue: PDF parsing fails**
- Solution: Install `pdfplumber`: `pip install pdfplumber`

**Issue: DOCX parsing fails**
- Solution: Install `python-docx`: `pip install python-docx`

**Issue: Gemini API errors**
- Solution: Verify your `GEMINI_API_KEY` in `.env` file or environment variable

**Issue: Web scraping times out**
- Solution: Increase timeout in `utils/job_scraper.py` or reduce `--max-fetch` count

## 📝 Configuration

All configuration can be done via:
- Command-line arguments (highest priority)
- Environment variables (via `.env` file)
- Default values in `main.py`

## 📚 Additional Documentation

- `DOCUMENTATION.md` - Detailed technical documentation of the implementation
- `TEST_REPORT.md` - Comprehensive test results and validation
- `SELENIUM_USAGE.md` - Web scraping implementation details

## 📄 License & Notes

- This tool is designed for educational and professional use
- Web scraping respects robots.txt and terms of service of job platforms
- LLM integration is optional and works best with configured API key
