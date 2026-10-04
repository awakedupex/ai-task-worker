"""Run all eval tasks headless (auto-approve). Usage: python eval/run_eval.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("MODEL_PROVIDER", "mock")
os.environ["AUTO_APPROVE"] = "1"
os.environ["REQUIRE_APPROVAL"] = "false"
from agent.loop import run

TASKS = [
    "Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal system.",
    "Find invoice from Globex, get amount and due date, store in internal system.",
    "Research current GST rate for services in India, save a 1-page summary to reports/gst_note.md with sources.",
]
if __name__ == "__main__":
    ok = 0
    for t in TASKS:
        print("\n######## EVAL:", t)
        r = run(t, auto_approve=True, verbose=True)
        v = r["verification"]["verified"]
        ok += 1 if v else 0
        print("EVAL RESULT verified =", v)
    print(f"\n==== {ok}/{len(TASKS)} verified ====")
