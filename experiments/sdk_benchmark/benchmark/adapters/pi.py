"""Adapter for the Pi Coding Agent SDK (delegates to a Node runner)."""

from __future__ import annotations

from pathlib import Path

from .base import Adapter, SkillRunRequest, SkillRunResult
from ._subprocess import run_node_adapter


RUNNER = Path(__file__).resolve().parents[1] / "runners" / "pi_runner.mjs"


class PiAdapter(Adapter):
    name = "pi"

    def run(self, request: SkillRunRequest) -> SkillRunResult:
        return run_node_adapter(self.name, RUNNER, request)
