"""CLI entry: python -m ui.cli "your task" [--auto-approve]"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.loop import run


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    auto = "--auto-approve" in sys.argv or "--auto" in sys.argv
    if not args:
        print('Usage: python -m ui.cli "Find latest invoice from Acme Corp..." [--auto-approve]')
        print('Other example: python -m ui.cli "Research current GST rate for services in India, save summary to reports/gst_note.md" --auto-approve')
        return
    task = " ".join(args)
    run(task, auto_approve=auto)


if __name__ == "__main__":
    main()
