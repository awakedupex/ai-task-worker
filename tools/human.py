"""Human-in-the-loop tools: clarification + approval."""
import os
from tools.base import Tool, Observation

AUTO_APPROVE = os.getenv("REQUIRE_APPROVAL", "true").lower() not in ("true", "1", "yes")


class AskTool(Tool):
    name = "human.ask"
    description = "Ask the user a clarifying question when blocked/ambiguous. Args: question."
    schema = {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]}

    def execute(self, args):
        q = args.get("question", "Need clarification")
        print(f"\n[WORKER NEEDS INPUT] {q}")
        try:
            ans = input("Your answer (or 'proceed'): ").strip()
        except EOFError:
            ans = "proceed"
        return Observation(ok=True, data={"answer": ans, "question": q})


class ApproveTool(Tool):
    name = "human.approve"
    description = "Request approval before a risky action. Args: summary."
    schema = {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}

    def execute(self, args):
        summary = args.get("summary", "")
        if AUTO_APPROVE or os.getenv("AUTO_APPROVE") == "1":
            return Observation(ok=True, data={"approved": True, "auto": True})
        print(f"\n[APPROVAL REQUIRED] {summary}")
        try:
            ans = input("Approve? [y/N]: ").strip().lower()
        except EOFError:
            ans = "y"
        if ans in ("y", "yes"):
            return Observation(ok=True, data={"approved": True})
        return Observation(ok=False, error="user denied approval")
