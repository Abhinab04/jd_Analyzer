from __future__ import annotations

import html
import json
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


@dataclass
class SeleniumJobScraper:
    platform: str = "glassdoor"
    timeout_seconds: int = 20
    headless: bool = True

    def __post_init__(self) -> None:
        if self.platform not in {"glassdoor", "nauki"}:
            raise ValueError("Platform must be 'glassdoor' or 'nauki'")

    def fetch_jobs(self, query: str, total_results: int = 35, location: str = "India") -> List[Dict]:
        if total_results <= 0:
            return []

        driver = self._create_driver()
        try:
            search_url = self._build_search_url(query=query, location=location)
            driver.get(search_url)
            self._wait_for_page_ready(driver)
            self._scroll_page(driver)

            jobs = self._extract_jobs(driver, query=query, location=location)
            if not jobs:
                print(f"No {self.platform.title()} job cards found at {driver.current_url}")
                return []

            return jobs[:total_results]
        finally:
            driver.quit()

    def _build_search_url(self, query: str, location: str) -> str:
        if self.platform == "glassdoor":
            safe_query = re.sub(r"\s+", "%20", query.strip())
            safe_location = re.sub(r"\s+", "%20", location.strip())
            return f"https://www.glassdoor.co.in/Job/jobs.htm?keyword={safe_query}&location={safe_location}"

        slug = self._query_slug(query)
        return f"https://www.naukri.com/{slug}-jobs"

    def _query_slug(self, query: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", query.lower())
        parts = [part for part in cleaned.split() if part]
        if not parts:
            return "jobs"

        generic_terms = {
            "developer",
            "engineer",
            "senior",
            "lead",
            "software",
            "full",
            "stack",
            "backend",
            "backenddeveloper",
            "job",
            "jobs",
        }

        keyword = next((part for part in parts if part not in generic_terms), parts[0])
        return f"{keyword}-jobs"

    def _wait_for_page_ready(self, driver: webdriver.Chrome) -> None:
        deadline = time.time() + self.timeout_seconds
        last_length = 0

        while time.time() < deadline:
            try:
                ready_state = driver.execute_script("return document.readyState")
                page_text = driver.find_element(By.TAG_NAME, "body").text
            except Exception:
                ready_state = "loading"
                page_text = ""

            current_length = len(page_text)
            if ready_state == "complete" and current_length > 0 and current_length >= last_length:
                return

            last_length = current_length
            time.sleep(1)

    def _scroll_page(self, driver: webdriver.Chrome) -> None:
        for _ in range(3):
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            except Exception:
                break
            time.sleep(1)

    def _extract_jobs(self, driver: webdriver.Chrome, query: str, location: str) -> List[Dict]:
        jobs = self._extract_from_jsonld(driver)
        if jobs:
            return self._deduplicate_jobs(jobs)

        jobs = self._extract_from_links(driver, query=query, location=location)
        if jobs:
            return self._deduplicate_jobs(jobs)

        jobs = self._extract_from_job_containers(driver, location=location)
        return self._deduplicate_jobs(jobs)

    def _extract_from_jsonld(self, driver: webdriver.Chrome) -> List[Dict]:
        page_source = driver.page_source
        scripts = re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            page_source,
            flags=re.IGNORECASE | re.DOTALL,
        )

        jobs: List[Dict] = []
        for script_text in scripts:
            parsed_objects = self._parse_jsonld_block(script_text)
            for item in parsed_objects:
                for job in self._collect_job_postings(item):
                    jobs.append(self._normalize_job_posting(job, driver.current_url))

        return jobs

    def _parse_jsonld_block(self, script_text: str) -> List[Any]:
        cleaned = html.unescape(script_text.strip())
        if not cleaned:
            return []

        try:
            parsed = json.loads(cleaned)
        except Exception:
            return []

        if isinstance(parsed, list):
            return parsed

        return [parsed]

    def _collect_job_postings(self, value: Any) -> List[Dict]:
        jobs: List[Dict] = []

        if isinstance(value, dict):
            value_type = value.get("@type")
            if isinstance(value_type, list):
                value_type = {str(v).lower() for v in value_type}
            else:
                value_type = {str(value_type).lower()} if value_type else set()

            if "jobposting" in value_type:
                jobs.append(value)

            for nested_key in ("@graph", "itemListElement", "mainEntity"):
                nested_value = value.get(nested_key)
                jobs.extend(self._collect_job_postings(nested_value))

        elif isinstance(value, list):
            for item in value:
                jobs.extend(self._collect_job_postings(item))

        return jobs

    def _normalize_job_posting(self, job: Dict, fallback_url: str) -> Dict:
        organization = job.get("hiringOrganization") or {}
        address = job.get("jobLocation") or {}

        if isinstance(address, list) and address:
            address = address[0]
        if isinstance(address, dict):
            address = address.get("address") or address
        if isinstance(address, list) and address:
            address = address[0]

        location_parts: List[str] = []
        if isinstance(address, dict):
            for key in ("addressLocality", "addressRegion", "addressCountry"):
                value = address.get(key)
                if value:
                    location_parts.append(str(value))

        description = job.get("description") or ""
        if isinstance(description, str):
            description = self._strip_html(description)

        return {
            "job_title": job.get("title") or job.get("name") or "Unknown",
            "company": organization.get("name") or organization.get("legalName") or "Unknown",
            "location": ", ".join(location_parts) if location_parts else "Unknown",
            "job_description": description,
            "job_url": job.get("url") or fallback_url,
        }

    def _extract_from_job_containers(self, driver: webdriver.Chrome, location: str) -> List[Dict]:
        selectors = [
            "article",
            "li",
            "[class*='job']",
            "[class*='Job']",
            "[data-job-id]",
            "[data-id]",
        ]

        containers: List[Any] = []
        for selector in selectors:
            try:
                found = driver.find_elements(By.CSS_SELECTOR, selector)
            except Exception:
                found = []
            containers.extend(found)

        jobs: List[Dict] = []
        seen_signatures = set()

        for container in containers:
            try:
                container_text = container.text.strip()
            except Exception:
                continue

            if not container_text or len(container_text) < 40:
                continue

            lines = [line.strip() for line in container_text.splitlines() if line.strip()]
            if not lines:
                continue

            title = self._pick_title(lines)
            if not title:
                continue

            if self._looks_like_navigation(title):
                continue

            company = self._guess_company(lines, title)
            job_location = self._guess_location(lines, location)
            description = self._guess_description(lines)
            url = self._guess_url_from_container(container)

            if not self._is_valid_job_record(title, company, job_location, description, url):
                continue

            signature = (title.lower(), company.lower(), job_location.lower(), url)
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)

            jobs.append(
                {
                    "job_title": title,
                    "company": company,
                    "location": job_location,
                    "job_description": description,
                    "job_url": url,
                }
            )

        return jobs

    def _extract_from_links(self, driver: webdriver.Chrome, query: str, location: str) -> List[Dict]:
        jobs: List[Dict] = []
        seen_urls = set()

        try:
            anchors = driver.find_elements(By.TAG_NAME, "a")
        except Exception:
            anchors = []

        for anchor in anchors:
            try:
                href = (anchor.get_attribute("href") or "").strip()
                text = (anchor.text or "").strip()
            except Exception:
                continue

            if not href or href in seen_urls:
                continue
            if not self._looks_like_job_link(href, text, query):
                continue

            container_text = self._get_container_text(anchor)
            title = text or self._pick_title([line.strip() for line in container_text.splitlines() if line.strip()])
            if not title:
                continue

            if not self._looks_like_job_link(href, title, query):
                continue

            company = self._guess_company(container_text.splitlines(), title)
            job_location = self._guess_location(container_text.splitlines(), location)
            description = self._guess_description(container_text.splitlines())

            if not self._is_valid_job_record(title, company, job_location, description, href):
                continue

            seen_urls.add(href)
            jobs.append(
                {
                    "job_title": title,
                    "company": company,
                    "location": job_location,
                    "job_description": description,
                    "job_url": href,
                }
            )

        return jobs

    def _get_container_text(self, anchor: Any) -> str:
        xpaths = [
            "./ancestor::article[1]",
            "./ancestor::li[1]",
            "./ancestor::div[1]",
            "./parent::*",
        ]

        for xpath in xpaths:
            try:
                container = anchor.find_element(By.XPATH, xpath)
                container_text = (container.text or "").strip()
                if container_text:
                    return container_text
            except Exception:
                continue

        try:
            return (anchor.text or "").strip()
        except Exception:
            return ""

    def _guess_url_from_container(self, container: Any) -> str:
        try:
            anchors = container.find_elements(By.TAG_NAME, "a")
        except Exception:
            anchors = []

        for anchor in anchors:
            try:
                href = (anchor.get_attribute("href") or "").strip()
            except Exception:
                href = ""
            if href:
                return href

        return ""

    def _looks_like_job_link(self, href: str, text: str, query: str) -> bool:
        href_lower = href.lower()
        text_lower = text.lower()
        query_words = [part.lower() for part in re.split(r"\s+", query.strip()) if part]

        if any(keyword in href_lower for keyword in ("job-listings", "job-details", "career", "opening", "vacancy")):
            return True
        if any(keyword in text_lower for keyword in ("apply", "opening", "vacancy")):
            return True
        if query_words and any(word in text_lower for word in query_words[:2]):
            return True

        return False

    def _pick_title(self, lines: List[str]) -> str:
        for line in lines[:5]:
            if len(line) >= 8 and not self._looks_like_noise(line):
                return self._clean_value(line)
        return ""

    def _guess_company(self, lines: List[str], title: str) -> str:
        for line in lines[1:6]:
            if self._looks_like_company(line, title):
                return self._clean_value(line)
        return "Unknown"

    def _guess_location(self, lines: List[str], default_location: str) -> str:
        for line in lines:
            if self._looks_like_location(line):
                return self._clean_value(line)
        return default_location

    def _guess_description(self, lines: List[str]) -> str:
        return self._clean_value(" ".join(lines[1:6]))

    def _looks_like_company(self, line: str, title: str) -> bool:
        normalized = line.lower().strip()
        if not normalized or normalized == title.lower().strip():
            return False
        if self._looks_like_location(line):
            return False
        if any(token in normalized for token in ("apply", "salary", "experience", "remote", "full-time", "part-time")):
            return False
        return len(line) <= 80

    def _looks_like_location(self, line: str) -> bool:
        normalized = line.lower().strip()
        location_tokens = (
            "india",
            "bangalore",
            "bengaluru",
            "delhi",
            "mumbai",
            "hyderabad",
            "chennai",
            "pune",
            "gurgaon",
            "noida",
            "remote",
            "hybrid",
        )
        return any(token in normalized for token in location_tokens) or bool(re.search(r"\b\w+\s*,\s*\w+\b", line))

    def _looks_like_navigation(self, text: str) -> bool:
        normalized = text.lower().strip()
        return normalized in {"home", "about", "privacy", "terms", "sign in", "login", "register"}

    def _looks_like_noise(self, line: str) -> bool:
        normalized = line.lower().strip()
        return (
            normalized in {"", "apply", "more", "save", "view", "share", "python jobs"}
            or bool(re.match(r"^\d+\s*-\s*\d+\s*of\s+\d+", normalized))
            or normalized.startswith("sort by:")
        )

    def _is_valid_job_record(
        self,
        title: str,
        company: str,
        location: str,
        description: str,
        url: str,
    ) -> bool:
        title_clean = title.strip().lower()
        company_clean = company.strip().lower()
        location_clean = location.strip().lower()
        description_clean = description.strip().lower()
        url_clean = url.strip().lower()

        if not title_clean or len(title_clean) < 6:
            return False
        if title_clean in {"jobs", "python jobs", "search", "results"}:
            return False
        if bool(re.match(r"^\d+\s*-\s*\d+\s*of\s+\d+", title_clean)):
            return False
        if company_clean in {"", "unknown", "python jobs"} and not url_clean:
            return False
        if not url_clean and not description_clean and company_clean == "unknown":
            return False
        if "naukri.com" in url_clean and "job-listings" not in url_clean:
            return False

        return True

    def _clean_value(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    def _strip_html(self, value: str) -> str:
        value = re.sub(r"<[^>]+>", " ", value)
        return self._clean_value(html.unescape(value))

    def _deduplicate_jobs(self, jobs: List[Dict]) -> List[Dict]:
        deduped: List[Dict] = []
        seen = set()

        for job in jobs:
            signature = (
                job.get("job_title", "").strip().lower(),
                job.get("company", "").strip().lower(),
                job.get("location", "").strip().lower(),
                job.get("job_url", "").strip().lower(),
            )
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(job)

        return deduped

    def _create_driver(self) -> webdriver.Chrome:
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless=new")

        chrome_options.add_argument("--window-size=1440,1200")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        return webdriver.Chrome(options=chrome_options)
