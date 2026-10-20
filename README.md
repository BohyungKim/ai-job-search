# AI Job Search

Find remote jobs and let Claude rank them by how well they fit your resume.

## How it works
1. Pulls live remote job listings from the free [Remotive API](https://remotive.com/api/remote-jobs).
2. Sends your resume and the listings to Claude, which scores each job 0–100 with a short reason.
3. Prints the best matches with links to apply.

## Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your-key-here
cp resume.example.txt resume.txt   # then paste in your own resume
```

## Usage
```bash
python job_search.py "python developer"
python job_search.py "data analyst" --fetch 40 --top 5
```

`resume.txt` is git-ignored so your personal info stays off GitHub.
