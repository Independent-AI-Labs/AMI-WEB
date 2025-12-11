"""Helpers for reading compute profile settings."""

from __future__ import annotations

import os


_COMPUTE_ENV_VARS = ("AMI_COMPUTE_PROFILE", "AMI_COMPUTE_TARGET", "COMPUTE_PROFILE")
_ALIASES: dict[str, str] = {
    "cpu": "cpu",
    "nvidia": "nvidia",
    "gpu": "nvidia",
    "cuda": "nvidia",
    "intel": "intel",
    "xpu": "intel",
    "amd": "amd",
    "rocm": "amd",
}


def get_compute_profile(default: str = "cpu") -> str:
    """Return the normalized compute profile for the current environment."""

    for key in _COMPUTE_ENV_VARS:
        value = os.environ.get(key)
        if not value:
            continue
        normalized = _ALIASES.get(value.strip().lower())
        if normalized:
            return normalized
    return default
