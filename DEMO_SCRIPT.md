# Demo Video Recording Script (2 minutes)

## Setup (before recording)

```bash
# Terminal 1: Clean state
cd ai-task-worker
rm -f mock_env/erp.db trajectory_logs/*.json reports/gst_note.md
python3 mock_env/seed_data.py

# Terminal 2: Start ERP server for browser demo (optional)
uvicorn mock_env.erp_server:app --port 8000
```

## Scene 1: Invoice Task — CLI Auto-approve (45s)

```bash
# Record this terminal
REQUIRE_APPROVAL=false AUTO_APPROVE=1 MODEL_PROVIDER=mock \
  python3 -m ui.cli "Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal system." --auto-approve
```

**Narrate while running:**
> "The agent searches the inbox, finds 3 Acme invoices, picks the latest by date (INV-Acme-2026-09-28), parses it for amount $4820.50 and due date 2026-10-28, submits to ERP via API, and the independent verifier confirms the row exists in SQLite."

**Show after completion:**
```bash
sqlite3 mock_env/erp.db "SELECT * FROM invoices WHERE vendor='ACME CORP';"
cat trajectory_logs/task_*.json | head -60
```

## Scene 2: Research Task — CLI (30s)

```bash
REQUIRE_APPROVAL=false python3 -m ui.cli "Research current GST rate for services in India, save a 1-page summary to reports/gst_note.md with sources." --auto-approve
```

**Narrate:**
> "Same agent loop, different tools: web search (keyless DuckDuckGo), fetch top source, write markdown report with citations. Verifier checks file exists, contains a percentage rate, and has source URLs."

**Show:**
```bash
cat reports/gst_note.md
```

## Scene 3: Failure Recovery — Trajectory Log (15s)

```bash
# Show a log where corrupt invoice was skipped
cat trajectory_logs/task_*.json | jq '.history[] | select(.action=="invoice.parse") | {step, thought, action, observation: .observation.ok}' | head -20
```

**Narrate:**
> "When the corrupt invoice parse fails (ok=false), the observation becomes the next prompt — the agent automatically tries the next candidate without human intervention."

## Scene 4: Browser Fallback (20s) — Optional but impressive

```bash
# Kill ERP server to force fallback
pkill -f "uvicorn mock_env.erp_server"

REQUIRE_APPROVAL=false AUTO_APPROVE=1 MODEL_PROVIDER=mock \
  python3 -m ui.cli "Find latest invoice from Globex, enter into ERP." --auto-approve
```

**Narrate:**
> "With the ERP UI down, the browser tool fails — the agent sees the error observation and falls back to the reliable API path. This is autonomous error recovery."

## Scene 5: Streamlit UI (15s)

```bash
# Restart ERP server
uvicorn mock_env.erp_server:app --port 8000 &
streamlit run ui/app.py
```

**Show in browser:**
- Paste task in input
- Click "Run task"
- Watch live Thought → Action → Observation expanders
- Show Facts JSON + Verification result

## Recording Tips

- Use **OBS Studio** (free) or **QuickTime** (macOS)
- Record at 1920x1080, 30fps
- Terminal font: 14pt, high contrast theme
- Keep narration concise — let the output speak
- Total target: **~2 minutes**

## Post-Recording

1. Trim silence, speed up typing parts 2x
2. Add captions for key moments (search, parse, verify)
3. Upload to YouTube (unlisted) or Loom
4. Link in GitHub README + submission form