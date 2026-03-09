# Elicit

**Elicit what matters from customer interviews. Build the right thing.**

[![CI](https://github.com/npow/elicit/actions/workflows/ci.yml/badge.svg)](https://github.com/npow/elicit/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE) [![Docs](https://img.shields.io/badge/docs-mintlify-18a34a?style=flat-square)](https://mintlify.com/npow/elicit)

You did the interviews. You took the notes. But now you're staring at a pile of Google Docs trying to remember what that one PM said three months ago about dashboards. Sound familiar?

Paste in a transcript. Elicit extracts jobs-to-be-done, pain points, and workarounds with supporting quotes — then, after a few interviews, tells you what to build next with a ranked, evidence-backed recommendation you can take straight to your team.

---

**Input — raw interview transcript (excerpt):**

> **Sarah (PM, B2B SaaS):** When planning time comes around, I'm trying to remember what people said three months ago. I'll search through my notes but it's really hard to find patterns across multiple interviews. Probably 2-3 full days per quarter just re-reading notes and trying to pull out themes. I'll highlight things, copy-paste into a spreadsheet, try to tag them. It's a mess.
>
> The gap between "I have a bunch of interviews" and "I know what to build" — that's where I feel like I'm just guessing. And when I present my recommendations to leadership, I can't really trace back to specific evidence. It's like "trust me, I talked to customers." That doesn't fly anymore.

**Output — structured extractions, scored and quoted:**

```
JOB-TO-BE-DONE
  Synthesize interview data into a defensible, prioritized product decision
  importance: 9.1/10 · satisfaction: 2.0/10 · confidence: 0.94
  "connecting the dots across 10 interviews to find the real patterns —
   that's where I feel like I'm just guessing"

PAIN POINTS
  • Interview insights rot in unstructured notes, invisible at planning time [severity: high]
    "all that information just sits in my Google Docs...trying to remember
     what people said three months ago"

  • No evidence trail from customer voice to product decision  [severity: high]
    "I can't really trace back to specific evidence. 'Trust me, I talked
     to customers.' That doesn't fly anymore."

WORKAROUND
  • Manual highlight → copy-paste → spreadsheet to find cross-interview themes [effort: high]
    "I'll highlight things, copy paste into a spreadsheet, try to tag them.
     It's a mess."

OPPORTUNITY SCORE: 17.6 / 20
  Automate the synthesis layer — extract patterns across interviews and surface
  evidence-backed recommendations without the 2-3 day manual slog.
```

**After 3+ interviews, Elicit synthesizes across them and generates a ranked recommendation:**

```
#1 BUILD NOW  (priority: 0.91 · confidence: 0.88 · supported by 4/4 interviews)

  "Ship an automated synthesis view that surfaces recurring JTBD and pain
   patterns across all interviews, with evidence chains to specific quotes."

  Rationale: Every interviewed PM spends 2-3 days/quarter manually re-reading notes
  to find patterns they're not confident they're catching. Satisfaction with current
  workarounds (spreadsheets, Dovetail) is near zero. High importance, no good solution.

  Evidence:
    [pain]  "all that information just sits in my Google Docs"           — Sarah, interview 1
    [pain]  "I end up with conflicting information and I don't know why" — Maya, interview 2
    [job]   "connecting the dots across 10 interviews"                   — Sarah, interview 1
    [wa]    "copy paste into a spreadsheet, try to tag them. It's a mess"— Sarah, interview 1
```

---

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

Long-running extraction/synthesis/recommendation actions run through an async job queue. The UI submits jobs and polls status so requests don't have to stay open until completion.

Output quality safeguards:
- LLM score/type normalization (percentages, 0-10 scales, mixed string/number fields)
- Best-effort list parsing for partially malformed model output
- Deterministic fallback synthesis/recommendation generation when LLM parsing returns no usable items

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

## Project structure

```
discovery_engine/
  models/      SQLAlchemy data models
  schemas/     Pydantic schemas (API + LLM output parsing)
  engine/      Core logic (extraction, synthesis, recommendations, simulation)
  llm/         LLM client + 13 Jinja2 prompt templates
  api/         FastAPI routes
streamlit_app/ Streamlit UI (9 pages)
tests/         Tests + sample transcripts
scripts/       Seed data, dev launcher
```

## Demo Interview Sources

The `Web Interview Examples` transcripts are condensed paraphrases for demo/testing (not verbatim copies), grounded in these public interviews:

- [iPhone / smartphone purchase interview](https://jobstobedone.org/radio/iphone-jobs-to-be-done-interview/)
- [Camera purchase interview](https://jobstobedone.org/news/jobs-to-be-done-camera-interview/)
- [Mattress purchase interview](https://jobstobedone.org/radio/the-mattress-interview-part-one/)
