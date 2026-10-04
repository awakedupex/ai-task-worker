"""ReAct orchestrator: think -> act (one tool) -> observe -> remember -> repeat."""
import os
import json
import copy
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from agent.memory import Memory
from agent.llm import get_llm
from agent import verifier
from tools.base import Observation
from tools.files import ListTool, ReadTool, WriteTool
from tools.inbox import InboxSearchTool, InvoiceParseTool
from tools.erp_api import ERPCreateTool, ERPGetTool, ERPListTool
from tools.web import WebSearchTool, WebFetchTool
from tools.browser import BrowserOpenTool, BrowserFillSubmitTool
from tools.human import AskTool, ApproveTool

TOOLS = {}
for t in [ListTool(), ReadTool(), WriteTool(), InboxSearchTool(), InvoiceParseTool(),
          ERPCreateTool(), ERPGetTool(), ERPListTool(), WebSearchTool(), WebFetchTool(),
          BrowserOpenTool(), BrowserFillSubmitTool(), AskTool(), ApproveTool()]:
    TOOLS[t.name] = t


def tools_schema():
    return [{"name": t.name, "description": t.description, "parameters": t.schema}
            for t in TOOLS.values()]


def autofill(tool_name: str, args: dict, facts: dict) -> dict:
    """Fill missing args from memory facts so LLM doesn't have to repeat values."""
    args = dict(args or {})
    if tool_name == "erp_api.create":
        for k in ("vendor", "amount", "due_date", "invoice_id"):
            if k not in args or args[k] in (None, "", 0):
                if k in facts and facts[k]:
                    args[k] = facts[k]
        # invoice_id -> source_file compat
        if "invoice_id" in args and "source_file" not in args:
            args["invoice_id"] = args.get("invoice_id")
    if tool_name == "invoice.parse" and not args.get("path"):
        cands = facts.get("candidates")
        if isinstance(cands, list) and cands:
            # skip corrupt
            for c in cands:
                if "corrupt" not in str(c.get("path", "")).lower():
                    args["path"] = c["path"]
                    break
    if tool_name == "fs.write" and not args.get("path"):
        # research default
        args["path"] = "reports/gst_note.md"
        if not args.get("content"):
            srcs = facts.get("sources") or facts.get("urls") or []
            args["content"] = WriteTool()._default_report({"sources": ", ".join(srcs) if srcs else "web.search"})
    if tool_name == "web.fetch" and not args.get("url"):
        srcs = facts.get("sources") or facts.get("urls") or []
        if srcs:
            args["url"] = srcs[0]
    return args


def run(task: str, max_steps: int = 15, auto_approve: bool = False, verbose: bool = True):
    if auto_approve:
        os.environ["AUTO_APPROVE"] = "1"
    max_steps = int(os.getenv("MAX_STEPS", max_steps))
    mem = Memory(task)
    llm = get_llm()
    schema = tools_schema()

    if verbose:
        print(f"\n=== TASK: {task} ===\n(provider={os.getenv('MODEL_PROVIDER','mock')})")

    for i in range(max_steps):
        decision = llm.decide(task, mem.prompt_context(), schema)
        if decision.get("finish"):
            break
        thought = decision.get("thought", "")
        tool_name = decision.get("tool", "")
        args = decision.get("args", {}) or {}
        if tool_name not in TOOLS:
            mem.update(thought, tool_name or "unknown",
                       args, {"ok": False, "error": f"unknown tool {tool_name}"})
            if verbose:
                print(f"[step {i+1}] UNKNOWN TOOL {tool_name}")
            continue
        args = autofill(tool_name, args, mem.facts)
        # approval gate for risky writes
        if tool_name in ("erp_api.create", "erp_browser.submit") and not auto_approve \
                and os.getenv("REQUIRE_APPROVAL", "true").lower() in ("true", "1", "yes"):
            # ensure we have real values before asking
            if tool_name == "erp_api.create" and not all([args.get("vendor"), args.get("amount"), args.get("due_date")]):
                mem.update(thought, tool_name, args,
                           {"ok": False, "error": "missing vendor/amount/due_date, parse invoice first"})
                continue
            print(f"\n[APPROVAL] About to call {tool_name} with {args}")
            try:
                ans = input("Approve? [Y/n]: ").strip().lower()
            except EOFError:
                ans = "y"
            if ans in ("n", "no"):
                mem.update(thought, tool_name, args, {"ok": False, "error": "user denied approval"})
                if verbose:
                    print(" -> denied by user")
                continue
        obs: Observation = TOOLS[tool_name].safe_execute(args)
        mem.update(thought, tool_name, args, obs.to_dict())
        if verbose:
            status = "OK" if obs.ok else "FAIL"
            print(f"[step {i+1}] {thought}\n  -> {tool_name} {args} [{status}]"
                  f" {str(obs.data)[:300] if obs.ok else obs.error}")
        # smart recovery: corrupt invoice -> auto-try next candidate next loop
        # (LLM sees error observation and picks alternative; nothing special needed)

    verdict = verifier.verify(task, mem.facts)
    summary = decision.get("summary", "") if decision.get("finish") else "Stopped after max steps."
    result = {
        "task": task, "task_id": mem.task_id, "facts": mem.facts,
        "history": mem.history, "verification": verdict, "summary": summary,
    }
    os.makedirs("trajectory_logs", exist_ok=True)
    with open(f"trajectory_logs/{mem.task_id}.json", "w") as f:
        json.dump(result, f, indent=2, default=str)

    if verbose:
        print(f"\n=== DONE verified={verdict['verified']} ===")
        print("Detail:", verdict["detail"])
        print("Facts:", json.dumps(mem.facts, indent=2, default=str))
        print(f"Log: trajectory_logs/{mem.task_id}.json")
    return result
