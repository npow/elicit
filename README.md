# Elicit

**Elicit what matters from customer interviews. Build the right thing.**

You did the interviews. You took the notes. But now you're staring at a pile of Google Docs trying to remember what that one PM said three months ago about dashboards. Sound familiar?

Elicit reads your interview transcripts and draws out what matters: what jobs your customers are actually trying to do, what's painful, what workarounds they've duct-taped together, and — most importantly — what you should build next, backed by evidence you can trace back to specific quotes.

## What you can do

- **Upload interviews** and get structured extractions (jobs-to-be-done, pain points, workarounds) without manually tagging anything
- **See patterns across conversations** — which pains keep coming up, which jobs are universal, where the real opportunities are
- **Get prioritized "build this next" recommendations** with evidence chains that trace back to actual customer quotes
- **Prepare better interviews** with Mom Test guides tailored to your hypothesis
- **Score your interviews** after the fact — find out where you asked leading questions and how to improve
- **Practice with AI customers** before talking to real ones, with real-time feedback when you slip into bad habits
- **Track accuracy** of your synthetic interviews against real ones over time

## Quick start

```bash
# Requires Python 3.11+
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Set up your LLM keys
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY and/or OPENAI_API_KEY

# Seed sample data and launch
python scripts/seed_sample_data.py
./scripts/run_dev.sh
```

The API runs at `http://localhost:8000` (docs at `/docs`), and the UI at `http://localhost:8501`.

`seed_sample_data.py` creates two starter projects:
- `Elicit Validation` (synthetic fixtures in `tests/fixtures`)
- `Web Interview Examples` (paraphrased demos grounded in public JTBD interviews in `scripts/fixtures`)

After seeding, open the `Web Interview Examples` project in the UI and run:
1. Extraction on each interview
2. Cross-interview synthesis
3. Recommendation generation

## How it works

1. **You upload a transcript** (paste text or upload a file)
2. **AI extracts structured insights** — jobs-to-be-done, pain points, workarounds, and opportunities, each with supporting quotes and confidence scores
3. **After 2+ interviews, run synthesis** to find patterns across conversations
4. **Get recommendations** ranked by priority with full evidence chains back to the source material
5. **Before your next interview**, generate a Mom Test guide. After, score your technique.
6. **Practice first** with synthetic personas that behave like real customers — and call you out when you ask leading questions

Long-running extraction/synthesis/recommendation actions now run through an async job queue. The UI submits jobs and polls status so requests don't have to stay open until completion.

## Async Analysis Jobs (API)

Use these endpoints for non-blocking analysis:

- `POST /api/analysis/jobs/extract/{interview_id}`
- `POST /api/analysis/jobs/synthesize/{project_id}`
- `POST /api/analysis/jobs/recommend/{project_id}`
- `GET /api/analysis/jobs/{job_id}`
- `GET /api/analysis/jobs?project_id=<id>&limit=<n>`

Each job returns:
- `status`: `queued`, `running`, `completed`, or `failed`
- `result`: summary counts for completed jobs
- `error_message`: failure details when status is `failed`

## Demo Interview Sources

The `Web Interview Examples` transcripts are condensed paraphrases for demo/testing (not verbatim copies), grounded in these public interviews:

- [iPhone / smartphone purchase interview](https://jobstobedone.org/radio/iphone-jobs-to-be-done-interview/)
- [Camera purchase interview](https://jobstobedone.org/news/jobs-to-be-done-camera-interview/)
- [Mattress purchase interview](https://jobstobedone.org/radio/the-mattress-interview-part-one/)

## Project structure

```
discovery_engine/
  models/      SQLAlchemy data models
  schemas/     Pydantic schemas (API + LLM output parsing)
  engine/      Core logic (extraction, synthesis, recommendations, coaching, simulation, calibration)
  llm/         LLM client + 13 Jinja2 prompt templates
  api/         FastAPI routes
streamlit_app/ Streamlit UI (9 pages)
tests/         Tests + sample transcripts
scripts/       Seed data, dev launcher
```

## Configuration

Copy `.env.example` to `.env` and add your keys. Elicit uses three model tiers:

| Tier | Default | Used for |
|------|---------|----------|
| Primary | Claude Sonnet | Extraction, synthesis, recommendations |
| Fallback | GPT-4o | Automatic fallback if primary fails |
| Cheap | GPT-4o Mini | Quick validations (Mom Test checks) |

## Audio transcription

To transcribe audio interviews with Whisper:

```bash
pip install -e ".[whisper]"
```

Then upload audio files through the API. Requires ~1GB for the base model download.
