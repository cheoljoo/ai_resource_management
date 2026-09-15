"""POC: 전문가 파인더 (Expert Finder) — "이 모듈은 누구에게 물어볼까"

Mockus & Herbsleb(2002)의 경험 원자(EA) 개념을 **저장소의 모든 기여자**에게
적용해, (저장소, 모듈)별로 최근 가장 많이 손댄 사람(=물어볼 만한 사람 후보)을
찾아준다. 원 논문이 실증한 병목("두 번째 기여자가 작업 구간 마지막 10%에야
개입") — 즉 전문가를 찾는 데 걸리는 시간 자체를 줄이는 것이 목적이다.

**POC 제약 (spec.md "거버넌스 확장" 절, 2026-09-11 결정)**:
  * 이 스크립트는 spec.md의 "본인 범위 한정" 원칙에 대한 명시적 예외다 — 공유
    저장소에 이미 공개된 git log(= git blame과 동일 수준 정보)를 라우팅
    목적으로만 집계한다.
  * `--since-days` 기본값 14일은 "가장 최근에 활발히 만진 사람"을 우선하기
    위한 POC 기본값이며, 검증 목적으로는 `--since-days`를 늘려 여러 저장소를
    합쳐 폭넓게 확인한다(예: 180일). 전체 이력을 무제한으로 다루지는 않는다.
  * 결과는 "최근 기여자 랭킹"일 뿐 "역량 평가"가 아니다. 인사 평가·개인 비교
    목적으로 쓰지 않는다(developer_evaluation_metrics.md 1.3절 Goodhart's Law
    와 동일 원칙).

여러 `--repo`를 동시에 넘기면 (저장소, 모듈)을 합쳐 하나의 랭킹으로 보여준다.

사용 예:
    python3 expert_finder.py --repo /path/to/repo --since-days 14
    python3 expert_finder.py --repo /path/a --repo /path/b --since-days 180 --top 3
"""
from __future__ import annotations

import argparse
import time
from collections import Counter, defaultdict

from experience_atoms import module_of
from git_utils import iter_commits


def collect_module_contributor_ea(
    repos: list[str],
    since_days: int,
    module_depth: int,
    branch: str = "HEAD",
) -> dict[tuple[str, str], Counter[str]]:
    """(repo, module) -> Counter[contributor_email] -> EA count"""
    result: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    since_ts = time.time() - since_days * 86400

    for repo in repos:
        extra_args = [f"--since={since_days}.days"] if since_days > 0 else []
        commits = iter_commits(repo, rev_range=branch, with_files=True, extra_args=extra_args)
        for c in commits:
            if since_days > 0 and c.author_ts < since_ts:
                continue
            for path in c.files:
                module = module_of(path, module_depth)
                result[(repo, module)][c.author_email] += 1

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--repo", action="append", required=True, help="분석할 git 저장소 경로 (팀 공유 저장소, 여러 번 지정 가능)")
    parser.add_argument("--branch", default="HEAD", help="분석 대상 브랜치")
    parser.add_argument(
        "--since-days",
        type=int,
        default=14,
        help="POC 범위 제약: 최근 N일치 커밋만 사용 (기본 14일 = 2주). "
        "다중 저장소 검증처럼 폭넓게 볼 때는 크게 늘려 지정한다(예: 180). 0이면 전체 이력.",
    )
    parser.add_argument("--module-depth", type=int, default=2, help="모듈로 묶을 디렉터리 깊이 (기본 2)")
    parser.add_argument("--module", default=None, help="특정 모듈(경로 일부)을 지정하면 그 모듈의 전문가만 조회")
    parser.add_argument("--top", type=int, default=3, help="모듈당 상위 몇 명을 보여줄지")
    args = parser.parse_args()

    data = collect_module_contributor_ea(args.repo, args.since_days, args.module_depth, args.branch)

    print(f"# Expert Finder — {len(args.repo)}개 저장소, 최근 {args.since_days}일" if args.since_days > 0 else f"# Expert Finder — {len(args.repo)}개 저장소, 전체 이력")
    all_people: set[str] = set()
    for (repo, module), counter in data.items():
        if args.module and args.module not in module:
            continue
        all_people.update(counter.keys())
        repo_name = repo.rstrip("/").rsplit("/", 1)[-1]
        print(f"\n## [{repo_name}] {module}")
        for person, ea in counter.most_common(args.top):
            print(f"  {ea:6d} EA  {person}")

    print(f"\n# 이번 조회에서 확인된 고유 기여자 수: {len(all_people)}명")


if __name__ == "__main__":
    main()
