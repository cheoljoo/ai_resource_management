"""전문가 파인더 — Gerrit 리뷰/변경 활동 신호 (spec.md B안, 5개 소스 결합의 일부)

`gerrit_fetch.py`는 원래 "동료 데이터가 섞여 들어오지 않도록" owner를 자기
자신으로 제한하는 안전장치를 두고 있었다. 이 스크립트는 spec.md
"거버넌스 확장" 절(2026-09-11 사용자 승인)에 따라 그 제한을 **라우팅 목적에
한해서만** 완화한다:
  * 원본 코드/리뷰 코멘트 본문은 가져오지 않는다 — project/owner/status/시간
    등 메타데이터만 집계.
  * 결과는 "누가 이 프로젝트를 최근 리뷰/변경했는가"에 대한 라우팅 신호이며,
    개인별 성과 비교·평가로 전용하지 않는다.

자격증명은 기존 `gerrit_fetch.py`와 동일하게 이 워크스페이스 밖의
`~/code/ccr/global_variables.py`(git에 커밋되지 않는 사내 자격증명 파일)를
런타임에 import해서만 사용한다.

사용 예:
    python3 gerrit_signal.py --since-days 180 --top 5
    python3 gerrit_signal.py --since-days 180 --server na --server lamp
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

import requests
from requests.auth import HTTPBasicAuth

GERRIT_CREDS_DIR = os.path.expanduser("~/code/ccr")
XSSI_PREFIX = ")]}'"


def _load_gerrit_conf() -> dict:
    if GERRIT_CREDS_DIR not in sys.path:
        sys.path.insert(0, GERRIT_CREDS_DIR)
    try:
        from global_variables import gerrit_conf_dict  # type: ignore
    except ImportError:
        print(f"ERROR: Gerrit 자격증명 모듈을 찾을 수 없습니다 ({GERRIT_CREDS_DIR}/global_variables.py).")
        sys.exit(4)
    return gerrit_conf_dict


def _decode_json(text: str):
    if text.startswith(XSSI_PREFIX):
        text = "\n".join(text.splitlines()[1:])
    return json.loads(text)


def fetch_recent_changes(server_name: str, conf: dict, since_days: int, limit: int) -> list[dict]:
    auth = HTTPBasicAuth(conf["usr"], conf["pw"])
    url = conf["url"].rstrip("/") + "/a/changes/"
    params = {
        "q": f"-age:{since_days}d",
        "n": str(limit),
        "o": "DETAILED_ACCOUNTS",
    }
    try:
        r = requests.get(url, params=params, auth=auth, timeout=15)
    except requests.RequestException as e:
        print(f"  [{server_name}] 연결 실패: {e}", file=sys.stderr)
        return []
    if r.status_code != 200:
        print(f"  [{server_name}] HTTP {r.status_code} — 인증/권한 문제로 건너뜀", file=sys.stderr)
        return []
    changes = _decode_json(r.text)
    for c in changes:
        c["_server"] = server_name
    return changes


def collect_signal(servers: list[str], since_days: int, limit_per_server: int) -> dict:
    conf = _load_gerrit_conf()
    project_person: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    person_total: Counter[str] = Counter()
    reachable_servers: list[str] = []

    for name in servers:
        s_conf = conf.get(name)
        if not s_conf:
            print(f"  [{name}] 설정 없음 — 건너뜀", file=sys.stderr)
            continue
        changes = fetch_recent_changes(name, s_conf, since_days, limit_per_server)
        if changes:
            reachable_servers.append(name)
        for c in changes:
            owner = c.get("owner", {})
            email = owner.get("email")
            if not email:
                continue
            project = c.get("project", "(unknown)")
            project_person[(name, project)][email] += 1
            person_total[email] += 1

    return {
        "project_person": project_person,
        "person_total": person_total,
        "reachable_servers": reachable_servers,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--server",
        action="append",
        default=None,
        help="조회할 Gerrit 서버 이름(복수 지정 가능, ~/code/ccr/global_variables.py의 키). 생략하면 전체.",
    )
    parser.add_argument("--since-days", type=int, default=180, help="최근 N일 이내 변경만 사용 (기본 180)")
    parser.add_argument("--limit-per-server", type=int, default=300, help="서버당 최대 조회 change 수")
    parser.add_argument("--top", type=int, default=5, help="프로젝트당 상위 몇 명을 보여줄지")
    parser.add_argument("--json-out", default=None, help="집계 결과를 JSON으로 저장할 경로(다른 신호와 결합용)")
    args = parser.parse_args()

    conf = _load_gerrit_conf()
    servers = args.server or list(conf.keys())

    print(f"# Gerrit 신호 — 서버 {len(servers)}개, 최근 {args.since_days}일")
    result = collect_signal(servers, args.since_days, args.limit_per_server)

    print(f"# 응답한 서버: {result['reachable_servers']}")
    for (server, project), counter in sorted(result["project_person"].items()):
        print(f"\n## [{server}] {project}")
        for person, n in counter.most_common(args.top):
            print(f"  {n:4d} changes  {person}")

    print(f"\n# 이번 조회에서 확인된 고유 기여자(owner) 수: {len(result['person_total'])}명")

    if args.json_out:
        serializable = {
            "person_total": dict(result["person_total"]),
            "project_person": {
                f"{server}::{project}": dict(counter)
                for (server, project), counter in result["project_person"].items()
            },
            "reachable_servers": result["reachable_servers"],
        }
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2)
        print(f"# JSON 저장: {args.json_out}")


if __name__ == "__main__":
    main()
