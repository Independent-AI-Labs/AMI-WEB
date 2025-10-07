"""Web search tools for the Chrome MCP server."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import quote_plus

from aiohttp import ClientError, ClientSession, ClientTimeout
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag
from loguru import logger

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.response import BrowserResponse

_DEFAULT_PRIMARY_URL = "http://127.0.0.1:8888/search?q={query}&format=json"
_HTTP_OK = 200

type SearchResult = dict[str, str | int | None]


class _NoResultsError(RuntimeError):
    """Raised when a search provider returns no usable results."""


@dataclass(slots=True)
class _SearchProvider:
    """Runtime configuration for a single search provider."""

    name: str
    url_template: str


def _format_search_url(template: str, query: str) -> str:
    """Safely interpolate the user query into the provider template."""
    safe_query = quote_plus(query)
    return template.replace("{query}", safe_query)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None

    stripped = value.strip()
    if not stripped:
        return None

    if "<" in stripped and ">" in stripped:
        # Best-effort strip of markup returned by providers like SearXNG
        soup = BeautifulSoup(stripped, "html.parser")
        text = soup.get_text(" ", strip=True)
        return text or None

    return stripped


def _parse_json_results(payload: Any, max_results: int) -> list[SearchResult]:
    results: list[SearchResult] = []
    if not isinstance(payload, dict):
        return results

    items = payload.get("results")
    if not isinstance(items, Iterable):
        return results

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue

        url = item.get("url")
        title = item.get("title") or item.get("name")
        snippet = item.get("content") or item.get("snippet") or item.get("summary")

        cleaned_title = _clean_text(title)
        cleaned_snippet = _clean_text(snippet)

        if not url or not cleaned_title:
            continue

        results.append(
            {
                "rank": index + 1,
                "title": cleaned_title,
                "url": url,
                "snippet": cleaned_snippet,
            }
        )

        if len(results) >= max_results:
            break

    return results


def _find_snippet_text(container: Tag) -> str | None:
    snippet_candidate = container.find("p") or container.find("span", class_="snippet")
    if not snippet_candidate:
        return None
    return _clean_text(snippet_candidate.get_text(" ", strip=True))


def _collect_structured_html_results(
    soup: BeautifulSoup,
    max_results: int,
    start_rank: int,
    seen_urls: set[str],
) -> tuple[list[SearchResult], int]:
    results: list[SearchResult] = []
    rank = start_rank
    for container_candidate in cast(
        Iterable[Any],
        soup.select(
            "article, div.result, div.result-default, li.result, div.web-result"
        ),
    ):
        if not isinstance(container_candidate, Tag):
            continue
        container = container_candidate

        anchor_candidate = container.find("a", href=True)
        anchor = anchor_candidate if isinstance(anchor_candidate, Tag) else None
        if not isinstance(anchor, Tag):
            continue

        title = _clean_text(anchor.get_text(" ", strip=True))
        if not title:
            continue

        link = anchor.get("href")
        if not isinstance(link, str) or link in seen_urls:
            continue

        snippet_text = _find_snippet_text(container)
        results.append(
            {"rank": rank, "title": title, "url": link, "snippet": snippet_text}
        )
        seen_urls.add(link)
        rank += 1

        if len(results) >= max_results:
            break

    return results, rank


def _collect_anchor_results(
    soup: BeautifulSoup,
    remaining: int,
    start_rank: int,
    seen_urls: set[str],
) -> list[SearchResult]:
    results: list[SearchResult] = []
    rank = start_rank
    for anchor_candidate in cast(Iterable[Any], soup.find_all("a", href=True)):
        if isinstance(anchor_candidate, NavigableString):
            continue
        anchor = cast(Tag, anchor_candidate)

        title = _clean_text(anchor.get_text(" ", strip=True))
        if not title:
            continue

        link = anchor.get("href")
        if not isinstance(link, str) or link in seen_urls:
            continue

        results.append({"rank": rank, "title": title, "url": link, "snippet": None})
        seen_urls.add(link)
        rank += 1

        if len(results) >= remaining:
            break

    return results


def _parse_html_results(payload: str, max_results: int) -> list[SearchResult]:
    soup = BeautifulSoup(payload, "html.parser")
    seen_urls: set[str] = set()

    structured_results, next_rank = _collect_structured_html_results(
        soup, max_results, 1, seen_urls
    )
    if len(structured_results) >= max_results:
        return structured_results[:max_results]

    anchors_needed = max_results - len(structured_results)
    anchor_results = _collect_anchor_results(soup, anchors_needed, next_rank, seen_urls)

    return (structured_results + anchor_results)[:max_results]


async def _fetch_payload(
    session: ClientSession, url: str, headers: dict[str, str]
) -> tuple[str, Any]:
    async with session.get(url, headers=headers) as response:
        if response.status != _HTTP_OK:
            raise RuntimeError(f"HTTP {response.status} for {url}")

        content_type = response.headers.get("Content-Type", "")

        if "json" in content_type:
            try:
                return "json", await response.json()
            except (
                ClientError,
                json.JSONDecodeError,
            ) as exc:  # pragma: no cover - defensive
                logger.warning(f"Failed to decode JSON response from {url}: {exc}")

        text = await response.text()

        if not text:
            raise RuntimeError("Empty response body")

        try:
            parsed = json.loads(text)
            return "json", parsed
        except json.JSONDecodeError:
            return "html", text


def _dedupe_results(results: list[SearchResult]) -> list[SearchResult]:
    seen: set[tuple[str, str]] = set()
    deduped: list[SearchResult] = []
    for item in results:
        url = item.get("url")
        title = item.get("title")
        if not isinstance(url, str):
            continue
        key = (url, str(title) if title is not None else "")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _summarise_results(results: list[SearchResult]) -> str:
    lines: list[str] = []
    for result in results:
        rank = result.get("rank")
        title = result.get("title") or "<untitled>"
        url = result.get("url") or ""
        snippet = result.get("snippet")
        prefix = f"{rank}. " if rank is not None else ""
        lines.append(f"{prefix}{title} — {url}")
        if snippet:
            lines.append(f"    {snippet}")
    return "\n".join(lines)


def _resolve_template(
    config: Any,
    primary_override: str | None,
) -> str:
    return (
        primary_override
        or (config.get("backend.tools.web_search.primary_url") if config else None)
        or _DEFAULT_PRIMARY_URL
    )


def _resolve_timeout(config: Any, timeout_override: float | None) -> float:
    configured = (
        config.get("backend.tools.web_search.timeout_seconds", 10) if config else 10
    )
    timeout_value = timeout_override if timeout_override is not None else configured
    return configured if timeout_value <= 0 else timeout_value


def _resolve_max_results(config: Any, max_results_override: int | None) -> int:
    configured = (
        config.get("backend.tools.web_search.max_results", 10) if config else 10
    )
    max_value = max_results_override if max_results_override is not None else configured
    return configured if max_value <= 0 else max_value


def _resolve_user_agent(config: Any) -> str | None:
    return config.get("backend.tools.web_search.user_agent") if config else None


def _build_headers(user_agent: str | None) -> dict[str, str]:
    return {"User-Agent": user_agent} if user_agent else {}


def _parse_payload(
    payload_type: str, payload: Any, max_results: int
) -> list[SearchResult]:
    parser = cast(
        Callable[[Any, int], list[SearchResult]],
        _parse_json_results if payload_type == "json" else _parse_html_results,
    )
    return _dedupe_results(parser(payload, max_results))


def _build_success_response(
    query: str,
    provider: _SearchProvider,
    url: str,
    results: list[SearchResult],
) -> BrowserResponse:
    result_payload = {"results": results}
    result_bytes = json.dumps(result_payload, ensure_ascii=False).encode("utf-8")
    return BrowserResponse(
        success=True,
        data={"provider": provider.name, "query": query, "request_url": url},
        result=result_payload,
        text=_summarise_results(results),
        returned_bytes=len(result_bytes),
        total_bytes_estimate=len(result_bytes),
    )


async def _execute_provider(
    session: ClientSession,
    provider: _SearchProvider,
    query: str,
    max_results: int,
    headers: dict[str, str],
) -> BrowserResponse:
    url = _format_search_url(provider.url_template, query)
    payload_type, payload = await _fetch_payload(session, url, headers)
    parsed = _parse_payload(payload_type, payload, max_results)
    if not parsed:
        raise _NoResultsError(f"Provider {provider.name} returned no usable results")
    return _build_success_response(query, provider, url, parsed)


async def browser_web_search_tool(
    manager: ChromeManager,
    query: str,
    *,
    max_results: int | None = None,
    search_engine_url: str | None = None,
    timeout: float | None = None,
) -> BrowserResponse:
    """Run a web search using the configured engine."""
    cleaned_query = query.strip()
    if not cleaned_query:
        return BrowserResponse(success=False, error="Query must not be empty")

    config = getattr(manager, "config", None)
    primary_template = _resolve_template(config, search_engine_url)
    timeout_seconds = _resolve_timeout(config, timeout)
    effective_max = _resolve_max_results(config, max_results)
    user_agent = _resolve_user_agent(config)

    headers = _build_headers(user_agent)

    provider = _SearchProvider(name="primary", url_template=primary_template)

    error_message = "No web search providers returned results"

    async with ClientSession(timeout=ClientTimeout(total=timeout_seconds)) as session:
        try:
            return await _execute_provider(
                session, provider, cleaned_query, effective_max, headers
            )
        except _NoResultsError as exc:
            logger.warning(str(exc))
            error_message = str(exc)
        except (ClientError, TimeoutError, RuntimeError) as exc:
            logger.warning(f"Provider {provider.name} failed: {exc}")
            error_message = str(exc)
        except Exception as exc:  # pragma: no cover - hard failure path
            logger.exception(f"Unexpected error from provider {provider.name}: {exc}")
            error_message = str(exc)

    return BrowserResponse(
        success=False,
        error=f"Web search failed: {error_message}",
        data={"query": cleaned_query},
    )
