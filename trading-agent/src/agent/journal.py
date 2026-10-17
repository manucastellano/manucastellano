"""Append-only JSONL journal, one file per UTC day. The nightly review reads only this."""

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterator


def _default(o: Any) -> Any:
    if is_dataclass(o):
        return asdict(o)
    if isinstance(o, Enum):
        return o.value
    if isinstance(o, Path):
        return str(o)
    if hasattr(o, "model_dump"):
        return o.model_dump()
    raise TypeError(f"not serializable: {type(o)}")


def day_of(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


class Journal:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def write(self, ts: float, kind: str, **data: Any) -> None:
        line = json.dumps({"ts": ts, "kind": kind, **data}, default=_default, separators=(",", ":"))
        with open(self.root / f"{day_of(ts)}.jsonl", "a") as f:
            f.write(line + "\n")

    def read_day(self, day: str) -> Iterator[dict]:
        path = self.root / f"{day}.jsonl"
        if not path.exists():
            return
        with open(path) as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)
