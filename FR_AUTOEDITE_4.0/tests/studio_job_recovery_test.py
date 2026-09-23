#!/usr/bin/env python3
"""Regressão do heartbeat, cancelamento e recuperação de tarefas do Studio."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import time
from pathlib import Path


def load_studio(app_root: Path):
    spec = importlib.util.spec_from_file_location("fr_studio_job_test", app_root / "app" / "studio.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Não foi possível carregar o Studio.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wait_until(predicate, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError("Condição de tarefa não atingida dentro do limite.")


def main() -> int:
    app_root = Path(__file__).resolve().parents[1]
    studio = load_studio(app_root)

    class ControlledState(studio.StudioState):
        def _command_for(self, project: Path, action: str) -> list[str]:
            del project, action
            return [
                sys.executable,
                "-u",
                "-c",
                (
                    "import time; "
                    "print('[FR] Preparação 1/64: processando M0001 · teste.mp4', flush=True); "
                    "time.sleep(30)"
                ),
            ]

    with tempfile.TemporaryDirectory(prefix="fr-studio-job-") as temporary:
        state = ControlledState(app_root, Path(temporary) / "Studio")
        created = state.create_project("Recuperação 63 de 64")
        project = state.project_dir(created["slug"])
        state.start_job(project, "prepare")

        def item_visible() -> bool:
            with state.lock:
                job = state.jobs.get(project.name, {})
                return bool(job.get("pid") and job.get("current_item") == "M0001")

        wait_until(item_visible)
        with state.lock:
            first_heartbeat = float(state.jobs[project.name]["heartbeat_at"])
            assert state.jobs[project.name]["progress"]["current"] == 1
            assert state.jobs[project.name]["progress"]["total"] == 64

        wait_until(
            lambda: float(state.jobs[project.name].get("heartbeat_at", 0)) > first_heartbeat,
            timeout=3.0,
        )
        state.cancel_job(project)
        wait_until(lambda: not state.jobs[project.name].get("running"), timeout=5.0)

        with state.lock:
            finished = dict(state.jobs[project.name])
        assert finished["cancel_requested"] is True
        assert finished["returncode"] != 0
        assert any("resultados concluídos foram preservados" in line for line in finished["log"])

        status_path = project / "_CONTROLE" / "STUDIO_JOB_STATUS.json"
        persisted = json.loads(status_path.read_text(encoding="utf-8"))
        assert persisted["running"] is False
        persisted.update({"running": True, "returncode": None, "finished_at": None})
        status_path.write_text(json.dumps(persisted), encoding="utf-8")

        recovered_state = ControlledState(app_root, Path(temporary) / "Studio")
        recovered = recovered_state.project_state(project)["job"]
        assert recovered["running"] is False
        assert recovered["interrupted"] is True
        assert recovered["returncode"] == 130
        assert "reutilizados" in recovered["error_message"]

    print("STUDIO JOB RECOVERY TEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
