"""POC: 전문가 파인더 (Expert Finder) — "이 모듈은 누구에게 물어볼까"

Mockus & Herbsleb(2002)의 경험 원자(EA) 개념을 **저장소의 모든 기여자**에게 적용해,
모듈별로 최근 가장 많이 손댄 사람(=물어볼 만한 사람 후보)을 찾아준다. 원 논문이
실증한 병목("두 번째 기여자가 작업 구간 마지막 10%에야 개입") — 즉 전문가를 찾는 데
걸리는 시간 자체를 줄이는 것이 목적이다.

**POC 제약 (spec.md "범위 밖" 절, 2026-09-11 결정)**:
  * 이 스크립트만 spec.md의 "본인 범위 한정" 원칙에 대한 명시적 예외다 — 공유 저장소에
    이미 공개된 git log(= git blame과 동일 수준 정보)를 라우팅 목적으로만 집계한다.
  * **개념 검증(POC)이므로 기본값은 최근 14일(2주)치 커밋으로 제한**한다. 전체 이력을
    다루지 않는다 — 전체 이력 확장 여부는 이 POC 결과를 보고 별도로 판단한다.
  * 결과는 "최근 기여자 랭킹"일 뿐 "역량 평가"가 아니다. 인사 평가·개인 비교 목적으로
    쓰지 않는다(developer_evaluation_metrics.md 1.3절 Goodhart's Law와 동일 원칙).

사용 예:
    python3 expert_finder.py --repo /path/to/repo --since-days 14
    python3 expert_finder.py --repo /path/to/repo --since-days 14 --module src/foo
"""
from __future__ import annotations

import argparse
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from experience_atoms import classify_purpose
from git_utils import iter_commits


def _module_of(path: str, depth: int) -> str:
    parts = path.split("/")[:-1]
    if not parts:
        return "(root)"
    return "/".join(parts[:depth]) or "(root)"


def compute_expert_map(
    repo: str,
    branch: str,
    since_days: int,
    module_depth: int = 2,
) -> dict:
    since_date = (datetime.now(timezone.utc) - timedelta(days=since_days)).strftime("%Y-%m-%d")
    commits = iter_commits(repo, branch, with_files=True, extra_args=[f"--since={since_date}"])

    # (module) -> Counter(author -> EA)
    ea_by_module_author: dict[str, Counter[str]] = defaultdict(Counter)
    # (module, author) -> 최근 커밋 시각 (동률일 때 "최근에 만졌는가"로 보조 정렬)
    last_touch: dict[tuple[str, str], str] = {}
    author_commit_count: Counter[str] = Counter()

    for c in commits:
        author_commit_count[c.author_name] += 1
        for f in c.files:
            module = _module_of(f, module_depth)
            ea_by_module_author[module][c.author_name] += 1
            key = (module, c.author_name)
            if key not in last_touch or c.dt.isoformat() > last_touch[key]:
                last_touch[key] = c.dt.isoformat()

    return {
        "since_date": since_date,
        "since_days": since_days,
        "total_commits": len(commits),
        "distinct_authors": len(author_commit_count),
        "ea_by_module_author": {m: dict(c) for m, c in ea_by_module_author.items()},
        "last_touch": last_touch,
    }


def rank_experts_for_module(expert_map: dict, module: str, top: int = 5) -> list[tuple[str, int, str]]:
    matches = [m for m in expert_map["ea_by_module_author"] if module in m]
    combined: Counter[str] = Counter()
    latest: dict[str, str] = {}
    for m in matches:
        for author, ea in expert_map["ea_by_module_author"][m].items():
            combined[author] += ea
            key = (m, author)
            if author not in latest or expert_map["last_touch"].get(key, "") > latest[author]:
                latest[author] = expert_map["last_touch"].get(key, "")
    ranked = sorted(combined.items(), key=lambda kv: (-kv[1], -1 if not latest.get(kv[0]) else 0))
    return [(author, ea, latest.get(author, "")) for author, ea in ranked[:top]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="분석할 git 저장소 경로 (팀 공유 저장소)")
    parser.add_argument("--branch", default="HEAD", help="분석 대상 브랜치")
    parser.add_argument(
        "--since-days", type=int, default=14,
        help="POC 범위 제약: 최근 N일치 커밋만 사용 (기본 14일 = 2주, spec.md 범위 밖 절 참고)",
    )
    parser.add_argument("--module-depth", type=int, default=2, help="모듈로 묶을 디렉터리 깊이 (기본 2)")
    parser.add_argument("--module", default=None, help="특정 모듈(경로 일부)을 지정하면 그 모듈의 전문가만 조회")
    parser.add_argument("--top", type=int, default=5, help="모듈당 상위 몇 명을 보여줄지")
    args = parser.parse_args()

    expert_map = compute_expert_map(args.repo, args.branch, args.since_days, args.module_depth)

    print(
        f"# 전문가 파인더 POC (최근 {expert_map['since_days']}일, {expert_map['since_date']} 이후, "
        f"커밋 {expert_map['total_commits']}건, 기여자 {expert_map['distinct_authors']}명)\n"
    )

    if expert_map["total_commits"] == 0:
        print("⚠️ 지정한 기간 내 커밋이 없습니다. --since-days를 늘려 다시 시도하세요.")
        return

    if args.module:
        ranked = rank_experts_for_module(expert_map, args.module, args.top)
        if not ranked:
            print(f"'{args.module}'과 일치하는 모듈을 찾지 못했습니다.")
            return
        print(f"## '{args.module}' 최근 기여자 순위\n")
        for author, ea, last in ranked:
            print(f"  {author:<30} EA={ea:>4}  최근 활동: {last or '-'}")
    else:
        print("## 모듈별 최근 기여자 1순위 (전체 개요)\n")
        for module, authors in sorted(expert_map["ea_by_module_author"].items()):
            top_author, top_ea = max(authors.items(), key=lambda kv: kv[1])
            print(f"  {module:<40} 1순위: {top_author} (EA={top_ea}, 이 모듈 기여자 {len(authors)}명)")

    print(
        "\n※ 이 순위는 '최근 누가 이 모듈을 많이 만졌는가'일 뿐 역량 평가가 아닙니다 — 질문할 사람을"
        " 찾는 라우팅 용도로만 사용하세요 (developer_evaluation_metrics.md 1.3절 Goodhart's Law)."
    )
    print(
        f"※ POC 범위 제약: 최근 {expert_map['since_days']}일치 데이터만 사용했습니다"
        " (spec.md '범위 밖' 절 — 전체 이력 확장은 이 POC 결과를 보고 별도 결정)."
    )


if __name__ == "__main__":
    main()
