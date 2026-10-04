# Autonomous AI Task Worker 🤖

> **A prototype autonomous agent that takes natural-language goals and executes them end-to-end using real tools — with memory, retries, verification, and human-in-the-loop safety.**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32%2B-FF4B4B?logo=streamlit)](https://streamlit.io)
[![Playwright](https://img.shields.io/badge/Playwright-1.42%2B-2EAD33?logo=playwright)](https://playwright.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

---

## 🎯 What This Does

Give it a goal in plain English, and it **figures out the steps, uses tools, recovers from errors, and proves it worked** — no step-by-step instructions needed.

### Demo Tasks (same agent, different tools)

| Task | Tools Used | Verification |
|------|------------|--------------|
| `Find latest invoice from Acme Corp, extract amount + due date, enter into ERP` | `inbox.search` → `invoice.parse` → `erp_api.create` (or `erp_browser.submit`) | SQLite `SELECT` confirms row exists |
| `Research GST rate for services in India, save summary to reports/gst_note.md` | `web.search` → `web.fetch` → `fs.write` | File exists + contains `%` rate + source URLs |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER GOAL (NL)                           │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  INTERFACE: CLI (streaming trace)  │  Streamlit (live + evidence) │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    REACT ORCHESTRATOR (agent/loop.py)           │
│  Think → Act (1 tool) → Observe → Update Memory → Repeat (≤15)  │
│  • Autofills args from memory (ERP create gets parsed facts)    │
│  • Approval gate for risky writes                               │
│  • Error = observation → LLM retries / tries alternative        │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  LOCAL TOOLS  │     │ MOCK COMPANY  │     │ EXTERNAL TOOLS│
│ fs.list/read  │     │ ERP (FastAPI  │     │ web.search    │
│ fs.write      │     │  + SQLite +   │     │ web.fetch     │
│ inbox.search  │     │  HTML UI)     │     │ (DuckDuckGo)  │
│ invoice.parse │     │ erp_browser   │     │               │
│ erp_api.*     │     │ (Playwright)  │     │               │
└───────────────┘     └───────────────┘     └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INDEPENDENT VERIFIER                         │
│  • Invoice: SQL row matches vendor/amount/due_date              │
│  • Research: file exists + rate % + ≥1 source URL               │
│  • NOT LLM self-report                                          │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  OUTPUT: Summary + Evidence (ERP ID, file path, screenshots,    │
│          trajectory_logs/task_<ts>.json)                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start (2 minutes)

```bash
# 1. Clone & install
git clone https://github.com/<your-username>/ai-task-worker.git
cd ai-task-worker
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure (zero keys needed for demo!)
cp .env.example .env   # MODEL_PROVIDER=mock works offline

# 3. Seed mock environment
python3 mock_env/seed_data.py

# 4. Run invoice task (auto-approve for demo)
REQUIRE_APPROVAL=false AUTO_APPROVE=1 MODEL_PROVIDER=mock \
  python3 -m ui.cli "Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal system." --auto-approve

# 5. Run research task
REQUIRE_APPROVAL=false python3 -m ui.cli "Research current GST rate for services in India, save a 1-page summary to reports/gst_note.md with sources." --auto-approve

# 6. Full eval (3/3 should verify)
python3 eval/run_eval.py
python3 tests/test_tools.py
```

### Visual UI + Browser Demo

```bash
# Terminal 1: Mock ERP server (REST + HTML form at localhost:8000/ui)
uvicorn mock_env.erp_server:app --port 8000

# Terminal 2: Streamlit live trace viewer
streamlit run ui/app.py
```

---

## 🧠 Key Design Decisions

| Principle | Implementation |
|-----------|----------------|
| **Autonomy over scripts** | Single ReAct loop (not planner+executor); LLM picks next action from observation |
| **Execution over mocks** | Real SQLite writes, real file I/O, real HTTP, real browser (Playwright on localhost) |
| **Reliability by design** | Tools return `Observation{ok,data,error}` — never crash loop; error → retry/fallback |
| **Verification ≠ self-report** | Independent DB/file checks; agent cannot claim success without evidence |
| **Generalization** | Same loop handles both tasks; new task = new tools, no loop changes |
| **Human-in-loop at risk only** | Approval for ERP writes; `human.ask` on ambiguity/ties; logged as evidence |
| **Zero-key demo** | `MockLLM` deterministic policy runs offline; swap to `gpt-4o-mini`/`claude-3.5-haiku` via `.env` |

---

## 🛠 Toolset

| Tool | Description | Evidence |
|------|-------------|----------|
| `fs.list/read/write` | Local filesystem ops | file paths, byte counts |
| `inbox.search` | Finds vendor invoices in `mock_env/inbox/` | candidate list + dates |
| `invoice.parse` | Regex + `pdfplumber`/`pypdf` extraction | amount, due_date, vendor, source file |
| `erp_api.create/get/list` | SQLite REST API (fast, reliable) | ERP row ID |
| `erp_browser.open/submit` | Playwright on `localhost:8000/ui` | screenshots (`trajectory_logs/erp_*.png`) |
| `web.search/fetch` | Keyless DuckDuckGo + `requests`/`bs4` | snippets, URLs, fetched text |
| `human.ask/approve` | CLI/Streamlit prompts | user response logged |

---

## 📁 Project Structure

```
ai-task-worker/
├── agent/                 # Core agent logic
│   ├── loop.py           # ReAct orchestrator (think→act→observe)
│   ├── memory.py         # Working memory: goal + facts + trajectory
│   ├── llm.py            # Multi-provider LLM wrapper (OpenAI/Anthropic/Ollama/Mock)
│   ├── verifier.py       # Independent outcome verification
│   └── prompts.py        # System prompt
├── tools/                # Uniform Tool interface
│   ├── base.py           # Tool + Observation dataclasses
│   ├── files.py          # fs.list/read/write
│   ├── inbox.py          # inbox.search + invoice.parse
│   ├── erp_api.py        # ERP SQLite CRUD
│   ├── browser.py        # Playwright ERP UI automation
│   ├── web.py            # DuckDuckGo search + fetch
│   └── human.py          # Clarification + approval
├── mock_env/             # Local company sandbox
│   ├── seed_data.py      # 7 invoices (varied layouts, corrupt, ambiguous dates)
│   ├── erp_server.py     # FastAPI REST + HTML form
│   └── erp.db            # SQLite (gitignored)
├── ui/                   # Interfaces
│   ├── cli.py            # Streaming Thought/Action/Observation
│   └── app.py            # Streamlit live trace + evidence
├── eval/                 # Evaluation harness
│   ├── run_eval.py       # Headless 3-task suite
│   └── tasks.yaml        # Task definitions
├── tests/                # Unit + integration tests
│   └── test_tools.py     # Parse, ERP, end-to-end
├── trajectory_logs/      # Auto-generated JSON traces (gitignored)
├── reports/              # Generated research files
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🔧 Configuration (`.env`)

```bash
# Pick ONE provider — only that key needed
MODEL_PROVIDER=mock              # mock | openai | anthropic | gemini | ollama
MODEL_NAME=gpt-4o-mini

# OpenAI
# OPENAI_API_KEY=sk-...

# Anthropic
# ANTHROPIC_API_KEY=sk-ant-...

# Gemini (OpenAI-compat endpoint)
# GOOGLE_API_KEY=...

# Ollama (local, no key)
# OLLAMA_HOST=http://localhost:11434
# MODEL_NAME=llama3.1:8b

ERP_BASE_URL=http://localhost:8000
ERP_DB_PATH=mock_env/erp.db
INBOX_DIR=mock_env/inbox
MAX_STEPS=15
REQUIRE_APPROVAL=true
```

---

## 📊 Evaluation Results

```bash
$ python3 eval/run_eval.py

######## EVAL: Find the latest invoice from Acme Corp...
✅ VERIFIED: ERP row id=3 vendor=ACME CORP amount=4820.5 due=2026-10-28

######## EVAL: Find invoice from Globex...
✅ VERIFIED: ERP row id=5 vendor=GLOBEX amount=12400.75 due=2026-10-15

######## EVAL: Research current GST rate for services in India...
✅ VERIFIED: reports/gst_note.md exists (457 chars) with rate + sources

==== 3/3 verified ====
```

---

## 🎬 Demo Video Script

1. **Invoice flow** (30s): CLI runs → shows 3 Acme candidates → parses latest (`$4820.50`, `2026-10-28`) → creates ERP entry → verifier `SELECT` confirms → trajectory log displayed
2. **Research flow** (30s): CLI runs → web search → fetch → writes `reports/gst_note.md` → verifier checks file + rate + sources
3. **Failure recovery** (15s): Show `trajectory_logs/*.json` where corrupt invoice parse fails → agent picks next candidate automatically
4. **Browser fallback** (15s): Start `uvicorn mock_env.erp_server:app` → run with `erp_browser.submit` → show screenshot evidence → kill server → agent falls back to `erp_api.create`

---

## ⚠️ Known Limitations

- **Parser**: Regex-based for seeded layouts; scanned PDFs need OCR (`pytesseract` not bundled)
- **Browser**: Only works on local ERP UI (no auth, CAPTCHA, dynamic JS sites)
- **Date ambiguity**: `05/06/2026` → `2026-06-05` (assumes DD/MM/YYYY)
- **MockLLM**: Deterministic demo policy; open-ended autonomy needs `gpt-4o-mini`/Haiku
- **No sandboxing**: Single-user, single-task, no cross-task memory persistence

---

## 🗺 Roadmap (with 2 more weeks)

- [ ] Docker sandbox per task + Playwright trace/video evidence
- [ ] Persistent vector memory (Chroma/FAISS) + confidence scoring
- [ ] Calendar/Sheets/Gmail sandbox tools + OCR for scanned invoices
- [ ] Multi-task eval dashboard with latency/cost tracking
- [ ] Swap `MockLLM` → `gpt-4o-mini`; stress-test 20+ varied tasks
- [ ] Cost/latency ticker, PII redaction in logs

---

## 🤝 Contributing

PRs welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork → feature branch → PR
2. Run `python3 tests/test_tools.py && python3 eval/run_eval.py`
3. Update docs if behavior changes

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- Built for [CentrAlign AI](https://centralign.ai) Founding Engineer / AI Engineering Intern application
- Inspired by ReAct, AutoGPT, and the "computer-using agent" paradigm
- Mock environment pattern from [Browserbase](https://browserbase.com) / [Anthropic Computer Use](https://www.anthropic.com/news/computer-use)

---

**Built with ❤️ for the CentrAlign AI hiring challenge** — [Adwait Eklavya](https://github.com/adwaiteklavya) · [LinkedIn](https://linkedin.com/in/adwaiteklavya) · f20240825@goa.bits-pilani.ac.in