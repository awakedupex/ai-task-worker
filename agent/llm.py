"""LLM wrapper: OpenAI / Anthropic / Gemini / Ollama / mock (no key needed)."""
import os
import json
import re
from typing import Dict, Any, List


class LLMDecision(dict):
    pass


class BaseLLM:
    def decide(self, goal: str, memory_context: str, tools_schema: List[Dict]) -> Dict[str, Any]:
        raise NotImplementedError


class MockLLM(BaseLLM):
    """Deterministic offline policy so demo works with MODEL_PROVIDER=mock.
    Handles invoice tasks + web/file tasks. Good enough to prove autonomy loop,
    error recovery, and verification without an API key."""

    def decide(self, goal: str, memory_context: str, tools_schema: List[Dict]) -> Dict[str, Any]:
        g = goal.lower()
        has = lambda *names: True  # history inspection done via context string
        ctx = memory_context.lower()

        is_invoice = "invoice" in g
        is_research = any(w in g for w in ("gst", "research", "summary", "report", "rate"))

        # --- invoice flow ---
        if is_invoice:
            if "inbox.search" not in ctx and "candidates" not in ctx:
                vendor = self._extract_vendor(goal)
                return self._act("Searching inbox for vendor invoices",
                                 "inbox.search", {"vendor": vendor, "sort": "latest"})
            if "invoice.parse" not in ctx:
                # pick latest candidate path from memory context if visible, else let tool pick latest
                m = re.search(r"'path': '([^']+)'", memory_context)
                path = m.group(1) if m else ""
                # if parse previously failed, try next: tool handles fallback, just retry with explicit path
                return self._act("Parsing latest invoice for amount/due date",
                                 "invoice.parse", {"path": path} if path else {})
            if "erp_id" not in ctx and "erp_api.create" not in ctx.replace("erp_api.create_entry", ""):
                return self._act("Submitting extracted invoice to ERP (needs approval in UI/CLI)",
                                 "erp_api.create", {})
            return {"finish": True,
                    "thought": "ERP entry created, ready to verify",
                    "summary": "Invoice processed and entered into ERP."}
        # --- research flow ---
        if is_research:
            if "web.search" not in ctx:
                q = "GST rate services India 2026" if "gst" in g else goal[:120]
                return self._act("Searching web for current rates", "web.search", {"query": q})
            if "web.fetch" not in ctx and "fs.write" not in ctx:
                m = re.search(r"https?://[^\s'\"]+", memory_context)
                url = m.group(0) if m else ""
                if url:
                    return self._act("Fetching top source", "web.fetch", {"url": url})
                return self._act("Writing report from search snippets", "fs.write", {})
            if "fs.write" not in ctx:
                return self._act("Writing summary report to file", "fs.write", {})
            return {"finish": True, "thought": "Report written", "summary": "Research report saved."}

        # generic fallback: explore files then finish
        if "fs.list" not in ctx:
            return self._act("Exploring workspace", "fs.list", {"path": "."})
        return {"finish": True, "thought": "No further autonomous action possible, asking user",
                "summary": "", "needs_user": True}

    def _extract_vendor(self, goal: str) -> str:
        m = re.search(r"from\s+([A-Za-z][A-Za-z0-9 &.\-]{1,40})", goal, re.I)
        if m:
            v = m.group(1).strip().rstrip(",.")
            # strip trailing words like 'extract', 'latest', 'invoice'
            v = re.sub(r"\b(extract|latest|invoice).*$", "", v, flags=re.I).strip()
            return v or ""
        return ""

    def _act(self, thought, tool, args):
        return {"thought": thought, "tool": tool, "args": args}


