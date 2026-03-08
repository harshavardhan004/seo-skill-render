#!/usr/bin/env python3
"""
Shared GitHub API helpers for repository SEO scripts.
"""

import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError


API_BASE = "https://api.github.com"


class GitHubAPIError(RuntimeError):
    """Raised when GitHub API requests fail."""

    def __init__(self, message: str, status: int = None, details: dict = None):
        super().__init__(message)
        self.status = status
        self.details = details or {}


def get_token(cli_token: str = None) -> str:
    """Resolve token from CLI override or standard environment variables."""
    if cli_token:
        return cli_token.strip()
    for env_key in ("GITHUB_TOKEN", "GH_TOKEN"):
        value = os.environ.get(env_key, "").strip()
        if value:
            return value
    return ""


def normalize_repo_slug(value: str) -> str:
    """Normalize a repo identifier to owner/repo format."""
    if not value:
        return ""

    text = value.strip()
    text = re.sub(r"\.git$", "", text)

    if text.startswith("git@github.com:"):
        text = text.split(":", 1)[1]
    elif text.startswith(("https://github.com/", "http://github.com/")):
        parsed = urllib.parse.urlparse(text)
        text = parsed.path.strip("/")

    parts = [p for p in text.split("/") if p]
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return ""


def infer_repo_from_git(cwd: str = None) -> str:
    """Infer owner/repo from local git origin URL."""
    try:
        output = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            cwd=cwd,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return ""
    return normalize_repo_slug(output)


def resolve_repo(repo: str = None, cwd: str = None) -> str:
    """Resolve repository slug from explicit value or local git origin."""
    slug = normalize_repo_slug(repo or "")
    if slug:
        return slug
    inferred = infer_repo_from_git(cwd=cwd)
    if inferred:
        return inferred
    raise GitHubAPIError(
        "Could not resolve repository slug. Use --repo owner/repo or run inside a git repo with origin configured."
    )


def parse_repo_slug(repo: str) -> tuple:
    """Return (owner, repo_name)."""
    slug = normalize_repo_slug(repo)
    parts = slug.split("/")
    if len(parts) != 2:
        raise GitHubAPIError(f"Invalid repository slug: {repo}")
    return parts[0], parts[1]


def _headers(token: str = "", accept: str = "", content_type: str = "application/json") -> dict:
    headers = {
        "User-Agent": "SEOSkill-GitHubAPI/1.0",
        "Accept": accept or "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if content_type:
        headers["Content-Type"] = content_type
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _build_url(path: str, params: dict = None) -> str:
    url = path if path.startswith("http") else f"{API_BASE}{path}"
    if params:
        query = urllib.parse.urlencode(params, doseq=True)
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{query}"
    return url


def rest_json(
    path: str,
    token: str = "",
    method: str = "GET",
    params: dict = None,
    body: dict = None,
    accept: str = "",
    timeout: int = 20,
    retries: int = 2,
    max_sleep_seconds: int = 30,
) -> dict:
    """
    Execute a REST request and return parsed JSON plus metadata.
    Raises GitHubAPIError on terminal failures.
    """
    url = _build_url(path, params=params)
    payload = None
    if body is not None:
        payload = json.dumps(body).encode("utf-8")

    attempt = 0
    while attempt <= retries:
        request = urllib.request.Request(
            url,
            data=payload,
            headers=_headers(token=token, accept=accept),
            method=method.upper(),
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace").strip()
                data = json.loads(raw) if raw else {}
                return {
                    "data": data,
                    "status": getattr(resp, "status", 200),
                    "rate_limit": {
                        "limit": resp.headers.get("X-RateLimit-Limit"),
                        "remaining": resp.headers.get("X-RateLimit-Remaining"),
                        "reset": resp.headers.get("X-RateLimit-Reset"),
                    },
                }
        except HTTPError as exc:
            response_text = exc.read().decode("utf-8", errors="replace").strip()
            try:
                payload_json = json.loads(response_text) if response_text else {}
            except Exception:
                payload_json = {"raw": response_text}

            status = exc.code
            remaining = exc.headers.get("X-RateLimit-Remaining")
            reset = exc.headers.get("X-RateLimit-Reset")

            can_retry = attempt < retries
            if can_retry and status in (429, 500, 502, 503, 504):
                sleep_seconds = min(max_sleep_seconds, 2 ** attempt)
                time.sleep(max(1, sleep_seconds))
                attempt += 1
                continue

            if can_retry and status == 403 and remaining == "0" and reset:
                try:
                    reset_ts = int(reset)
                    wait_for = max(1, min(max_sleep_seconds, reset_ts - int(time.time()) + 1))
                except Exception:
                    wait_for = 2 ** attempt
                time.sleep(wait_for)
                attempt += 1
                continue

            message = payload_json.get("message", f"GitHub API error: HTTP {status}")
            raise GitHubAPIError(message=message, status=status, details=payload_json)
        except URLError as exc:
            if attempt < retries:
                time.sleep(max(1, 2 ** attempt))
                attempt += 1
                continue
            raise GitHubAPIError(f"Network error while calling GitHub API: {exc}") from exc

    raise GitHubAPIError("GitHub API request retries exhausted.")


def graphql_json(query: str, variables: dict = None, token: str = "", timeout: int = 20, retries: int = 2) -> dict:
    """Execute a GraphQL query and return data."""
    result = rest_json(
        "/graphql",
        token=token,
        method="POST",
        body={"query": query, "variables": variables or {}},
        timeout=timeout,
        retries=retries,
    )
    payload = result.get("data", {})
    if payload.get("errors"):
        raise GitHubAPIError("GraphQL query failed", details={"errors": payload.get("errors")})
    return payload.get("data", {})
