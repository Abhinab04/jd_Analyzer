# Job Portal Research and Selection

## Final Choice: Adzuna (Official API)

I selected **Adzuna API** as the single portal for this task.

## Why Adzuna

1. **Ease of integration (API-first)**
   - Official REST API with predictable JSON responses.
   - No browser automation needed.

2. **Legal and operational safety**
   - API usage avoids risky scraping patterns.
   - Lower compliance risk than scraping login-protected portals.

3. **Data richness**
   - Returns title, company, location, description, and job URL.
   - Sufficient fields for ranking and downstream analysis.

4. **Cost and practicality**
   - Has developer-friendly entry usage for prototypes.
   - No heavy infrastructure needed.

5. **Reliability and scalability**
   - Stable API contract supports modular extension.
   - Easy to add retries/caching/rate-limit handling later.

## Alternatives Considered

### 1) LinkedIn Jobs
- **Pros**: very rich data, strong market coverage.
- **Cons**: scraping is high-risk and often blocked; auth constraints; legal concerns without official partner access.
- **Decision**: rejected for instability/legal risk.

### 2) Indeed
- **Pros**: broad listings, often easier than LinkedIn to navigate.
- **Cons**: scraping stability varies over time; anti-bot controls can break pipelines.
- **Decision**: not selected due to scraping fragility compared to API route.

### 3) Naukri / Glassdoor / Wellfound
- **Pros**: domain-specific strengths depending on region/startup focus.
- **Cons**: API access limitations or less consistent scraping reliability.
- **Decision**: not selected because API-based stability was the top priority.

## Trade-offs of Adzuna Choice

- **Trade-off 1**: Coverage may differ from other portals in certain regions.
- **Trade-off 2**: Requires API credentials (`app_id`, `app_key`).
- **Trade-off 3**: API quota may constrain very high-volume usage.

Despite trade-offs, Adzuna gives the best balance of **stability, safety, and implementation speed** for this requirement.
