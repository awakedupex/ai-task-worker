"""Working memory: goal + facts discovered + full trajectory."""
import time
from typing import Any, Dict, List


class Memory:
    def __init__(self, goal: str):
        self.goal = goal
        self.facts: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []
        self.retries: Dict[str, int] = {}
        self.task_id = f"task_{int(time.time())}"

    def update(self, thought: str, action: str, action_args: Dict, obs_dict: Dict):
        self.history.append({
            "step": len(self.history) + 1,
            "thought": thought,
            "action": action,
            "args": action_args,
            "observation": obs_dict,
        })
        # track retries per tool
        if not obs_dict.get("ok", False):
            self.retries[action] = self.retries.get(action, 0) + 1
        # auto-promote useful data into facts
        data = obs_dict.get("data")
        if isinstance(data, dict):
            for k in ("vendor", "amount", "due_date", "invoice_id", "invoice_path",
                       "erp_id", "file_path", "sources", "candidates"):
                if k in data and data[k] is not None:
                    self.facts[k] = data[k]

    def prompt_context(self, last_n: int = 8) -> str:
        lines = [f"GOAL: {self.goal}", f"KNOWN FACTS: {self.facts}", "RECENT HISTORY:"]
        for h in self.history[-last_n:]:
            obs = h["observation"]
            ok = obs.get("ok")
            summary = str(obs.get("data"))[:600] if ok else f"ERROR: {obs.get('error')}"
            lines.append(f" Step {h['step']}: thought={h['thought'][:300]} | action={h['action']} args={h['args']} -> ok={ok} {summary}")
        if not self.history:
            lines.append(" (no actions yet)")
        return "\n".join(lines)
