from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict

import yaml


@dataclass(frozen=True)
class Config:
    raw: Dict[str, Any]

    @staticmethod
    def load(path: str = "config.yaml") -> "Config":
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        return Config(raw=raw)

    def env_email_to(self) -> str:
        key = self.raw["email"]["to_env"]
        val = os.environ.get(key)
        if not val:
            raise RuntimeError(f"Missing env var {key} (set GitHub secret {key}).")
        return val


# ✅ compatibility wrapper expected by main.py
def load_config(path: str = "config.yaml") -> Config:
    return Config.load(path)
