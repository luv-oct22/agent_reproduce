from __future__ import annotations

import sys
import json
import importlib
from pathlib import Path
from typing import Any, Optional

NEWTONBENCH_ROOT = str(Path(__file__).resolve().parent.parent / "NewtonBench")
if NEWTONBENCH_ROOT not in sys.path:
    sys.path.insert(0, NEWTONBENCH_ROOT)


class NewtonBenchEnv:

    def __init__(
        self,
        module_name: str,
        difficulty: str = "easy",
        system: str = "vanilla_equation",
        law_version: str = "v0",
        noise_level: float = 0.0,
        max_turns: int = 10,
        is_code_assisted: bool = False,
    ):
        self.module_name = module_name
        self.difficulty = difficulty
        self.system = system
        self.law_version = law_version
        self.noise_level = noise_level
        self.max_turns = max_turns
        self.is_code_assisted = is_code_assisted

        self._module = importlib.import_module(f"modules.{module_name}")
        self._turn = 0
        self._done = False
        self._submitted_law: Optional[str] = None

    # ------------------------------------------------------------------
    # Prompt helpers
    # ------------------------------------------------------------------

    def get_task_prompt(self) -> str:
        return self._module.get_task_prompt(
            self.system,
            is_code_assisted=self.is_code_assisted,
            noise_level=self.noise_level,
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def run_experiment(self, params: dict | list[dict]) -> str:
        if self._done:
            return "<experiment_output>\nEnvironment is done.\n</experiment_output>"
        if isinstance(params, dict):
            params = [params]

        self._turn += 1
        results = []
        for p in params:
            r = self._module.run_experiment_for_module(
                **p,
                noise_level=self.noise_level,
                difficulty=self.difficulty,
                system=self.system,
                law_version=self.law_version,
            )
            if self.system == "vanilla_equation":
                r = "{:.15e}".format(r)
            results.append(r)

        if self._turn >= self.max_turns:
            self._done = True

        return f"<experiment_output>\n{json.dumps(results)}\n</experiment_output>"

    def execute_python(self, code: str) -> str:
        if self._done:
            return "<python_output>\nEnvironment is done.\n</python_output>"

        self._turn += 1
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                exec(code, {})  # noqa: S102
            stdout = buf.getvalue().strip()
            out = stdout if stdout else "(no output)"
        except Exception as exc:
            out = f"Error: {exc}"

        if self._turn >= self.max_turns:
            self._done = True

        return f"<python_output>\n{out}\n</python_output>"

    def submit_law(self, law_str: str, judge_model: str = "nemotron-ultra") -> dict:
        self._submitted_law = law_str
        self._done = True
        return self._module.evaluate_law(
            llm_function_str=law_str,
            param_description=self._module.PARAM_DESCRIPTION,
            difficulty=self.difficulty,
            law_version=self.law_version,
            judge_model_name=judge_model,
        )

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def done(self) -> bool:
        return self._done

    @property
    def turn(self) -> int:
        return self._turn
