"""신규 지표: 경험 원자(Experience Atom, EA) 기반 전문성 폭/깊이

Mockus & Herbsleb, "Expertise Browser: A Quantitative Approach to Identifying
Expertise" (ICSE 2002)의 방법을 그대로 적용한다: 설문/자기기술 없이, 형상관리
시스템(git)의 변경 이력만으로 "그 사람이 그 대상에 대해 획득한 경험 한 단위"를
정의하고 누적 집계한다.

이 구현에서는 커밋 하나가 건드린 파일 하나를 EA 1개로 보고, 아래 3축으로 분해한다
(원 논문의 "기능 영역 / 사용 기술 / 변경 목적" 축과 대응):
  * module   — 파일 경로의 상위 디렉터리(깊이 --module-depth, 기본 2단계)
  * tech     — 파일 확장자
  * purpose  — 커밋 메시지로 추정한 변경 목적: corrective(수정/버그) / adaptive(기능
               추가/마이그레이션) / perfective(리팩터링/정리) / unknown

EA를 (module, tech, purpose)별로 집계한 뒤, 다음 두 값을 산출한다:
  * breadth — EA 합계가 --min-ea 이상인 서로 다른 module 수 (여러 영역에 걸친 경험)
  * depth   — 가장 EA가 많은 module의 EA 합계 (특정 영역에 대한 깊은 경험)

developer_evaluation_metrics.md 4.4절, 1.3절 Goodhart's Law 경고와 함께 읽을 것 —
EA는 "불완전하지만 합리적인" 척도일 뿐, 변경량이 곧 전문성의 질을 보장하지 않는다
(원 논문 표현 그대로).

사용 예:
    python3 experience_atoms.py --repo /path/to/repo --author "cheoljoo"
"""
from __future__ import annotations

import argparse
import os
import re
from collections import Counter, defaultdict

from git_utils import iter_commits

CORRECTIVE = re.compile(r"\b(fix|fixed|fixes|bug|hotfix|issue|defect|patch)\b", re.IGNORECASE)
PERFECTIVE = re.compile(r"\b(refactor|cleanup|clean up|simplify|perf|optimi[sz]e|style)\b", re.IGNORECASE)
ADAPTIVE = re.compile(r"\b(feat|feature|add|support|migrate|upgrade|implement)\b", re.IGNORECASE)


def classify_purpose(subject: str) -> str:
    if CORRECTIVE.search(subject):
        return "corrective"
    if PERFECTIVE.search(subject):
        return "perfective"
    if ADAPTIVE.search(subject):
        return "adaptive"
    return "unknown"


def _module_of(path: str, depth: int) -> str:
    parts = path.split("/")[:-1]  # 디렉터리만
    if not parts:
        return "(root)"
    return "/".join(parts[:depth]) or "(root)"


def compute_experience_atoms(
    repo: str,
    branch: str,
    author: str | None,
    module_depth: int = 2,
) -> dict:
    commits = iter_commits(repo, branch, with_files=True)
    if author:
        commits = [c for c in commits if author in c.author_email or author in c.author_name]

    ea_by_module: Counter[str] = Counter()
    ea_by_tech: Counter[str] = Counter()
    ea_by_module_purpose: dict[str, Counter[str]] = defaultdict(Counter)

    for c in commits:
        purpose = classify_purpose(c.subject)
        for f in c.files:
            module = _module_of(f, module_depth)
            _, ext = os.path.splitext(f)
            tech = ext.lstrip(".") or "(no-ext)"
            ea_by_module[module] += 1
            ea_by_tech[tech] += 1
            ea_by_module_purpose[module][purpose] += 1

    return {
        "ea_by_module": dict(ea_by_module.most_common()),
        "ea_by_tech": dict(ea_by_tech.most_common()),
        "ea_by_module_purpose": {m: dict(c) for m, c in ea_by_module_purpose.items()},
        "total_ea": sum(ea_by_module.values()),
    }


def summarize_breadth_depth(ea: dict, min_ea: int) -> dict:
    modules_over_threshold = {m: v for m, v in ea["ea_by_module"].items() if v >= min_ea}
    breadth = len(modules_over_threshold)
    depth = max(ea["ea_by_module"].values()) if ea["ea_by_module"] else 0
    deepest_module = max(ea["ea_by_module"], key=ea["ea_by_module"].get) if ea["ea_by_module"] else None
    return {
        "min_ea_threshold": min_ea,
        "breadth_module_count": breadth,
        "depth_max_ea": depth,
        "deepest_module": deepest_module,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="분석할 git 저장소 경로")
    parser.add_argument("--branch", default="HEAD", help="분석 대상 브랜치")
    parser.add_argument("--author", default=None, help="특정 작성자(이름/이메일 일부)로 범위 제한")
    parser.add_argument("--module-depth", type=int, default=2, help="모듈로 묶을 디렉터리 깊이 (기본 2)")
    parser.add_argument("--min-ea", type=int, default=5, help="'실질 경험'으로 인정할 최소 EA 개수 (기본 5)")
    parser.add_argument("--top", type=int, default=15, help="출력할 상위 모듈 수")
    args = parser.parse_args()

    ea = compute_experience_atoms(args.repo, args.branch, args.author, args.module_depth)
    summary = summarize_breadth_depth(ea, args.min_ea)

    print(f"# 경험 원자(Experience Atom) 분석 (총 EA {ea['total_ea']}개, module-depth={args.module_depth})\n")
    print(f"{'module':<40} {'EA':>6}  corrective/adaptive/perfective/unknown")
    for module, count in list(ea["ea_by_module"].items())[: args.top]:
        purpose = ea["ea_by_module_purpose"].get(module, {})
        breakdown = "/".join(str(purpose.get(p, 0)) for p in ("corrective", "adaptive", "perfective", "unknown"))
        print(f"{module:<40} {count:>6}  {breakdown}")

    print(f"\n기술 스택별 EA: {ea['ea_by_tech']}")
    print(
        f"\n실질 경험 임계치(EA>={summary['min_ea_threshold']}) 기준 breadth(폭) = "
        f"{summary['breadth_module_count']}개 모듈"
    )
    print(f"depth(깊이) = {summary['depth_max_ea']} EA (최심 모듈: {summary['deepest_module']})")
    print(
        "\n※ EA는 '불완전하지만 합리적인' 척도일 뿐입니다 — 변경량이 곧 전문성의 질을 보장하지"
        " 않으므로 단독으로 평가하지 마세요 (developer_evaluation_metrics.md 1.3절 Goodhart's Law)."
    )


if __name__ == "__main__":
    main()
