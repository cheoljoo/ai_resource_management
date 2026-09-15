# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.32,<3", "python-dotenv>=1,<2"]
# ///
"""Jira/Confluence REST API에서 전문가 라우팅용 활동 건수를 수집한다.

uv run jira_confluence_signal.py --person cheoljoo.lee@lge.com --since-days 180
기본 명단은 기존 스냅샷의 people 키이며, 인증은 worktree 루트 .env의 PAT를 쓴다.
본문/댓글은 저장하지 않으며 개인 성과 비교·평가에 사용하지 않는다.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

import requests
from dotenv import dotenv_values

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ENV = SCRIPT_DIR.parent.parent / ".env"
DEFAULT_ROSTER = SCRIPT_DIR / "jira_confluence_signal_2026-09-11.json"


class CollectionError(Exception):
    """인증정보나 서버 응답 본문을 포함하지 않는 수집 오류."""


def load_settings(path: Path) -> dict[str, str]:
    # 프로세스 환경변수가 .env보다 우선. ${...} 확장 없이 토큰을 그대로 읽는다.
    values = dotenv_values(path, interpolate=False) if path.is_file() else {}
    return {key: value for key, value in {**values, **os.environ}.items() if value is not None}


def ssl_verify(settings: dict[str, str], service: str) -> bool:
    value = settings.get(f"{service}_SSL_VERIFY", "true").strip().lower()
    if value not in {"true", "false", "1", "0", "yes", "no"}:
        raise CollectionError(f"{service}_SSL_VERIFY는 true/false여야 합니다.")
    return value in {"true", "1", "yes"}


class AtlassianClient:
    def __init__(self, service: str, settings: dict[str, str]):
        self.service = service
        self.base_url = settings.get(f"{service}_URL", "").rstrip("/")
        token = settings.get(f"{service}_PERSONAL_TOKEN", "")
        if not self.base_url or not token:
            raise CollectionError(f"{service}_URL / {service}_PERSONAL_TOKEN 설정이 필요합니다.")
        url = urlsplit(self.base_url)
        if (url.scheme not in {"http", "https"} or not url.hostname
                or url.username or url.password or url.query or url.fragment):
            raise CollectionError(f"{service}_URL은 인증정보/쿼리 없는 http(s) 기본 URL이어야 합니다.")
        self.verify = ssl_verify(settings, service)
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/json"})
        if not self.verify:
            print(f"WARNING: {service}_SSL_VERIFY=false (인증서 검증 해제)", file=sys.stderr)
        if url.scheme == "http":
            print(f"WARNING: {service}_URL이 HTTP입니다. 가능하면 HTTPS를 사용하세요.", file=sys.stderr)

    def get(self, endpoint: str, params: dict) -> dict:
        try:
            response = self.session.get(
                self.base_url + endpoint, params=params, timeout=30,
                verify=self.verify, allow_redirects=False,
            )
        except requests.RequestException:
            raise CollectionError(f"{self.service}: 연결/인증서/시간초과 오류입니다.") from None
        if response.status_code != 200:
            raise CollectionError(
                f"{self.service}: HTTP {response.status_code}. URL, PAT, 조회 권한을 확인하세요."
            )
        try:
            data = response.json()
        except ValueError:
            raise CollectionError(f"{self.service}: JSON 응답이 아닙니다. REST 기본 URL을 확인하세요.") from None
        if not isinstance(data, dict):
            raise CollectionError(f"{self.service}: 예상하지 못한 응답 형식입니다.")
        return data


def query_literal(value: str) -> str:
    """JQL/CQL 문자열 리터럴의 따옴표와 역슬래시를 escape한다."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def jira_count(client: AtlassianClient, jql: str) -> int:
    data = client.get("/rest/api/2/search", {"jql": jql, "maxResults": 0, "fields": "key"})
    total = data.get("total")
    if type(total) is not int or total < 0:
        raise CollectionError("JIRA: 응답에 유효한 total이 없습니다.")
    return total


def confluence_count(client: AtlassianClient, cql: str) -> int:
    start = 0
    content_ids: set[str] = set()
    while True:
        data = client.get("/rest/api/content/search", {"cql": cql, "start": start, "limit": 100})
        results = data.get("results")
        links = data.get("_links", {})
        if (not isinstance(results, list) or not isinstance(links, dict)
                or any(not isinstance(item, dict) or not item.get("id") for item in results)):
            raise CollectionError("CONFLUENCE: 응답에 유효한 results/id가 없습니다.")
        page_ids = {str(item["id"]) for item in results}
        if links.get("next") and not (page_ids - content_ids):
            raise CollectionError("CONFLUENCE: 페이지가 진행되지 않아 수집을 중단합니다.")
        content_ids.update(page_ids)
        if not links.get("next"):
            return len(content_ids)
        # 서버가 반환한 외부 URL에 인증 헤더를 전달하지 않는다.
        start += len(results)


