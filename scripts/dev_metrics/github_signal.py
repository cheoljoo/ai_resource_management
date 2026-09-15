# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""GitHub PR/review/comment/actual-merger metadata, using the authenticated gh CLI.

uv run github_signal.py --repo owner/repo --since-days 180 --json-out output/github.json

PRs are selected by updated_at (limit=0 means all). Legacy prs/issues count
creation in the window; commits use GitHub's since/until commit-date filter.
Review states are the API's current representation of historical submissions:
DISMISSED does not preserve the original decision. Requested reviewers are not
participation. Comments count created_at, not edits; merges count merged_at.
Only allowlisted metadata is retained: bodies, titles and diff hunks are never
saved or printed. API responses exist transiently in captured process memory.
These signals support expertise routing, not individual performance rankings.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode


COUNTERS = (
    "commits", "prs", "issues", "request_author_total", "reviewer_total",
    "comment_total", "review_total", "merged_author_total", "merger_total",
)


class CollectionError(Exception):
    """Safe diagnostic: never include subprocess output or response content."""


def _gh_json(endpoint: str):
    try:
        result = subprocess.run(
            ["gh", "api", endpoint, "-H", "Accept: application/vnd.github+json",
             "-H", "X-GitHub-Api-Version: 2022-11-28"],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, "GH_PROMPT_DISABLED": "1"},
        )
    except FileNotFoundError:
        raise CollectionError("gh CLI is not installed.") from None
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise CollectionError("gh execution failed or timed out.") from None
    if result.returncode:
        raise CollectionError("GitHub API failed; check gh authentication, access and network.")
    try:
        return json.loads(result.stdout)
    except (ValueError, RecursionError):
        raise CollectionError("GitHub returned invalid JSON.") from None


def _items(endpoint: str, identity: str = "id"):
    """Manual pages; fail closed on overlap/repetition rather than double-count."""
    seen = set()
    page = 1
    while True:
        separator = "&" if "?" in endpoint else "?"
        rows = _gh_json(f"{endpoint}{separator}per_page=100&page={page}")
        if not isinstance(rows, list) or len(rows) > 100:
            raise CollectionError("GitHub list response has an invalid shape.")
        for row in rows:
            if not isinstance(row, dict):
                raise CollectionError("GitHub list item has an invalid shape.")
            key = row.get(identity)
            if type(key) not in (str, int) or key == "":
                raise CollectionError("GitHub list item is missing its identifier.")
            if key in seen:
                raise CollectionError("GitHub pagination repeated an item; retry collection.")
            seen.add(key)
            yield row
        if len(rows) < 100:
            return
        page += 1


def _pick(raw: dict, fields: tuple[str, ...]) -> dict:
    # Never copy nested containers, even under otherwise allowed field names.
    return {key: raw[key] for key in fields if key in raw
            and (raw[key] is None or type(raw[key]) in (str, int, bool))}


def account(raw) -> dict:
    if not isinstance(raw, dict):
        return {}
    result = _pick(raw, ("id", "login", "type"))
    if not isinstance(result.get("login"), str):
        result.pop("login", None)
    return result


def _timestamp(value) -> dt.datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise CollectionError("GitHub timestamp has an invalid format.")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError
        return parsed.astimezone(dt.timezone.utc)
    except (ValueError, OverflowError):
        raise CollectionError("GitHub timestamp has an invalid format.") from None


def in_window(value, cutoff: dt.datetime, now: dt.datetime) -> bool:
    timestamp = _timestamp(value)
    return timestamp is not None and cutoff <= timestamp <= now


