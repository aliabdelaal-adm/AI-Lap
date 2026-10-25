from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    api_tokens: dict[str, str]
    max_image_bytes: int = 20 * 1024 * 1024
    max_audio_bytes: int = 100 * 1024 * 1024
    max_scene_chars: int = 2_000
    max_active_jobs: int = 2

    @classmethod
    def from_env(cls) -> Settings:
        raw_tokens = os.environ.get("STUDIO_API_TOKENS", "{}")
        try:
            tokens = json.loads(raw_tokens)
        except json.JSONDecodeError as exc:
            raise ValueError("STUDIO_API_TOKENS must be a JSON object") from exc
        if not isinstance(tokens, dict):
            raise ValueError("STUDIO_API_TOKENS must be a JSON object")
        for user_id, token in tokens.items():
            if (
                not isinstance(user_id, str)
                or not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", user_id)
                or not isinstance(token, str)
                or not token.isascii()
                or len(token) < 32
            ):
                raise ValueError(
                    "Each API token needs a valid user ID and at least 32 characters"
                )
        if len(set(tokens.values())) != len(tokens):
            raise ValueError("Each user must have a unique API token")
        return cls(
            data_dir=Path(os.environ.get("STUDIO_DATA_DIR", "./data")).resolve(),
            api_tokens=tokens,
        )
