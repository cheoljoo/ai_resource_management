"""Gerrit 변경 이력 수집 - 특정 소유자(owner)의 change 목록을 REST API로 가져온다.

주의:
* 이 스크립트는 비밀번호/토큰을 절대 포함하지 않는다. Gerrit 서버 접속 정보는
  이 워크스페이스 밖에 이미 존재하는 `~/code/ccr/gerrit/global_variables.py`
  (secure_info.py와 동일한 성격의, git에 커밋되지 않는 사내 자격증명 파일)를
  런타임에 import해서만 사용한다. (`_worklog/secure_info.py`와 동일한 패턴)
* 기본적으로 특정 owner(자기 자신)로 쿼리를 제한해, 동료 데이터가 섞여 들어오지
  않도록 한다.

사용 예:
    python3 gerrit_fetch.py --owner cheoljoo.lee@lge.com --out /tmp/gerrit_self.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import requests
from requests.auth import HTTPBasicAuth

GERRIT_CREDS_DIR = os.path.expanduser("~/code/ccr")
XSSI_PREFIX = ")]}'"
DEFAULT_OPTIONS = ["CURRENT_REVISION", "DETAILED_LABELS", "MESSAGES"]


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


def fetch_changes_for_owner(owner: str, servers: list[str] | None = None, page_size: int = 200) -> dict:
    """서버별로 owner의 change를 모두 페이지네이션하여 가져온다."""
    conf = _load_gerrit_conf()
    servers = servers or list(conf.keys())
    result: dict[str, list] = {}

    for server in servers:
        s_conf = conf.get(server)
        if not s_conf:
            continue
        auth = HTTPBasicAuth(s_conf["usr"], s_conf["pw"])
        url = s_conf["url"].rstrip("/") + "/a/changes/"
        changes: list = []
        start = 0
        while True:
            params = [("q", f"owner:{owner}"), ("n", str(page_size)), ("S", str(start))]
            for opt in DEFAULT_OPTIONS:
                params.append(("o", opt))
            try:
                resp = requests.get(url, params=params, auth=auth, timeout=15, verify=False)
            except requests.exceptions.RequestException as e:
                print(f"[WARN] {server}: 요청 실패 ({e})")
                break
            if resp.status_code != 200:
                print(f"[WARN] {server}: HTTP {resp.status_code} (건너뜀)")
                break
            try:
                page = _decode_json(resp.text)
            except Exception as e:
                print(f"[WARN] {server}: JSON 파싱 실패 ({e})")
                break
            changes.extend(page)
            if not page or not page[-1].get("_more_changes"):
                break
            start += page_size
        if changes:
            result[server] = changes
        print(f"[INFO] {server}: {len(changes)}건")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True, help="Gerrit owner 이메일 (예: cheoljoo.lee@lge.com)")
    parser.add_argument("--servers", nargs="*", default=None, help="조회할 서버 목록 (기본: 전체)")
    parser.add_argument("--out", required=True, help="결과 JSON 저장 경로")
    args = parser.parse_args()

    data = fetch_changes_for_owner(args.owner, args.servers)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    total = sum(len(v) for v in data.values())
    print(f"[INFO] 총 {total}건 저장 -> {args.out}")


if __name__ == "__main__":
    main()
