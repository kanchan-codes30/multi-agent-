# Multi-Agent AI Research Assistant

A collaborative AI system where multiple specialized agents work together to
retrieve, summarize, compare, and compile research into structured reports.

## Modules Implemented

| # | Module | Where |
|---|--------|-------|
| 1 | User Login | `app.py` (`/login`, `/signup`, `/logout`), `database/db.py` |
| 2 | Research Topic Input | `templates/research_input.html`, `/research` route |
| 3 | Information Retrieval Agent | `agents/retrieval_agent.py` (Wikipedia + DuckDuckGo APIs) |
| 4 | Summarization Agent | `agents/summarization_agent.py` (HuggingFace transformer + extractive fallback) |
| 5 | Comparison & Analysis Agent | `agents/comparison_agent.py` (TF-IDF cosine similarity) |
| 6 | Report Generation Agent | `agents/report_agent.py` |
| 7 | Citation Management | `agents/citation_agent.py` (APA-style) |
| 8 | Research History | `/history` route, `templates/history.html` |
| 9 | Dashboard | `/dashboard` route, `templates/dashboard.html` |
| 10 | Export Reports | `/export/<id>/<format>` — PDF, DOCX, TXT |

## Architecture

```
User → Flask App → Orchestrator
                        │
        ┌───────────────┼────────────────┬─────────────────┬──────────────┐
        ▼               ▼                ▼                 ▼              ▼
  Retrieval Agent → Summarization → Comparison Agent → Citation Agent → Report Agent
   (Wikipedia,        Agent          (TF-IDF               (APA format)   (final compile)
    DuckDuckGo)        (HF model)     similarity)
        │               │                │                 │              │
        └───────────────┴────────────────┴─────────────────┴──────────────┘
                                     │
                              SQLite Database
                     (users, sessions, sources, summaries,
                          comparisons, reports)
```

Each agent inherits from `BaseAgent` (`agents/base_agent.py`) and exposes a
`run()` method. The `ResearchOrchestrator` (`agents/orchestrator.py`) calls
them in sequence, passing the output of one as input to the next — this is
the "multi-agent collaboration" at the heart of the project.

## Setup

```bash
cd research_assistant
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:5000** in your browser.

> **Note on the Summarization Agent:** it first tries to load a Hugging Face
> `transformers` model (`sshleifer/distilbart-cnn-12-6`) for abstractive
> summarization. This requires the `transformers` and `torch` packages and a
> one-time model download (~300MB) on first run. If those aren't installed,
> or there's no internet access, it automatically falls back to a built-in
> extractive (TF-IDF-style) summarizer — the app works either way.

> **Note on Retrieval Agent:** uses free, keyless public APIs (Wikipedia,
> DuckDuckGo). No API key needed. Requires internet access at runtime.

## Folder Structure

```
research_assistant/
├── app.py                     # Flask app, all routes
├── requirements.txt
├── agents/
│   ├── base_agent.py           # Abstract base class for all agents
│   ├── retrieval_agent.py      # Module 3
│   ├── summarization_agent.py  # Module 4
│   ├── comparison_agent.py     # Module 5
│   ├── citation_agent.py       # Module 7
│   ├── report_agent.py         # Module 6
│   └── orchestrator.py         # Coordinates all agents
├── database/
│   └── db.py                   # SQLite models + helper functions
├── utils/
│   └── export_utils.py         # PDF/DOCX export (Module 10)
├── templates/                  # Jinja2 HTML templates
├── static/
│   ├── css/style.css
│   └── js/main.js
└── exports/                     # Generated PDF/DOCX/TXT files land here
```

## Database Schema

- **users** — id, username, email, password_hash, created_at
- **research_sessions** — id, user_id, topic, status, created_at
- **sources** — id, session_id, title, url, raw_content, source_type
- **summaries** — id, source_id, summary_text
- **comparisons** — id, session_id, comparison_text, similarities, differences
- **reports** — id, session_id, title, content, citations

## How a Research Request Flows

1. User logs in and submits a topic on the **Research Topic Input** page.
2. A `research_sessions` row is created with status `pending`.
3. The **Orchestrator** runs the pipeline:
   - **Retrieval Agent** fetches raw text from Wikipedia/DuckDuckGo → saved to `sources`.
   - **Summarization Agent** condenses each source → saved to `summaries`.
   - **Comparison Agent** computes similarity/differences across sources → saved to `comparisons`.
   - **Citation Agent** formats APA-style references.
   - **Report Agent** compiles everything into one structured Markdown report → saved to `reports`.
4. Session status becomes `completed`.
5. User views the report, sees per-source summaries and the comparison,
   and can **export** it as PDF, DOCX, or TXT.
6. Everything is visible later in **History** and reflected in **Dashboard** stats.

## Extending This Project

- **Swap in a paid LLM** (OpenAI/Claude API) for higher-quality summarization
  and report writing by editing `agents/summarization_agent.py` and
  `agents/report_agent.py`.
- **Add more retrieval sources** (arXiv, NewsAPI, Google Scholar) by adding
  methods to `RetrievalAgent`.
- **Add role-based access** or team-shared research by extending the `users`
  table with roles/organizations.