def load_roster(path: Path, people: list[str] | None) -> dict[str, dict[str, str]]:
    if people:
        raw = {person: {} for person in people}
    else:
        try:
            raw = json.loads(path.read_text(encoding="utf-8")).get("people")
        except (OSError, ValueError, AttributeError):
            raise CollectionError("명단 JSON을 읽을 수 없습니다. --roster 또는 --person을 확인하세요.") from None
    if not isinstance(raw, dict) or not raw:
        raise CollectionError("명단에는 비어 있지 않은 people 객체가 필요합니다.")
    roster = {}
    for person, entry in raw.items():
        if not isinstance(person, str) or not person.strip() or not isinstance(entry, dict):
            raise CollectionError("명단의 사람 식별자/설정 형식이 올바르지 않습니다.")
        # 기존 결합기의 local-part 규칙. 서비스별 계정이 다르면 명시적으로 덮어쓴다.
        default_user = person.strip().split("@", 1)[0]
        identities = {key: entry.get(key, default_user) for key in ("jira_user", "confluence_user")}
        if any(not isinstance(value, str) or not value.strip() for value in identities.values()):
            raise CollectionError("jira_user/confluence_user에는 비어 있지 않은 계정 ID가 필요합니다.")
        roster[person] = identities
    return roster


def collect(roster: dict[str, dict[str, str]], settings: dict[str, str], days: int) -> dict:
    jira = AtlassianClient("JIRA", settings)
    try:
        confluence = AtlassianClient("CONFLUENCE", settings)
    except Exception:
        jira.session.close()
        raise
    people = {}
    try:
        for person, identities in roster.items():
            jira_user = query_literal(identities["jira_user"])
            conf_user = query_literal(identities["confluence_user"])
            jql = f"(assignee = {jira_user} OR reporter = {jira_user}) AND updated >= -{days}d"
            cql = f'contributor = {conf_user} AND lastmodified >= now("-{days}d")'
            people[person] = {
                **identities,
                # 기존 combine_expert_signals.py 호환 키. 실제 기간은 window_days에 기록.
                "jira_total_180d": jira_count(jira, jql),
                "confluence_hits": confluence_count(confluence, cql),
                "jql": jql,
                "cql": cql,
            }
            print(f"{person}: Jira={people[person]['jira_total_180d']}, "
                  f"Confluence={people[person]['confluence_hits']}", flush=True)
    finally:
        jira.session.close()
        confluence.session.close()
    return {
        "collected_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "window_days": days,
        "note": (
            "Jira: 최근 갱신된 담당자/보고자 이슈의 total. Confluence: 최근 수정된 기여 콘텐츠의 "
            "고유 ID 수(전체 페이지). 해당 인물이 그 기간에 직접 수정했다는 뜻은 아님. "
            "토큰의 조회 권한 범위에 한정. jira_total_180d는 호환용 키이며 실제 기간은 window_days. "
            "라우팅 참고용이며 개인 성과 비교·평가에 사용 금지."
        ),
        "people": people,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV, help="인증 .env 경로 (기본: worktree 루트)")
    parser.add_argument("--roster", type=Path, default=DEFAULT_ROSTER, help="people 객체를 가진 명단/기존 신호 JSON")
    parser.add_argument("--person", action="append", help="조회할 계정/이메일 (반복 가능, --roster 대신 사용)")
    parser.add_argument("--since-days", type=int, default=180)
    parser.add_argument("--json-out", type=Path, help="결합 리포트에 전달할 JSON 경로")
    args = parser.parse_args()
    if args.since_days <= 0:
        parser.error("--since-days는 양수여야 합니다.")
    try:
        roster = load_roster(args.roster, args.person)
        result = collect(roster, load_settings(args.env_file), args.since_days)
        # 모든 사람/서비스 조회가 성공한 뒤에만 저장. 실패를 0건으로 숨기지 않는다.
        if args.json_out:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"# JSON 저장: {args.json_out}")
    except CollectionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except OSError:
        print("ERROR: 설정/결과 파일을 읽거나 쓸 수 없습니다.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())