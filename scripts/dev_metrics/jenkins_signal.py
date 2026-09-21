# /// script
# requires-python = ">=3.11"
# dependencies = ["requests>=2.32,<3"]
# ///
"""agent-action-items.md C1: CI/CD 파이프라인 데이터 (DORA — 배포 빈도·변경 실패율)

2026-09-21 조사 결과: LGE의 webOS SCM CI/CD는 Gerrit(gpro.lge.com, 이 저장소
gerrit_conf_dict의 'gpro'와 동일 인스턴스) 이벤트를 Jenkins(gecko.lge.com/jenkins/)가
Gerrit Trigger 플러그인으로 받아 빌드를 실행하는 구조다(Confluence
"[SCM][Seminar] CI/CD Infrastructure", pageId=3531826964 참고). Jenkins REST API가
이 저장소의 공유 LDAP 계정(secure_info.py의 ladp_idpw)으로 그대로 인증되는 것을 확인했다
— 별도 자격증명 발급 없이 바로 조회 가능하다.

이 스크립트는 Jenkins Job의 빌드 이력(`{job}/api/json?tree=builds[number,result,
timestamp,duration]`)으로 DORA 지표 중 두 가지를 근사한다:
  * 배포 빈도(deployment frequency): 조회 기간 내 빌드 횟수 / 기간(일)
  * 변경 실패율(change failure rate): SUCCESS가 아닌 빌드(FAILURE/UNSTABLE/ABORTED) 비율

**주의**: 이 Jenkins job 다수는 "빌드"(컴파일/유닛테스트)이지 운영 배포(deploy to prod)가
아니다 — job 이름에 실제 배포 파이프라인인지 여부가 섞여 있어, 이 수치는 "빌드 성공률/빈도"의
근사치이지 엄밀한 DORA "배포 빈도"가 아니다. 실제 배포 파이프라인 job만 걸러 쓰려면 job 이름
패턴을 사용자와 함께 정해야 한다(`--job-pattern`).

또한 Jenkins 빌드는 팀/프로젝트 단위로 트리거되는 경우가 많아(여러 커밋이 한 빌드에 묶임),
**개인 단위 지표가 아니라 job(프로젝트) 단위 지표**로 다룬다 — 개인 성과 비교에 쓰지 않는다.

사용 예:
    uv run jenkins_signal.py --job-pattern acp-master-engineering --since-days 90 --top 10
    uv run jenkins_signal.py --job acp-master-engineering-sa8155 --since-days 180
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

_REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
from secure_info import ladp_idpw  # noqa: E402

DEFAULT_BASE_URL = "http://gecko.lge.com/jenkins/"
NON_SUCCESS_RESULTS = {"FAILURE", "UNSTABLE", "ABORTED"}


class CollectionError(Exception):
    pass


class JenkinsClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/") + "/"
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(*ladp_idpw)

    def get(self, path: str, params: dict | None = None) -> dict:
        resp = self.session.get(self.base_url + path.lstrip("/"), params=params, timeout=30)
        if resp.status_code != 200:
            raise CollectionError(f"Jenkins 요청 실패 ({resp.status_code}): {self.base_url + path}")
        return resp.json()


def list_jobs(client: JenkinsClient, name_pattern: str | None = None) -> list[dict]:
    data = client.get("api/json", params={"tree": "jobs[name,url,color]"})
    jobs = data.get("jobs", [])
    if name_pattern:
        jobs = [j for j in jobs if name_pattern.lower() in j["name"].lower()]
    return jobs


def fetch_builds(client: JenkinsClient, job_name: str, limit: int = 100) -> list[dict]:
    tree = f"builds[number,result,timestamp,duration]{{0,{limit}}}"
    data = client.get(f"job/{job_name}/api/json", params={"tree": tree})
    return data.get("builds", [])


def compute_job_stats(builds: list[dict], since_days: int, now_ms: int) -> dict:
    cutoff_ms = now_ms - since_days * 86400 * 1000
    in_window = [b for b in builds if b.get("timestamp", 0) >= cutoff_ms]
    total = len(in_window)
    if total == 0:
        return {"builds_in_window": 0}
    non_success = sum(1 for b in in_window if b.get("result") in NON_SUCCESS_RESULTS)
    building = sum(1 for b in in_window if b.get("result") is None)
    return {
        "builds_in_window": total,
        "deploy_frequency_per_day": round(total / since_days, 3),
        "non_success_count": non_success,
        "change_failure_rate": round(non_success / total, 3),
        "still_building": building,
        "avg_duration_sec": round(sum(b.get("duration", 0) for b in in_window) / total / 1000, 1),
    }


def collect_signal(base_url: str, job_names: list[str] | None, job_pattern: str | None,
                    since_days: int, limit_per_job: int, top: int) -> dict:
    client = JenkinsClient(base_url)
    now_ms = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)

    if job_names:
        jobs = [{"name": name} for name in job_names]
    else:
        jobs = list_jobs(client, job_pattern)
        if top:
            jobs = jobs[:top]

    per_job: dict[str, dict] = {}
    job_errors: dict[str, str] = {}
    for job in jobs:
        name = job["name"]
        try:
            builds = fetch_builds(client, name, limit_per_job)
        except Exception as exc:  # noqa: BLE001 - POC: job별 실패를 한 줄로 보고하고 계속 진행
            job_errors[name] = str(exc)
            continue
        per_job[name] = compute_job_stats(builds, since_days, now_ms)

    return {
        "base_url": base_url,
        "since_days": since_days,
        "limit_per_job": limit_per_job,
        "jobs_requested": len(jobs),
        "job_errors": job_errors,
        "per_job": per_job,
        "note": "job(프로젝트) 단위 지표이며 개인 단위가 아님 — 개인 성과 비교·평가에 쓰지 않는다. "
                "Jenkins job 다수는 빌드(컴파일/UT)이지 운영 배포가 아닐 수 있어 '배포 빈도'는 근사치.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--job", action="append", dest="job_names", help="특정 job 이름(복수 가능, 지정 시 --job-pattern 무시)")
    parser.add_argument("--job-pattern", help="job 이름에 포함된 문자열로 필터(대소문자 무시)")
    parser.add_argument("--since-days", type=int, default=90)
    parser.add_argument("--limit-per-job", type=int, default=100, help="job당 조회할 최근 빌드 수 상한")
    parser.add_argument("--top", type=int, default=20, help="--job 미지정 시 조회할 job 수 상한(전체 864개 중)")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    result = collect_signal(args.base_url, args.job_names, args.job_pattern, args.since_days, args.limit_per_job, args.top)

    print(f"# Jenkins CI/CD 신호(POC) — {result['base_url']}, 최근 {result['since_days']}일, job {result['jobs_requested']}개 조회")
    if result["job_errors"]:
        print("⚠️ 일부 job 조회 실패:")
        for k, v in result["job_errors"].items():
            print(f"  - {k}: {v}")
    for name, stats in sorted(result["per_job"].items(), key=lambda kv: -kv[1].get("builds_in_window", 0)):
        if stats.get("builds_in_window", 0) == 0:
            print(f"  {name}: 조회 기간 내 빌드 없음")
            continue
        print(f"  {name}: 빌드 {stats['builds_in_window']}건, 배포빈도 {stats['deploy_frequency_per_day']}/일, "
              f"변경실패율 {stats['change_failure_rate']:.1%}, 평균소요 {stats['avg_duration_sec']:.0f}초")
    print(f"\n※ {result['note']}")

    if args.json_out:
        args.json_out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"# JSON 저장: {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