def get_llm():
    provider = os.getenv("MODEL_PROVIDER", "mock").lower()
    if provider in ("", "mock"):
        return MockLLM()
    if provider == "openai":
        return OpenAILLM()
    if provider == "anthropic":
        return AnthropicLLM()
    if provider == "ollama":
        return OllamaLLM()
    if provider == "gemini":
        return OpenAILLM(base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
    return MockLLM()


class OpenAILLM(BaseLLM):
    def __init__(self, base_url=None):
        self.base_url = base_url

    def decide(self, goal, memory_context, tools_schema):
        try:
            from openai import OpenAI
        except ImportError:
            return MockLLM().decide(goal, memory_context, tools_schema)
        import os
        key = os.getenv("OPENAI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            return MockLLM().decide(goal, memory_context, tools_schema)
        client = OpenAI(api_key=key, base_url=self.base_url) if self.base_url else OpenAI(api_key=key)
        model = os.getenv("MODEL_NAME", "gpt-4o-mini")
        from agent.prompts import SYSTEM_PROMPT
        tools = [{"type": "function",
                  "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}}
                 for t in tools_schema]
        tools.append({"type": "function", "function": {
            "name": "finish",
            "description": "Call when goal is done. Args: summary string.",
            "parameters": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}}})
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": f"TASK: {goal}\n\n{memory_context}\n\nDecide ONE next tool call (or finish)."}],
                tools=tools, tool_choice="auto", temperature=0.2)
            msg = resp.choices[0].message
            if msg.tool_calls:
                tc = msg.tool_calls[0]
                args = json.loads(tc.function.arguments or "{}")
                if tc.function.name == "finish":
                    return {"finish": True, "thought": msg.content or "", "summary": args.get("summary", "")}
                return {"thought": msg.content or f"Calling {tc.function.name}", "tool": tc.function.name, "args": args}
            return {"finish": True, "thought": msg.content or "", "summary": msg.content or ""}
        except Exception as e:
            # graceful fallback to mock policy on API error (reliability)
            fallback = MockLLM().decide(goal, memory_context, tools_schema)
            fallback["thought"] = f"(LLM API error {e}, using fallback) " + fallback.get("thought", "")
            return fallback


class AnthropicLLM(BaseLLM):
    def decide(self, goal, memory_context, tools_schema):
        try:
            import anthropic
        except ImportError:
            return MockLLM().decide(goal, memory_context, tools_schema)
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            return MockLLM().decide(goal, memory_context, tools_schema)
        try:
            client = anthropic.Anthropic(api_key=key)
            model = os.getenv("MODEL_NAME", "claude-3-5-haiku-latest")
            from agent.prompts import SYSTEM_PROMPT
            # simplify: ask for JSON decision (avoids tool-use API version drift)
            schema_txt = json.dumps([{"name": t["name"], "desc": t["description"]} for t in tools_schema])
            msg = client.messages.create(
                model=model, max_tokens=600, temperature=0.2,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user",
                           "content": f"TASK: {goal}\n{memory_context}\nTOOLS: {schema_txt}\nReply ONLY JSON: {{\"thought\":str, \"tool\":str, \"args\":dict}} or {{\"finish\":true, \"summary\":str}}"}])
            txt = msg.content[0].text
            m = re.search(r"\{.*\}", txt, re.S)
            return json.loads(m.group(0)) if m else {"finish": True, "summary": txt}
        except Exception as e:
            f = MockLLM().decide(goal, memory_context, tools_schema)
            f["thought"] = f"(Anthropic error {e}, fallback) " + f.get("thought", "")
            return f


class OllamaLLM(BaseLLM):
    def decide(self, goal, memory_context, tools_schema):
        import urllib.request
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        model = os.getenv("MODEL_NAME", "llama3.1:8b")
        from agent.prompts import SYSTEM_PROMPT
        schema_txt = json.dumps([{"name": t["name"], "description": t["description"]} for t in tools_schema])
        prompt = f"{SYSTEM_PROMPT}\nTASK: {goal}\n{memory_context}\nTOOLS: {schema_txt}\nReply ONLY JSON: {{\"thought\":str, \"tool\":str, \"args\":dict}} or {{\"finish\":true, \"summary\":str}}"
        try:
            req = urllib.request.Request(f"{host}/api/generate",
                                         data=json.dumps({"model": model, "prompt": prompt, "stream": False}).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                out = json.loads(r.read().decode())
            txt = out.get("response", "")
            m = re.search(r"\{.*\}", txt, re.S)
            return json.loads(m.group(0)) if m else MockLLM().decide(goal, memory_context, tools_schema)
        except Exception as e:
            f = MockLLM().decide(goal, memory_context, tools_schema)
            f["thought"] = f"(Ollama error {e}, fallback) " + f.get("thought", "")
            return f
