"""AI Job Search: fetch remote job listings and let Claude rank them against your resume.

Usage:
    python job_search.py "python developer" --resume resume.txt --top 10
"""

import argparse
import html
import re
import sys

import anthropic
import requests
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()  # read ANTHROPIC_API_KEY from .env

JOBS_API = "https://remotive.com/api/remote-jobs"
MODEL = "claude-opus-5-5"


class JobMatch(BaseModel):
    job_id: int
    score: int  # 0-100 fit score
    reason: str


class Ranking(BaseModel):
    matches: list[JobMatch]


def fetch_jobs(query: str, limit: int) -> list[dict]:
    """Fetch remote jobs from the free Remotive API (no key needed)."""
    resp = requests.get(JOBS_API, params={"search": query, "limit": limit}, timeout=30)
    resp.raise_for_status()
    return resp.json().get("jobs", [])


def clean(text: str, max_chars: int = 1500) -> str:
    """Strip HTML tags and shorten long descriptions."""
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()[:max_chars]


def rank_jobs(client: anthropic.Anthropic, resume: str, jobs: list[dict]) -> Ranking:
    """Ask Claude to score each job against the resume."""
    listings = "\n\n".join(
        f"[job_id={j['id']}] {j['title']} at {j['company_name']} "
        f"({j.get('candidate_required_location', 'Anywhere')})\n{clean(j.get('description', ''))}"
        for j in jobs
    )
    response = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        output_config={"effort": "medium"},
        system=(
            "You are a career coach. Score how well each job fits the candidate's resume "
            "from 0 to 100, and give a one-sentence reason. Include every job_id."
        ),
        messages=[{
            "role": "user",
            "content": f"<resume>\n{resume}\n</resume>\n\n<jobs>\n{listings}\n</jobs>",
        }],
        output_format=Ranking,
    )
    if response.stop_reason == "refusal":
        sys.exit("Claude declined this request.")
    return response.parsed_output


def main() -> None:
    parser = argparse.ArgumentParser(description="AI-powered job search")
    parser.add_argument("query", help='Job search keywords, e.g. "data analyst"')
    parser.add_argument("--resume", default="resume.txt", help="Path to your resume (plain text)")
    parser.add_argument("--fetch", type=int, default=25, help="How many jobs to fetch")
    parser.add_argument("--top", type=int, default=10, help="How many matches to show")
    args = parser.parse_args()

    try:
        with open(args.resume, encoding="utf-8") as f:
            resume = f.read()
    except FileNotFoundError:
        sys.exit(f"Resume not found: {args.resume} (copy resume.example.txt to resume.txt)")

    print(f"Searching jobs for '{args.query}'...")
    jobs = fetch_jobs(args.query, args.fetch)
    if not jobs:
        sys.exit("No jobs found. Try different keywords.")

    print(f"Found {len(jobs)} jobs. Asking Claude to rank them...\n")
    ranking = rank_jobs(anthropic.Anthropic(), resume, jobs)

    by_id = {j["id"]: j for j in jobs}
    top = sorted(ranking.matches, key=lambda m: m.score, reverse=True)[: args.top]
    for i, m in enumerate(top, 1):
        job = by_id.get(m.job_id)
        if not job:
            continue
        print(f"{i}. [{m.score}/100] {job['title']} — {job['company_name']}")
        print(f"   {m.reason}")
        print(f"   {job['url']}\n")


if __name__ == "__main__":
    main()
