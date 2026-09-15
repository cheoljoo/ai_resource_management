# /// script
# requires-python = ">=3.11"
# dependencies = ["requests>=2.32,<3"]
# ///
"""Gerrit 변경·리뷰·공개 댓글·병합·submitter 메타데이터 수집.

uv run gerrit_signal.py --server na --server lamp --since-days 180
uv run gerrit_signal.py --server na --limit-per-server 0 --json-out output/gerrit.json

최근 갱신된 change를 조회한다. limit=0이면 전체 페이지를 조회한다.
2026-09-15 사용자 승인: 댓글 API 응답의 본문은 즉시 버리고 메타데이터만 저장.
라우팅 참고용이며 개인 성과 비교·평가로 전용하지 않는다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote

import requests
from requests.auth import HTTPBasicAuth

GERRIT_CREDS_DIR = os.path.expanduser("~/code/ccr")
XSSI_PREFIX = ")]}'"


class CollectionError(Exception):
    """인증정보/응답 본문을 포함하지 않는 오류."""


def _load_gerrit_conf() -> dict:
    if GERRIT_CREDS_DIR not in sys.path:
        sys.path.insert(0, GERRIT_CREDS_DIR)
    try:
        from global_variables import gerrit_conf_dict  # type: ignore
    except ImportError:
        raise CollectionError("Gerrit 자격증명 모듈을 찾을 수 없습니다.") from None
    return gerrit_conf_dict


def _decode_json(text: str):
    if text.startswith(XSSI_PREFIX):
        text = "\n".join(text.splitlines()[1:])
    return json.loads(text)


class GerritClient:
    def __init__(self, name: str, conf: dict):
        if not all(conf.get(key) for key in ("url", "usr", "pw")):
            raise CollectionError(f"[{name}] Gerrit url/usr/pw 설정이 필요합니다.")
        self.name = name
        self.url = conf["url"].rstrip("/") + "/a/changes/"
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(conf["usr"], conf["pw"])

    def get(self, endpoint: str = "", params: dict | None = None, optional: bool = False):
        try:
            response = self.session.get(
                self.url + endpoint, params=params, timeout=30, allow_redirects=False,
            )
        except requests.RequestException:
            raise CollectionError(f"[{self.name}] 연결/인증서/시간초과 오류입니다.") from None
        if optional and response.status_code in (404, 405):
            return None
        if response.status_code != 200:
            raise CollectionError(f"[{self.name}] HTTP {response.status_code}: Gerrit 조회 실패.")
        try:
            return _decode_json(response.text)
        except ValueError:
            raise CollectionError(f"[{self.name}] Gerrit JSON 응답 형식 오류입니다.") from None


def account(raw: dict | None) -> dict:
    return {key: raw[key] for key in ("_account_id", "email", "username", "name") if raw and key in raw}


def person_key(raw: dict, server: str) -> str | None:
    return (raw.get("email") or raw.get("username")
            or (f"{server}:account:{raw['_account_id']}" if "_account_id" in raw else None))


def change_metadata(raw: dict, server: str) -> dict:
    """허용 목록만 복사: message/subject/description/본문은 결과에 넣지 않는다."""
    result = {key: raw[key] for key in (
        "id", "_number", "project", "branch", "status", "created", "updated", "submitted",
        "total_comment_count", "unresolved_comment_count",
    ) if key in raw}
    if not raw.get("_number") or not raw.get("status"):
        raise CollectionError(f"[{server}] change 번호/status가 응답에 없습니다.")
    result.update(server=server, owner=account(raw.get("owner")),
                  submitter=account(raw.get("submitter")), merged=raw["status"] == "MERGED")
    result["submitter_known"] = bool(person_key(result["submitter"], server))
    result["votes"] = []
    for label, info in raw.get("labels", {}).items():
        for approval in info.get("all", []):
            if "value" in approval:
                result["votes"].append({"label": label, "value": approval["value"],
                                        "date": approval.get("date"), "reviewer": account(approval)})
    result["reviewers"] = {
        state: [account(person) for person in people]
        for state, people in raw.get("reviewers", {}).items()
    }
    result["reviewer_updates"] = [
        {"state": event.get("state"), "updated": event.get("updated"),
         "reviewer": account(event.get("reviewer")), "updated_by": account(event.get("updated_by"))}
        for event in raw.get("reviewer_updates", [])
    ]
    result["messages"] = [
        {**{key: message[key] for key in ("id", "date", "tag", "_revision_number") if key in message},
         "author": account(message.get("author")), "real_author": account(message.get("real_author"))}
        for message in raw.get("messages", [])
    ]
    return result


def fetch_recent_changes(client: GerritClient, since_days: int, limit: int) -> tuple[list[dict], bool]:
    changes = []
    seen = set()
    start = 0
    while True:
        size = min(100, limit - len(changes)) if limit else 100
        raw = client.get(params={
            "q": f"-age:{since_days}d", "n": size, "S": start,
            "o": ["DETAILED_ACCOUNTS", "DETAILED_LABELS", "MESSAGES", "REVIEWER_UPDATES"],
        })
        if not isinstance(raw, list) or any(not isinstance(change, dict) for change in raw):
            raise CollectionError(f"[{client.name}] change 목록 형식 오류입니다.")
        if not raw:
            return changes, False
        more = bool(raw[-1].get("_more_changes"))
        previous_count = len(changes)
        for change in raw:
            item = change_metadata(change, client.name)
            if item["_number"] not in seen:
                seen.add(item["_number"])
                changes.append(item)
        if more and len(changes) == previous_count:
            raise CollectionError(f"[{client.name}] change 페이지가 진행되지 않습니다.")
        if limit and len(changes) >= limit:
            return changes[:limit], more or len(changes) > limit
        if not more:
            return changes, False
        start += len(raw)


def fetch_comments(client: GerritClient, number: int, robot: bool = False) -> list[dict] | None:
    endpoint = f"{quote(str(number), safe='')}/{'robotcomments' if robot else 'comments'}"
    raw = client.get(endpoint, optional=robot)
    if raw is None and robot:
        return None
    if not isinstance(raw, dict):
        raise CollectionError(f"[{client.name}] 댓글 응답 형식 오류입니다.")
    comments = []
    seen = set()
    for path, entries in raw.items():
        if not isinstance(entries, list):
            raise CollectionError(f"[{client.name}] 댓글 목록 형식 오류입니다.")
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get("id"):
                raise CollectionError(f"[{client.name}] 댓글 ID가 응답에 없습니다.")
            if entry["id"] in seen:
                continue
            seen.add(entry["id"])
            metadata = {key: entry[key] for key in (
                "id", "updated", "patch_set", "line", "side", "range", "in_reply_to",
                "unresolved", "tag", "robot_id", "robot_run_id",
            ) if key in entry}
            metadata.update(path=path, author=account(entry.get("author")))
            comments.append(metadata)
    return comments


def in_window(value: str | None, cutoff: dt.datetime) -> bool:
    if not value:
        return False
    try:
        timestamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise CollectionError("Gerrit 이벤트 타임스탬프 형식 오류입니다.") from None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=dt.timezone.utc)
    return timestamp >= cutoff


def aggregate(changes: list[dict], since_days: int, now: dt.datetime) -> dict:
    cutoff = now - dt.timedelta(days=since_days)
    counters: dict[str, Counter] = {name: Counter() for name in (
        "person_total", "reviewer_total", "vote_total", "comment_total", "message_total",
        "robot_comment_total", "merged_owner_total", "submitter_total",
    )}
    projects = defaultdict(Counter)
    status_counts = Counter()
    unknown_submitters = 0
    for change in changes:
        server = change["server"]
        owner = person_key(change["owner"], server)
        status_counts[change["status"]] += 1
        if owner:
            counters["person_total"][owner] += 1
            projects[f"{server}::{change.get('project', '(unknown)')}"][owner] += 1
        if change["merged"]:
            if owner:
                counters["merged_owner_total"][owner] += 1
            submitter = person_key(change["submitter"], server)
            if not submitter:
                unknown_submitters += 1
            elif in_window(change.get("submitted"), cutoff):
                counters["submitter_total"][submitter] += 1
        reviewers = set()
        for vote in change["votes"]:
            person = person_key(vote["reviewer"], server)
            if person and vote["value"] != 0:
                counters["vote_total"][person] += 1
                reviewers.add(person)
        for field, counter_name in (("comments", "comment_total"), ("messages", "message_total"),
                                    ("robot_comments", "robot_comment_total")):
            for event in change.get(field) or []:
                if not in_window(event.get("updated") or event.get("date"), cutoff):
                    continue
                person = person_key(event.get("author", {}), server)
                if person:
                    counters[counter_name][person] += 1
                    tag = event.get("tag", "")
                    # 새 patch set 업로드는 리뷰로 세지 않는다. review 태그는 리뷰 행위다.
                    human_review = (field == "comments" or (field == "messages" and (
                        not tag.startswith("autogenerated:") or tag == "autogenerated:gerrit:review")))
                    if human_review:
                        reviewers.add(person)
        for person in reviewers - {owner}:
            counters["reviewer_total"][person] += 1
    return {
        **{key: dict(counter) for key, counter in counters.items()},
        "project_person": {key: dict(counter) for key, counter in projects.items()},
        "status_counts": dict(status_counts), "unknown_submitter_changes": unknown_submitters,
    }


def collect_signal(servers: list[str], since_days: int, limit_per_server: int) -> dict:
    conf = _load_gerrit_conf()
    now = dt.datetime.now(dt.timezone.utc)
    changes = []
    truncated_servers = []
    robot_unavailable_servers = []
    for name in dict.fromkeys(servers):
        if name not in conf:
            raise CollectionError(f"[{name}] Gerrit 설정이 없습니다.")
        client = GerritClient(name, conf[name])
        try:
            items, truncated = fetch_recent_changes(client, since_days, limit_per_server)
            if truncated:
                truncated_servers.append(name)
            for index, change in enumerate(items, 1):
                change["comments"] = fetch_comments(client, change["_number"])
                change["robot_comments"] = (
                    None if name in robot_unavailable_servers else fetch_comments(client, change["_number"], robot=True)
                )
                if change["robot_comments"] is None and name not in robot_unavailable_servers:
                    robot_unavailable_servers.append(name)
                changes.append(change)
                if index % 50 == 0 or index == len(items):
                    print(f"# [{name}] 댓글/리뷰 메타데이터 {index}/{len(items)} 확인", flush=True)
        finally:
            client.session.close()
    return {
        "schema_version": 2, "collected_at": now.isoformat(), "window_days": since_days,
        "reachable_servers": list(dict.fromkeys(servers)), "truncated_servers": truncated_servers,
        "robot_comments_unavailable_servers": robot_unavailable_servers,
        "note": "최근 갱신 change 범위. 댓글/메시지/submitter 집계는 이벤트 시각으로 제한. "
                "votes는 현재 patch set 스냅샷이며 과거 투표 이벤트 전체가 아님. "
                "messages는 시스템 이벤트 포함, comments는 모든 patch set의 공개 댓글. "
                "자동화 계정은 사람이란 보장이 없으며 robot 댓글은 별도 집계. "
                "본문은 저장하지 않음. 라우팅 전용, 개인 성과 비교·평가 금지.",
        **aggregate(changes, since_days, now), "changes": changes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--server", action="append", help="Gerrit 설정의 서버 이름. 반복 가능, 생략하면 전체")
    parser.add_argument("--since-days", type=int, default=180)
    parser.add_argument("--limit-per-server", type=int, default=300, help="서버당 change 상한 (0: 전체 조회)")
    parser.add_argument("--top", type=int, default=5, help="프로젝트별 owner 표시 인원")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    if args.since_days <= 0 or args.limit_per_server < 0 or args.top <= 0:
        parser.error("since-days/top은 양수, limit-per-server는 0 이상이어야 합니다.")
    try:
        servers = args.server or list(_load_gerrit_conf())
        result = collect_signal(servers, args.since_days, args.limit_per_server)
        print(f"# Gerrit 상태: {result['status_counts']}")
        for change in result["changes"]:
            owner = person_key(change["owner"], change["server"]) or "unknown"
            submitter = person_key(change["submitter"], change["server"]) or "unknown"
            print(f"[{change['server']}] {change['_number']} {change['status']} owner={owner} "
                  f"submitter={submitter} votes={sum(vote['value'] != 0 for vote in change['votes'])} "
                  f"comments={len(change['comments'])} messages={len(change['messages'])}")
        for project, people in sorted(result["project_person"].items()):
            print(f"# {project}: {Counter(people).most_common(args.top)} (owned changes)")
        if result["truncated_servers"]:
            print(f"WARNING: change 상한 도달: {result['truncated_servers']}. 전체 조회는 --limit-per-server 0", file=sys.stderr)
        if result["robot_comments_unavailable_servers"]:
            print(f"WARNING: robotcomments API 미지원/미노출: {result['robot_comments_unavailable_servers']}", file=sys.stderr)
        print(f"# MERGED인데 submitter 미확인: {result['unknown_submitter_changes']}")
        if args.json_out:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"# JSON 저장: {args.json_out}")
    except CollectionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except OSError:
        print("ERROR: Gerrit 설정/결과 파일 읽기 또는 쓰기 실패.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
