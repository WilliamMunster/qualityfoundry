"""
store
king
2025/12/23
qualityfoundry
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    kind: str  # "run" | "smoke" | "smoke_latest"
    artifact_dir: str
    ok: bool | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None


class ArtifactStore:
    """
    root 指向 artifacts 根目录（默认 ./artifacts）
    支持三类 run_id：
    - run_<TS>         -> artifacts/run_<TS>/
    - smoke_<TS>       -> artifacts/smoke/smoke_<TS>/
    - smoke            -> artifacts/smoke/（latest summary）
    """

    def __init__(self, root: Path):
        self.root = root.resolve()

    def _is_under(self, p: Path, base: Path) -> bool:
        try:
            return p.is_relative_to(base)  # py3.9+
        except AttributeError:  # pragma: no cover
            return str(p).startswith(str(base))

    def _parse_started_at_from_run_id(self, run_id: str) -> str | None:
        # run_YYYYMMDDTHHMMSSZ / smoke_YYYYMMDDTHHMMSSZ
        if not (run_id.startswith("run_") or run_id.startswith("smoke_")):
            return None
        ts = run_id.split("_", 1)[1]
        try:
            dt = datetime.strptime(ts, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            # ISO 8601 with Z
            return dt.isoformat().replace("+00:00", "Z")
        except Exception:
            return None

    def _run_dir(self, run_id: str) -> Path:
        if run_id.startswith("run_"):
            d = (self.root / run_id).resolve()
            base = self.root
        elif run_id.startswith("smoke_"):
            d = (self.root / "smoke" / run_id).resolve()
            base = (self.root / "smoke").resolve()
        elif run_id == "smoke":
            d = (self.root / "smoke").resolve()
            base = self.root
        else:
            raise FileNotFoundError("invalid run_id")

        if not self._is_under(d, base):
            raise FileNotFoundError("invalid run_id")
        return d

    def list_runs(self, limit: int = 20, offset: int = 0) -> list[RunSummary]:
        if not self.root.exists():
            return []

        run_ids: list[str] = []

        # run_*
        for p in self.root.glob("run_*"):
            if p.is_dir():
                run_ids.append(p.name)

        # smoke_*
        smoke_root = self.root / "smoke"
        if smoke_root.exists() and smoke_root.is_dir():
            for p in smoke_root.glob("smoke_*"):
                if p.is_dir():
                    run_ids.append(p.name)

            # 可选：把 smoke 最新 summary 也作为一条“特殊 run”展示
            if (smoke_root / "summary.json").exists():
                run_ids.append("smoke")

        # 排序策略：
        # - smoke（latest）置顶
        # - 其余按目录名倒序（时间戳越大越新）
        head = [r for r in run_ids if r == "smoke"]
        tail = [r for r in run_ids if r != "smoke"]
        tail.sort(reverse=True)
        run_ids = head + tail

        sliced = run_ids[offset: offset + limit]
        return [self.get_run(rid) for rid in sliced]

    def get_run(self, run_id: str) -> RunSummary:
        d = self._run_dir(run_id)

        summary_path = d / "summary.json"
        data: dict = {}
        if summary_path.exists():
            data = json.loads(summary_path.read_text(encoding="utf-8"))

        if run_id == "smoke":
            kind = "smoke_latest"
        elif run_id.startswith("smoke_"):
            kind = "smoke"
        else:
            kind = "run"

        started_at = data.get("started_at") or self._parse_started_at_from_run_id(run_id)

        return RunSummary(
            run_id=run_id,
            kind=kind,
            artifact_dir=str(d),
            ok=data.get("ok"),
            started_at=started_at,
            finished_at=data.get("finished_at"),
            error=data.get("error") or data.get("message"),
        )

    def list_files(self, run_id: str) -> list[dict]:
        d = self._run_dir(run_id)
        files: list[dict] = []
        for p in d.rglob("*"):
            if p.is_file():
                rel = p.relative_to(d).as_posix()
                files.append({"path": rel, "size": p.stat().st_size})

        def _file_sort_key(x: dict) -> tuple[int, str]:
            p = x["path"].lower()
            if p == "step_000.png" or p.endswith("/step_000.png"):
                return 0, p
            if p == "step_001.png" or p.endswith("/step_001.png"):
                return 1, p
            return 2, p

        files.sort(key=_file_sort_key)

        return files

    def resolve_file(self, run_id: str, rel_path: str) -> Path:
        d = self._run_dir(run_id)
        p = (d / rel_path).resolve()

        if not self._is_under(p, d):
            raise FileNotFoundError("invalid path")
        if not p.exists() or not p.is_file():
            raise FileNotFoundError("file not found")
        return p
