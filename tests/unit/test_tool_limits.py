"""Unit tests for MCP tool response limiting helpers."""

from __future__ import annotations

import pytest

from browser.backend.mcp.chrome.utils.limits import (
    ChunkComputationError,
    compute_chunk,
    enforce_text_limit,
)
from browser.backend.utils.config import Config


def build_config(tool_limits: dict[str, object]) -> Config:
    """Construct a Config seeded with tool limit overrides for testing."""

    return Config({"backend": {"mcp": {"tool_limits": tool_limits}}})


def test_enforce_text_limit_truncates_when_exceeding_cap() -> None:
    config = build_config(
        {
            "global_max_bytes": 10,
            "defaults": {"response_bytes": 10},
            "browser_get_text": {"response_bytes": 8},
        },
    )

    payload = "abcdefghijk"
    limited = enforce_text_limit(config, "browser_get_text", payload)

    assert limited.truncated is True
    assert limited.returned_bytes == 8
    assert limited.total_bytes == len(payload.encode("utf-8"))
    assert limited.text == payload[:8]


def test_enforce_text_limit_honours_global_cap() -> None:
    config = build_config(
        {
            "global_max_bytes": 6,
            "defaults": {"response_bytes": 20},
            "browser_get_text": {"response_bytes": 18},
        },
    )

    payload = "abcdefghij"
    limited = enforce_text_limit(config, "browser_get_text", payload)

    assert limited.truncated is True
    assert limited.returned_bytes == 6
    assert limited.text == payload[:6]


def test_compute_chunk_produces_offsets_and_checksum() -> None:
    config = build_config(
        {
            "global_max_bytes": 64,
            "defaults": {"response_bytes": 32},
            "chunks": {"default_chunk_size_bytes": 4, "max_chunk_bytes": 16},
            "browser_get_text": {"response_bytes": 32, "chunk_bytes": 6},
        },
    )

    payload = "abcdefghij"  # 10 bytes
    first = compute_chunk(
        config,
        "browser_get_text",
        payload,
        offset=0,
        length=None,
        snapshot_checksum=None,
    )

    assert first.text == payload[:6]
    assert first.chunk_start == 0
    assert first.chunk_end == 6
    assert first.next_offset == 6
    assert first.remaining_bytes == 4
    assert first.total_bytes == len(payload)
    assert len(first.snapshot_checksum) == 64

    second = compute_chunk(
        config,
        "browser_get_text",
        payload,
        offset=first.next_offset or 0,
        length=None,
        snapshot_checksum=first.snapshot_checksum,
    )

    assert second.text == payload[6:10]
    assert second.chunk_start == 6
    assert second.chunk_end == 10
    assert second.next_offset is None
    assert second.remaining_bytes == 0


def test_compute_chunk_rejects_invalid_offset() -> None:
    config = build_config(
        {
            "global_max_bytes": 32,
            "defaults": {"response_bytes": 32},
            "chunks": {"default_chunk_size_bytes": 4, "max_chunk_bytes": 16},
        },
    )

    with pytest.raises(ChunkComputationError):
        compute_chunk(
            config,
            "browser_get_text",
            "abc",
            offset=5,
            length=None,
            snapshot_checksum=None,
        )


def test_compute_chunk_detects_checksum_mismatch() -> None:
    config = build_config(
        {
            "global_max_bytes": 32,
            "defaults": {"response_bytes": 32},
            "chunks": {"default_chunk_size_bytes": 4, "max_chunk_bytes": 16},
        },
    )

    payload = "abcdefgh"
    first = compute_chunk(
        config, "browser_get_text", payload, offset=0, length=4, snapshot_checksum=None
    )

    with pytest.raises(ChunkComputationError):
        compute_chunk(
            config,
            "browser_get_text",
            payload,
            offset=4,
            length=4,
            snapshot_checksum="deadbeef",
        )

    # offset beyond total but checksum correct should still fail with offset error
    with pytest.raises(ChunkComputationError):
        compute_chunk(
            config,
            "browser_get_text",
            payload,
            offset=20,
            length=4,
            snapshot_checksum=first.snapshot_checksum,
        )


def test_compute_chunk_handles_offset_at_end() -> None:
    config = build_config(
        {
            "global_max_bytes": 32,
            "defaults": {"response_bytes": 32},
            "chunks": {"default_chunk_size_bytes": 4, "max_chunk_bytes": 16},
        },
    )

    payload = "abcd"
    first = compute_chunk(
        config, "browser_get_text", payload, offset=0, length=4, snapshot_checksum=None
    )

    terminal = compute_chunk(
        config,
        "browser_get_text",
        payload,
        offset=first.total_bytes,
        length=4,
        snapshot_checksum=first.snapshot_checksum,
    )

    assert terminal.text == ""
    assert terminal.chunk_start == first.total_bytes
    assert terminal.chunk_end == first.total_bytes
    assert terminal.next_offset is None
    assert terminal.remaining_bytes == 0
    assert terminal.returned_bytes == 0
