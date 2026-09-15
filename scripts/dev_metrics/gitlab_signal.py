# /// script
# requires-python = ">=3.11"
# dependencies = ["requests>=2.32,<3", "python-dotenv>=1,<2"]
# ///
"""GitLab v4 commit/issue counts and metadata-only MR participation signals.

GITLAB_TOKEN (PRIVATE-TOKEN) and GITLAB_BASE_URL are preferred; legacy
LGEP_ID/LGEP_PASSWORD Basic auth is optional. Process environment wins over
the worktree-root .env, regardless of cwd. No response bodies are saved/logged.
Approvals are current snapshots, not historical review events. Nonsystem
comments and approvals can come from bots: these are not human-only signals.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit, urlunsplit

import requests
from dotenv import dotenv_values

DEFAULT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
DEFAULT_BASE_URL = "https://mod.lge.com/hub"


class CollectionError(Exception):
    """Sanitized error: never include credentials, URLs, or response content."""


def load_env(env_path: Path | str = DEFAULT_ENV_FILE) -> dict:
    # Disable interpolation so values cannot unexpectedly resolve via other keys.
    return {**dotenv_values(env_path, interpolate=False), **os.environ}


def normalize_base_url(value: str) -> str:
    try:
        parts = urlsplit(value)
        valid = (parts.scheme in ("http", "https") and parts.hostname and
                 not parts.username and not parts.password and not parts.query and
                 not parts.fragment)
        _ = parts.port
    except ValueError:
        raise CollectionError("Invalid GitLab base URL configuration.") from None
    if not valid:
        raise CollectionError("Invalid GitLab base URL configuration.")
    path = parts.path.rstrip("/")
    while path.endswith("/api/v4"):
        path = path[:-7].rstrip("/")
    return urlunsplit((parts.scheme, parts.netloc, path + "/api/v4", "", ""))


class GitLabClient:
    def __init__(self, config: dict):
        self.url = normalize_base_url(config.get("GITLAB_BASE_URL") or DEFAULT_BASE_URL)
        token = config.get("GITLAB_TOKEN")
        uid, password = config.get("LGEP_ID"), config.get("LGEP_PASSWORD")
        if not token and not (uid and password):
            raise CollectionError("GITLAB_TOKEN or legacy LGEP_ID/LGEP_PASSWORD required.")
        self.session = requests.Session()
        # Avoid implicit netrc credentials and environment CA/proxy overrides.
        self.session.trust_env = False
        if token:
            self.session.headers["PRIVATE-TOKEN"] = token
        else:
            self.session.auth = (uid, password)

    def get(self, endpoint: str, params: dict | None = None, optional=False):
        try:
            response = self.session.get(
                self.url + "/" + endpoint, params=params, timeout=30,
                allow_redirects=False, verify=True,
            )
        except requests.RequestException:
            raise CollectionError("GitLab connection/TLS/timeout failure.") from None
        if optional and response.status_code in (404, 405):
            return None, response
        if response.status_code != 200:
            raise CollectionError(f"GitLab HTTP {response.status_code}: collection failed.")
        try:
            return response.json(), response
        except ValueError:
            raise CollectionError("Invalid GitLab JSON response.") from None

    def pages(self, endpoint: str, params: dict | None = None):
        page = 1
        seen_ids = set()
        while True:
            raw, response = self.get(endpoint, {**(params or {}), "per_page": 100, "page": page})
            if not isinstance(raw, list):
                raise CollectionError("Invalid GitLab list response.")
            for item in raw:
                if not isinstance(item, dict) or type(item.get("id")) not in (str, int):
                    raise CollectionError("GitLab list entry has no valid ID.")
                if item["id"] in seen_ids:
                    raise CollectionError("GitLab pagination repeated an entry.")
                seen_ids.add(item["id"])
            next_page = response.headers.get("X-Next-Page")
            if next_page is None:
                # Read only the page number; never follow an untrusted Link URL.
                link = response.links.get("next", {}).get("url")
                if link:
                    try:
                        target = urlsplit(link)
                        expected = urlsplit(self.url + "/" + endpoint)
                        if (target.scheme, target.netloc, target.path) != (
                                expected.scheme, expected.netloc, expected.path):
                            raise ValueError
                        values = parse_qs(target.query).get("page", [])
                        if len(values) != 1:
                            raise ValueError
                        next_page = values[0]
                    except ValueError:
                        raise CollectionError("Invalid GitLab pagination link.") from None
            if next_page:
                if not str(next_page).isdigit() or int(next_page) <= page or not raw:
                    raise CollectionError("GitLab pagination did not advance.")
                next_page = int(next_page)
            yield raw, bool(next_page)
            if not next_page:
                return
            page = next_page


def fields(raw: dict, allowed: tuple[str, ...]) -> dict:
    """Only allowlisted scalar fields; never copy arbitrary nested dictionaries."""
    if not isinstance(raw, dict):
        raise CollectionError("Invalid GitLab metadata object.")
    return {key: raw[key] for key in allowed if key in raw and
            (raw[key] is None or type(raw[key]) in (str, int, bool, float))}


def account(raw: dict | None) -> dict:
    return fields(raw if raw is not None else {}, ("id", "username", "email", "bot"))


def person_key(person: dict) -> str | None:
    value = person.get("username") or person.get("email")
    return value if isinstance(value, str) and value else None


def position_metadata(raw: dict) -> dict:
    result = fields(raw, ("base_sha", "start_sha", "head_sha", "position_type", "old_path",
                          "new_path", "old_line", "new_line", "width", "height", "x", "y"))
    if raw.get("line_range") is not None:
        line_range = raw["line_range"]
        if not isinstance(line_range, dict):
            raise CollectionError("Invalid GitLab line range.")
        result["line_range"] = {
            side: fields(line_range[side], ("line_code", "type", "old_line", "new_line"))
            for side in ("start", "end") if side in line_range
        }
    return result


def note_metadata(raw: dict) -> dict:
    result = fields(raw, ("id", "type", "created_at", "updated_at", "system", "resolvable",
                          "resolved", "resolved_at", "confidential", "internal", "noteable_id",
                          "noteable_iid", "noteable_type", "commit_id"))
    if type(result.get("id")) not in (str, int) or type(result.get("system")) is not bool:
        raise CollectionError("GitLab note missing ID/system flag.")
    result["author"] = account(raw.get("author"))
    result["resolved_by"] = account(raw.get("resolved_by"))
    if raw.get("position") is not None:
        result["position"] = position_metadata(raw["position"])
    return result


def request_metadata(raw: dict, project: str) -> dict:
    result = fields(raw, ("id", "iid", "project_id", "state", "created_at", "updated_at",
                          "merged_at", "closed_at", "draft", "work_in_progress", "sha",
                          "merge_commit_sha", "squash_commit_sha", "user_notes_count"))
    if type(result.get("iid")) is not int or result.get("state") not in (
            "opened", "closed", "merged", "locked"):
        raise CollectionError("GitLab MR missing valid iid/state.")
    reviewers = raw.get("reviewers", [])
    if not isinstance(reviewers, list):
        raise CollectionError("Invalid GitLab requested reviewers.")
    result.update(project=project, author=account(raw.get("author")),
                  merged_by=account(raw.get("merged_by") or raw.get("merge_user")),
                  requested_reviewers=[account(person) for person in reviewers])
    return result


def fetch_discussions(client: GitLabClient, endpoint: str) -> list[dict]:
    result = []
    seen_notes = set()
    for entries, _ in client.pages(endpoint + "/discussions"):
        for entry in entries:
            discussion = fields(entry, ("id", "individual_note"))
            if not isinstance(entry.get("notes"), list):
                raise CollectionError("Invalid GitLab discussion notes.")
            discussion["notes"] = []
            for raw in entry["notes"]:
                note = note_metadata(raw)
                if note["id"] not in seen_notes:
                    seen_notes.add(note["id"])
                    discussion["notes"].append(note)
            result.append(discussion)
    return result


def fetch_approvals(client: GitLabClient, endpoint: str) -> dict | None:
    raw, response = client.get(endpoint + "/approvals", optional=True)
    if raw is None and response.status_code in (404, 405):
        return None
    result = fields(raw, ("approved", "approvals_required", "approvals_left"))
    if not isinstance(raw.get("approved_by"), list):
        raise CollectionError("Invalid GitLab approval snapshot.")
    result["approved_by"] = []
    for entry in raw["approved_by"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("user"), dict):
            raise CollectionError("Invalid GitLab approving account.")
        result["approved_by"].append(account(entry["user"]))
    return result


def in_window(value: str | None, cutoff: dt.datetime, now: dt.datetime) -> bool:
    if not value:
        return False
    try:
        timestamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=dt.timezone.utc)
        return cutoff <= timestamp <= now
    except (ValueError, AttributeError, TypeError):
        raise CollectionError("Invalid GitLab event timestamp.") from None


def aggregate(records: list[dict], since_days: int, now: dt.datetime) -> dict:
    cutoff = now - dt.timedelta(days=since_days)
    counters = {key: Counter() for key in ("request_author_total", "reviewer_total", "comment_total",
                                           "review_total", "merged_author_total", "merger_total")}
    for record in records:
        owner = person_key(record["author"])
        if owner:
            counters["request_author_total"][owner] += 1
        if record["state"] == "merged":
            if owner:
                counters["merged_author_total"][owner] += 1
            merger = person_key(record["merged_by"])
            if merger and in_window(record.get("merged_at"), cutoff, now):
                counters["merger_total"][merger] += 1
        participants = set()
        for discussion in record["discussions"]:
            for note in discussion["notes"]:
                if note["system"] or not in_window(note.get("created_at"), cutoff, now):
                    continue
                actor = person_key(note["author"])
                if actor:
                    counters["comment_total"][actor] += 1
                    participants.add(actor)
        approved = {person_key(actor) for actor in (record["approvals"] or {}).get("approved_by", [])}
        for actor in approved - {None}:
            counters["review_total"][actor] += 1
            participants.add(actor)
        for actor in participants - {owner}:
            counters["reviewer_total"][actor] += 1
    return {key: dict(value) for key, value in counters.items()}


def collect_signal(projects: list[str], since_days: int, limit_per_project: int = 0,
                   env_file: Path | str = DEFAULT_ENV_FILE, skip_commits: bool = False) -> dict:
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=since_days)
    since_iso = cutoff.isoformat()
    client = GitLabClient(load_env(env_file))
    counters = {key: Counter() for key in ("commits", "mrs", "issues")}
    records, truncated, unavailable = [], [], []
    try:
        for project in dict.fromkeys(projects):
            prefix = "projects/" + quote(project, safe="")
            if skip_commits:
                unavailable.append({"project": project, "feature": "commits",
                                    "reason": "not_collected (--skip-commits)"})
            else:
                for entries, _ in client.pages(prefix + "/repository/commits", {
                        "since": since_iso, "until": now.isoformat(), "all": "true"}):
                    for entry in entries:
                        email = fields(entry, ("author_email",)).get("author_email")
                        if isinstance(email, str) and email:
                            counters["commits"][email] += 1
            # Legacy counters are independent of the detailed-MR selection/cap.
            for endpoint, key in (("merge_requests", "mrs"), ("issues", "issues")):
                for entries, _ in client.pages(prefix + "/" + endpoint, {
                        "created_after": since_iso, "created_before": now.isoformat(), "state": "all"}):
                    for entry in entries:
                        actor = person_key(account(entry.get("author")))
                        if actor and in_window(entry.get("created_at"), cutoff, now):
                            counters[key][actor] += 1
            selected = []
            for entries, more in client.pages(prefix + "/merge_requests", {
                    "updated_after": since_iso, "updated_before": now.isoformat(), "state": "all",
                    "order_by": "updated_at", "sort": "desc"}):
                for entry in entries:
                    metadata = request_metadata(entry, project)
                    if in_window(metadata.get("updated_at"), cutoff, now):
                        selected.append(metadata)
                if limit_per_project and len(selected) >= limit_per_project:
                    if len(selected) > limit_per_project or more:
                        truncated.append(project)
                    selected = selected[:limit_per_project]
                    break
            for item in selected:
                endpoint = prefix + "/merge_requests/" + str(item["iid"])
                raw, _ = client.get(endpoint)
                record = request_metadata(raw, project)
                if record["iid"] != item["iid"]:
                    raise CollectionError("GitLab MR detail identity mismatch.")
                record["discussions"] = fetch_discussions(client, endpoint)
                record["approvals"] = fetch_approvals(client, endpoint)
                if record["approvals"] is None:
                    unavailable.append({"project": project, "iid": record["iid"], "feature": "approvals",
                                        "reason": "unsupported_or_not_visible (HTTP 404/405)"})
                records.append(record)
    finally:
        client.session.close()
    return {
        "schema_version": 2, "collected_at": now.isoformat(), "window_days": since_days,
        "projects": list(dict.fromkeys(projects)),
        **{key: dict(value) for key, value in counters.items()},
        "commits": None if skip_commits else dict(counters["commits"]),
        **aggregate(records, since_days, now), "requests": records,
        "truncated_projects": truncated, "unavailable": unavailable,
        "note": "MR records selected by updated_at; legacy mrs/issues by created_at. "
                "MR cap applies only to records. All discussion notes retained as metadata, including system notes. "
                "comment_total uses nonsystem created_at in window; merger_total uses actual merged_by/merge_user "
                "and merged_at in window. Approvals/review_total are current approved_by snapshots, not history; "
                "unavailable approvals are null, not zero. requested_reviewers are not participation. "
                "reviewer_total counts distinct MRs per nonowner commenter/approver. "
                "Accounts are not guaranteed human. No bodies. Routing only, not individual performance ranking.",
    }


def write_json(path: Path, result: dict) -> None:
    """Replace only a complete result, leaving the previous output on failure."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".gitlab-signal-", delete=False) as output:
            temporary = Path(output.name)
            json.dump(result, output, ensure_ascii=False, indent=2)
            output.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", action="append", required=True)
    parser.add_argument("--since-days", type=int, default=180)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--skip-commits", action="store_true",
                        help="Collect MR/issue metadata without legacy commits; commits becomes null, not zero")
    parser.add_argument("--limit-per-project", type=int, default=0, help="Detailed MR cap; 0 means all")
    args = parser.parse_args()
    if args.since_days <= 0 or args.limit_per_project < 0:
        parser.error("since-days must be positive and limit-per-project nonnegative.")
    try:
        result = collect_signal(args.project, args.since_days, args.limit_per_project, args.env_file,
                    skip_commits=args.skip_commits)
        if args.json_out:
            write_json(args.json_out, result)
        print(f"# GitLab: {len(result['requests'])} MR metadata records; "
              f"{len(result['truncated_projects'])} truncated projects; "
              f"{len(result['unavailable'])} unavailable features/snapshots")
    except CollectionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except OSError:
        print("ERROR: GitLab configuration/output file operation failed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
