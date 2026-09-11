"""전문가 파인더 — 사내 GitHub/GitLab(mod.lge.com/hub) 활동 신호

회사 내부의 GitHub/GitLab에 해당하는 서비스는 github.com이 아니라
**mod.lge.com/hub**(자체 호스팅 GitLab, API v4)이다. 접속 계정 정보는 이
워크스페이스의 `.env`(`LGEP_ID`/`LGEP_PASSWORD`)를 사용한다 — 이 값은
`~/code/mouse`의 기존 mod.lge.com/hub 연동 스크립트(`mod-project.py`,
`mod-fork.py` 등)가 쓰던 것과 동일한 사내 LGE 포털 계정이다.

수집 항목(180일 이내로 제한):
  * 프로젝트별 최근 커밋 작성자 카운트(`/projects/:id/repository/commits`)
  * 프로젝트별 최근 Merge Request 작성자 카운트
  * 프로젝트별 최근 Issue 작성자 카운트

주의: 이 계정으로 API 조회가 되는 프로젝트만 조회 가능하다 — SSH 키 기반
git clone 권한과 GitLab 웹/API 조회 권한이 다를 수 있다(예: `swpmviz`
그룹은 이 계정으로 API 조회가 되지 않음, 별도 확인 필요).

사용 예:
    python3 gitlab_signal.py --project Tiger/AutoTest_Cmd --project cheoljoo.lee/ldap --since-days 180
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import urllib.parse
from collections import Counter

import requests

BASE_URL = "http://mod.lge.com/hub/api/v4"


def load_env(env_path: str) -> dict:
    env = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k] = v.strip().strip("'").strip('"')
    return env


def resolve_credentials() -> tuple[str, str]:
    env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(env_path):
        print("ERROR: .env 파일을 찾을 수 없습니다 (LGEP_ID/LGEP_PASSWORD 필요).")
        raise SystemExit(4)
    env = load_env(env_path)
    uid, pw = env.get("LGEP_ID"), env.get("LGEP_PASSWORD")
    if not uid or not pw:
        print("ERROR: .env에 LGEP_ID/LGEP_PASSWORD가 없습니다.")
        raise SystemExit(4)
    return uid, pw


def project_id_or_path(project: str) -> str:
    return urllib.parse.quote(project, safe="")


def fetch_commits(auth, project: str, since_iso: str) -> Counter[str]:
    counter: Counter[str] = Counter()
    pid = project_id_or_path(project)
    page = 1
    while True:
        r = requests.get(
            f"{BASE_URL}/projects/{pid}/repository/commits",
            params={"since": since_iso, "per_page": 100, "page": page, "all": "true"},
            auth=auth, timeout=15,
        )
        if r.status_code != 200:
            if page == 1:
                print(f"  [{project}] commits 조회 실패: HTTP {r.status_code}")
            break
        data = r.json()
        if not data:
            break
        for c in data:
            email = c.get("author_email")
            if email:
                counter[email] += 1
        if len(data) < 100:
            break
        page += 1
    return counter


def fetch_mrs_or_issues(auth, project: str, since_iso: str, kind: str) -> Counter[str]:
    counter: Counter[str] = Counter()
    pid = project_id_or_path(project)
    endpoint = "merge_requests" if kind == "mr" else "issues"
    page = 1
    while True:
        r = requests.get(
            f"{BASE_URL}/projects/{pid}/{endpoint}",
            params={"created_after": since_iso, "per_page": 100, "page": page, "state": "all"},
            auth=auth, timeout=15,
        )
        if r.status_code != 200:
            if page == 1:
                print(f"  [{project}] {endpoint} 조회 실패: HTTP {r.status_code}")
            break
        data = r.json()
        if not data:
            break
        for item in data:
            author = item.get("author", {})
            username = author.get("username")
            if username:
                counter[username] += 1
        if len(data) < 100:
            break
        page += 1
    return counter


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", action="append", required=True, help="namespace/project 형식(GitLab path), 복수 지정 가능")
    parser.add_argument("--since-days", type=int, default=180)
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args()

    uid, pw = resolve_credentials()
    auth = (uid, pw)
    since_iso = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=args.since_days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    combined = {"commits": Counter(), "mrs": Counter(), "issues": Counter()}
    print(f"# GitLab(mod.lge.com/hub) 신호 — 최근 {args.since_days}일")
    for project in args.project:
        commits = fetch_commits(auth, project, since_iso)
        mrs = fetch_mrs_or_issues(auth, project, since_iso, "mr")
        issues = fetch_mrs_or_issues(auth, project, since_iso, "issue")
        combined["commits"].update(commits)
        combined["mrs"].update(mrs)
        combined["issues"].update(issues)
        print(f"  [{project}] 커밋:{dict(commits.most_common(3))} MR:{dict(mrs.most_common(3))} 이슈:{dict(issues.most_common(3))}")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump({k: dict(v) for k, v in combined.items()}, f, ensure_ascii=False, indent=2)
        print(f"# JSON 저장: {args.json_out}")


if __name__ == "__main__":
    main()
