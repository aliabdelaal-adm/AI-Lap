from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class EngineUnavailable(RuntimeError):
    pass


class VideoEngine(Protocol):
    async def generate(
        self,
        config: dict[str, Any],
        inputs: dict[str, Path],
        output_dir: Path,
    ) -> Path: ...


class UnconfiguredEngine:
    async def generate(
        self,
        config: dict[str, Any],
        inputs: dict[str, Path],
        output_dir: Path,
    ) -> Path:
        raise EngineUnavailable(
            "No video-generation adapter is configured; inference was not run."
        )
