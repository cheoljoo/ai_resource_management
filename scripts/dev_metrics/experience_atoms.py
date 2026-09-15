"""신규 지표: 경험 원자(Experience Atom, EA) 기반 전문성 폭/깊이

Mockus & Herbsleb, "Expertise Browser: A Quantitative Approach to Identifying
Expertise" (ICSE 2002)의 방법을 그대로 적용한다: 설문/자기기술 없이, 형상관리
시스템(git)의 변경 이력만으로 "그 사람이 그 대상에 대해 획득한 경험 한 단위"를
정의하고 누적 집계한다.

이 구현에서는 커밋 하나가 건드린 파일 하나를 EA 1개로 보고, 아래 3축으로
분해한다 (원 논문의 "기능 영역 / 사용 기술 / 변경 목적" 축과 대응):
  * module  — 파일 경로의 상위 디렉터리(깊이 --module-depth, 기본 2단계)
  * tech    — 파일 확장자
  * purpose — 커밋 메시지로 추정한 변경 목적:
              corrective(수정/버그) / adaptive(기능 추가/마이그레이션) /
              perfective(리팩터링/정리) / unknown

EA를 (module, tech, purpose)별로 집계한 뒤, 다음 두 값을 산출한다:
  * breadth — EA 합계가 --min-ea 이상인 서로 다른 module 수(여러 영역 경험)
  * depth   — 가장 EA가 많은 module의 EA 합계(특정 영역에 대한 깊은 경험)

developer_evaluation_metrics.md 6.6절, 1.3절 Goodhart's Law 경고와 함께 읽을 것
— EA는 "불완전하지만 합리적인" 척도일 뿐, 변경량이 곧 전문성의 질을 보장하지
않는다(원 논문 표현 그대로).

사용 예:
    python3 experience_atoms.py --repo /path/to/repo --author "cheoljoo"
"""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict

from git_utils import iter_commits

CORRECTIVE_RE = re.compile(r"\b(fix|bug|hotfix|patch|defect|이슈|버그|수정)\b", re.IGNORECASE)
PERFECTIVE_RE = re.compile(r"\b(refactor|cleanup|style|rename|docs?|chore|정리|리팩)\b", re.IGNORECASE)
ADAPTIVE_RE = re.compile(r"\b(feat|feature|add|migrate|migration|introduce|추가|신규)\b", re.IGNORECASE)


def classify_purpose(subject: str) -> str:
    if CORRECTIVE_RE.search(subject):
        return "corrective"
    if PERFECTIVE_RE.search(subject):
        return "perfective"
    if ADAPTIVE_RE.search(subject):
        return "adaptive"
    return "unknown"


def module_of(path: str, depth: int) -> str:
    parts = path.split("/")
    if len(parts) <= depth:
        return "/".join(parts[:-1]) or "(root)"
    return "/".join(parts[:depth])


def tech_of(path: str) -> str:
    if "." not in path.rsplit("/", 1)[-1]:
        return "(none)"
    return path.rsplit(".", 1)[-1]


def compute_experience_atoms(
    repo: str,
    author: str | None,
    module_depth: int,
    branch: str = "HEAD",
) -> dict:
    commits = iter_commits(repo, rev_range=branch, with_files=True)
    if author:
        needle = author.lower()
        commits = [c for c in commits if needle in c.author_name.lower() or needle in c.author_email.lower()]

    ea_counter: Counter[tuple[str, str, str]] = Counter()
    module_ea: Counter[str] = Counter()

    for c in commits:
        purpose = classify_purpose(c.subject)
        for path in c.files:
            module = module_of(path, module_depth)
            tech = tech_of(path)
            ea_counter[(module, tech, purpose)] += 1
            module_ea[module] += 1

    return {
        "commit_count": len(commits),
        "ea_total": sum(ea_counter.values()),
        "by_module_tech_purpose": ea_counter,
        "module_ea": module_ea,
    }


def breadth_depth(module_ea: Counter[str], min_ea: int) -> tuple[int, int, str | None]:
    qualifying = [m for m, n in module_ea.items() if n >= min_ea]
    breadth = len(qualifying)
    if not module_ea:
        return 0, 0, None
    top_module, depth = module_ea.most_common(1)[0]
    return breadth, depth, top_module


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--repo", required=True, help="분석할 git 저장소 경로")
    parser.add_argument("--branch", default="HEAD", help="분석 대상 브랜치")
    parser.add_argument("--author", default=None, help="특정 작성자(이름/이메일 일부)로 범위 제한")
    parser.add_argument("--module-depth", type=int, default=2, help="모듈로 묶을 디렉터리 깊이 (기본 2)")
    parser.add_argument("--min-ea", type=int, default=5, help="'실질 경험'으로 인정할 최소 EA 개수 (기본 5)")
    parser.add_argument("--top", type=int, default=10, help="출력할 상위 모듈 수")
    args = parser.parse_args()

    result = compute_experience_atoms(args.repo, args.author, args.module_depth, args.branch)
    breadth, depth, top_module = breadth_depth(result["module_ea"], args.min_ea)

    print(f"# Experience Atoms — {args.repo} (author filter: {args.author or '(all)'})")
    print(f"commits: {result['commit_count']}, EA total: {result['ea_total']}")
    print(f"breadth (min_ea={args.min_ea}): {breadth} modules")
    print(f"depth: {depth} EA in top module '{top_module}'")
    print()
    print(f"# Top {args.top} modules by EA")
    for module, n in result["module_ea"].most_common(args.top):
        print(f"  {n:6d}  {module}")


if __name__ == "__main__":
    main()