def _iso(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def review_metadata(raw: dict) -> dict:
    result = _pick(raw, ("id", "state", "submitted_at", "commit_id"))
    result["author"] = account(raw.get("user"))
    return result


def comment_metadata(raw: dict) -> dict:
    result = _pick(raw, (
        "id", "created_at", "updated_at", "path", "line", "original_line",
        "start_line", "original_start_line", "side", "start_side", "position",
        "original_position", "in_reply_to_id", "pull_request_review_id",
        "commit_id", "original_commit_id", "resolved", "is_resolved", "unresolved",
        "resolved_at",
    ))
    result["author"] = account(raw.get("user"))
    if "resolved_by" in raw:
        result["resolved_by"] = account(raw["resolved_by"])
    # REST normally omits thread resolution; absent is unknown, never false.
    if isinstance(raw.get("resolution"), dict):
        resolution = raw["resolution"]
        result["resolution"] = _pick(resolution, ("resolved", "is_resolved", "resolved_at"))
        if "resolved_by" in resolution:
            result["resolution"]["resolved_by"] = account(resolution["resolved_by"])
    return result


def request_metadata(raw, repo: str, number: int) -> dict:
    if (not isinstance(raw, dict) or raw.get("number") != number
            or raw.get("state") not in ("open", "closed")
            or (raw.get("merged") is not None and type(raw["merged"]) is not bool)):
        raise CollectionError("GitHub PR detail has an invalid shape.")
    requested = raw.get("requested_reviewers", [])
    if not isinstance(requested, list):
        raise CollectionError("GitHub requested reviewer list has an invalid shape.")
    result = _pick(raw, ("id", "number", "state", "created_at", "updated_at", "closed_at", "merged_at", "draft"))
    result.update(
        repo=repo, author=account(raw.get("user")), merged=raw.get("merged"),
        merged_by=account(raw.get("merged_by")),
        requested_reviewers=[account(person) for person in requested],
    )
    result["merger_known"] = bool(result["merged_by"].get("login"))
    return result


def _add(counter: Counter, person: dict) -> None:
    login = person.get("login")
    if login:
        counter[login] += 1


def _count_request(result: dict, request: dict, cutoff: dt.datetime, now: dt.datetime) -> None:
    owner = request["author"].get("login")
    _add(result["request_author_total"], request["author"])
    if request["merged"] is True:
        _add(result["merged_author_total"], request["author"])
        if in_window(request.get("merged_at"), cutoff, now):
            _add(result["merger_total"], request["merged_by"])
    participants = set()
    for review in request["reviews"]:
        if review.get("state") == "PENDING" or not in_window(review.get("submitted_at"), cutoff, now):
            continue
        _add(result["review_total"], review["author"])
        if review["author"].get("login"):
            participants.add(review["author"]["login"])
    for comment in request["review_comments"] + request["issue_comments"]:
        if in_window(comment.get("created_at"), cutoff, now):
            _add(result["comment_total"], comment["author"])
            if comment["author"].get("login"):
                participants.add(comment["author"]["login"])
    for person in participants:
        if not owner or person.casefold() != owner.casefold():
            result["reviewer_total"][person] += 1


def collect_signal(repo: str, since_days: int = 180, limit_per_repo: int = 0,
                   now: dt.datetime | None = None) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise CollectionError("Repository must use owner/repo format.")
    if since_days <= 0 or limit_per_repo < 0:
        raise CollectionError("Window must be positive and limit must be nonnegative.")
    now = now or dt.datetime.now(dt.timezone.utc)
    try:
        cutoff = now - dt.timedelta(days=since_days)
    except OverflowError:
        raise CollectionError("Window is out of range.") from None
    result = {key: Counter() for key in COUNTERS}
    result.update(schema_version=2, collected_at=_iso(now), window_days=since_days,
                  metadata_only=True, repos=[repo], requests=[], truncated_repos=[])
    root = f"repos/{repo}"
    commit_query = urlencode({"since": _iso(cutoff), "until": _iso(now)})
    for commit in _items(f"{root}/commits?{commit_query}", "sha"):
        info = commit.get("commit")
        author = info.get("author") if isinstance(info, dict) else None
        email = author.get("email") if isinstance(author, dict) else None
        if isinstance(email, str) and email:
            result["commits"][email] += 1
    issue_query = urlencode({"state": "all", "since": _iso(cutoff)})
    for issue in _items(f"{root}/issues?{issue_query}"):
        if "pull_request" not in issue and in_window(issue.get("created_at"), cutoff, now):
            _add(result["issues"], account(issue.get("user")))

    # Continue the updated list after a detail cap to keep the legacy created-PR
    # counter complete. Only detail/review/comment requests are capped.
    for pr in _items(f"{root}/pulls?state=all&sort=updated&direction=desc", "number"):
        updated = _timestamp(pr.get("updated_at"))
        if updated is None:
            raise CollectionError("GitHub PR list is missing updated_at.")
        if updated < cutoff:
            break
        if updated > now:
            continue
        if in_window(pr.get("created_at"), cutoff, now):
            _add(result["prs"], account(pr.get("user")))
        if limit_per_repo and len(result["requests"]) >= limit_per_repo:
            result["truncated_repos"] = [repo]
            continue
        number = pr["number"]
        if type(number) is not int or number <= 0:
            raise CollectionError("GitHub PR number has an invalid format.")
        endpoint = f"{root}/pulls/{number}"
        request = request_metadata(_gh_json(endpoint), repo, number)
        request["reviews"] = [review_metadata(row) for row in _items(f"{endpoint}/reviews")]
        request["review_comments"] = [comment_metadata(row) for row in _items(f"{endpoint}/comments")]
        request["issue_comments"] = [comment_metadata(row) for row in _items(f"{root}/issues/{number}/comments")]
        result["requests"].append(request)
        _count_request(result, request, cutoff, now)
    for key in COUNTERS:
        result[key] = dict(sorted(result[key].items()))
    return result


def _write_json(path: Path, result: dict) -> None:
    """Atomic replacement after successful collection of every repository."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".github-signal-", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    except (OSError, UnicodeError, ValueError):
        raise CollectionError("Could not write metadata JSON; existing output was not replaced.") from None
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                raise CollectionError("Could not clean up temporary metadata JSON.") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", action="append", required=True)
    parser.add_argument("--since-days", type=int, default=180)
    parser.add_argument("--limit-per-repo", type=int, default=0, help="PR detail cap; 0 = all")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    now = dt.datetime.now(dt.timezone.utc)
    combined = {key: Counter() for key in COUNTERS}
    combined.update(schema_version=2, collected_at=_iso(now), window_days=args.since_days,
                    metadata_only=True, repos=list(dict.fromkeys(args.repo)), requests=[], truncated_repos=[])
    try:
        for repo in dict.fromkeys(args.repo):
            result = collect_signal(repo, args.since_days, args.limit_per_repo, now)
            for key in COUNTERS:
                combined[key].update(result[key])
            combined["requests"].extend(result["requests"])
            combined["truncated_repos"].extend(result["truncated_repos"])
        for key in COUNTERS:
            combined[key] = dict(sorted(combined[key].items()))
        if args.json_out:
            _write_json(args.json_out, combined)
    except CollectionError as error:
        print(f"GitHub collection failed: {error}", file=sys.stderr)
        return 1
    print(f"GitHub metadata: {len(combined['requests'])} PRs; schema_version=2; window_days={args.since_days}")
    if combined["truncated_repos"]:
        print("WARNING: PR detail cap reached; request/event counters are partial (see truncated_repos).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
