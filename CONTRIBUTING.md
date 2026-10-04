# Contributing to Autonomous AI Task Worker

Thank you for your interest in contributing! This project demonstrates an autonomous AI worker prototype — contributions that improve reliability, tool coverage, or evaluation are especially welcome.

## Getting Started

```bash
git clone https://github.com/<your-username>/ai-task-worker.git
cd ai-task-worker
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 mock_env/seed_data.py
python3 tests/test_tools.py
python3 eval/run_eval.py
```

## Development Workflow

1. **Fork** the repository
2. **Create a feature branch**: `git checkout -b feat/your-feature`
3. **Make changes** with tests
4. **Run the full test suite**: `python3 tests/test_tools.py && python3 eval/run_eval.py`
5. **Update documentation** if behavior changes
6. **Submit a PR** with a clear description

## Code Standards

- **Type hints** on all public functions
- **Docstrings** for classes and non-trivial functions (Google style)
- **No silent failures** — tools must return `Observation{ok, data, error}`
- **Deterministic tests** — no external API calls in unit tests (use `MockLLM`)
- **Security**: Never commit API keys, secrets, or real credentials

## Adding a New Tool

1. Create `tools/your_tool.py` extending `Tool` base class
2. Implement `execute(args) -> Observation` (never raise, return error in Observation)
3. Add schema with clear descriptions for LLM function-calling
4. Register in `agent/loop.py` `TOOLS` dict
5. Add unit test in `tests/test_tools.py`
6. Update `README.md` tool table

## Adding a New Evaluation Task

1. Add entry to `eval/tasks.yaml`
2. Ensure it passes with `MODEL_PROVIDER=mock` (deterministic)
3. Run `python3 eval/run_eval.py` — all tasks must verify

## Reporting Issues

Use the issue templates:
- 🐛 **Bug Report** — for crashes, incorrect behavior
- ✨ **Feature Request** — for new tools, capabilities
- 📚 **Documentation** — for unclear docs

## Code of Conduct

Be respectful, inclusive, and constructive. This project follows the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

## Questions?

Open a [Discussion](https://github.com/<your-username>/ai-task-worker/discussions) or email f20240825@goa.bits-pilani.ac.in