"""Uniform Tool interface. Every tool returns an Observation, never raises."""
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass
class Observation:
    ok: bool
    data: Any = None
    error: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None

    def to_dict(self):
        return asdict(self)


class Tool:
    name: str = "base"
    description: str = "base tool"
    schema: Dict[str, Any] = {}

    def execute(self, args: Dict[str, Any]) -> Observation:
        raise NotImplementedError

    def safe_execute(self, args: Dict[str, Any]) -> Observation:
        try:
            return self.execute(args or {})
        except Exception as e:
            return Observation(ok=False, error=f"{self.name} failed: {e}")
