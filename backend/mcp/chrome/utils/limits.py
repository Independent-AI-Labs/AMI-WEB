"""Response limiting and chunk calculation helpers for MCP tools."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from browser.backend.utils.config import Config

DEFAULT_GLOBAL_MAX_BYTES = 256_000
DEFAULT_TOOL_LIMIT_BYTES = 64_000
DEFAULT_CHUNK_SIZE_BYTES = 16_000
DEFAULT_MAX_CHUNK_BYTES = 128_000


@dataclass(frozen=True)
class LimitedText:
    """Container describing capped text payloads."""

    text: str
    truncated: bool
    returned_bytes: int
    total_bytes: int


@dataclass(frozen=True)
class ChunkResult:
    """Container describing a computed chunk."""

    text: str
    chunk_start: int
    chunk_end: int
    next_offset: int | None
    remaining_bytes: int
    returned_bytes: int
    total_bytes: int
    snapshot_checksum: str


class ChunkComputationError(Exception):
    """Raised when chunk computation fails due to invalid input."""


def enforce_text_limit(config: Config, tool_key: str, payload: str) -> LimitedText:
    """Return a capped payload for the supplied tool."""

    limit = _resolve_tool_limit(config, tool_key)
    encoded = payload.encode("utf-8")
    total_bytes = len(encoded)

    if total_bytes <= limit:
        return LimitedText(
            text=payload,
            truncated=False,
            returned_bytes=total_bytes,
            total_bytes=total_bytes,
        )

    truncated_bytes = encoded[:limit]
    truncated_text = truncated_bytes.decode("utf-8", errors="ignore")
    return LimitedText(
        text=truncated_text,
        truncated=True,
        returned_bytes=len(truncated_bytes),
        total_bytes=total_bytes,
    )


def compute_chunk(
    config: Config,
    tool_key: str,
    payload: str,
    *,
    offset: int,
    length: int | None,
    snapshot_checksum: str | None,
) -> ChunkResult:
    """Return a deterministic chunk for the supplied payload."""

    encoded = payload.encode("utf-8")
    total_bytes = len(encoded)
    checksum = hashlib.sha256(encoded).hexdigest()

    if snapshot_checksum is not None and snapshot_checksum != checksum:
        raise ChunkComputationError(
            "snapshot checksum mismatch; fetch a fresh snapshot"
        )

    max_allowed = _resolve_global_max(config)
    chunk_length = _resolve_chunk_length(config, tool_key, requested=length)
    chunk_length = min(chunk_length, max_allowed)

    if offset < 0:
        raise ChunkComputationError("offset must be >= 0")
    if offset > total_bytes:
        raise ChunkComputationError("offset exceeds payload length")

    end = min(offset + chunk_length, total_bytes)
    if offset == total_bytes:
        return ChunkResult(
            text="",
            chunk_start=offset,
            chunk_end=offset,
            next_offset=None,
            remaining_bytes=0,
            returned_bytes=0,
            total_bytes=total_bytes,
            snapshot_checksum=checksum,
        )

    if end <= offset:
        raise ChunkComputationError(
            "computed chunk has no length; increase requested length"
        )

    chunk_bytes = encoded[offset:end]
    chunk_text = chunk_bytes.decode("utf-8", errors="ignore")
    returned_bytes = len(chunk_bytes)
    remaining = total_bytes - end
    next_offset = end if end < total_bytes else None

    return ChunkResult(
        text=chunk_text,
        chunk_start=offset,
        chunk_end=end,
        next_offset=next_offset,
        remaining_bytes=remaining,
        returned_bytes=returned_bytes,
        total_bytes=total_bytes,
        snapshot_checksum=checksum,
    )


def _resolve_tool_limit(config: Config, tool_key: str) -> int:
    requested = config.get(f"backend.mcp.tool_limits.{tool_key}.response_bytes")
    if requested is None:
        requested = config.get(
            "backend.mcp.tool_limits.defaults.response_bytes", DEFAULT_TOOL_LIMIT_BYTES
        )

    limit = _coerce_positive_int(requested, DEFAULT_TOOL_LIMIT_BYTES)
    global_max = _resolve_global_max(config)
    return min(limit, global_max)


def _resolve_chunk_length(
    config: Config, tool_key: str, *, requested: int | None
) -> int:
    default_size = _coerce_positive_int(
        config.get(
            "backend.mcp.tool_limits.chunks.default_chunk_size_bytes",
            DEFAULT_CHUNK_SIZE_BYTES,
        ),
        DEFAULT_CHUNK_SIZE_BYTES,
    )
    max_chunk = _coerce_positive_int(
        config.get(
            "backend.mcp.tool_limits.chunks.max_chunk_bytes", DEFAULT_MAX_CHUNK_BYTES
        ),
        DEFAULT_MAX_CHUNK_BYTES,
    )
    chunk_length = default_size

    tool_specific = config.get(f"backend.mcp.tool_limits.{tool_key}.chunk_bytes")
    if tool_specific is not None:
        chunk_length = _coerce_positive_int(tool_specific, chunk_length)

    if requested is not None:
        chunk_length = _coerce_positive_int(requested, chunk_length)

    return min(chunk_length, max_chunk)


def _resolve_global_max(config: Config) -> int:
    return _coerce_positive_int(
        config.get(
            "backend.mcp.tool_limits.global_max_bytes", DEFAULT_GLOBAL_MAX_BYTES
        ),
        DEFAULT_GLOBAL_MAX_BYTES,
    )


def _coerce_positive_int(value: Any, default_value: int) -> int:
    try:
        candidate = int(value)
    except (TypeError, ValueError):
        return default_value
    return candidate if candidate > 0 else default_value
