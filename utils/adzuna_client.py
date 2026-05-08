from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import requests  # type: ignore[import-not-found]


@dataclass
class AdzunaJobAPIClient:
    app_id: str
    app_key: str
    country: str = "in"
    timeout_seconds: int = 20

    def fetch_jobs(self, query: str, total_results: int = 35, page_size: int = 20) -> List[Dict]:
        if total_results <= 0:
            return []

        page_size = max(1, min(page_size, 50))
        remaining = total_results
        page = 1
        collected: List[Dict] = []

        while remaining > 0:
            batch_size = min(page_size, remaining)
            payload = self._fetch_page(query=query, page=page, page_size=batch_size)
            results = payload.get("results", [])

            if not results:
                break

            for item in results:
                collected.append(self._normalize_job(item))

            remaining = total_results - len(collected)
            page += 1

            if len(results) < batch_size:
                break

        return collected[:total_results]

    def _fetch_page(self, query: str, page: int, page_size: int) -> Dict:
        url = (
            f"https://api.adzuna.com/v1/api/jobs/{self.country}/search/{page}"
            f"?app_id={self.app_id}&app_key={self.app_key}"
        )

        params = {
            "what": query,
            "results_per_page": page_size,
            "content-type": "application/json",
        }

        response = requests.get(url, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _normalize_job(raw: Dict) -> Dict:
        company = (raw.get("company") or {}).get("display_name") or "Unknown"
        location = (raw.get("location") or {}).get("display_name") or "Unknown"

        return {
            "job_title": raw.get("title") or "Unknown",
            "company": company,
            "location": location,
            "job_description": raw.get("description") or "",
            "job_url": raw.get("redirect_url") or "",
        }
