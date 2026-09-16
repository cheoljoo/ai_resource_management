"""agent-action-items.md A4: 테스트 충분성 정량화 (Test Adequacy)

developer_evaluation_metrics.md 1.7절이 지금까지 "개념"으로만 설명해온 테스트 충분성 신호 중,
외부 도구 없이 로컬 git만으로 즉시 계산 가능한 부분("프로덕션 코드만 바뀌고 테스트 코드는 안 바뀐
커밋의 비율")을 실제로 계산한다. 커버리지 도구(coverage.py 등) 실행은 대상 저장소마다 테스트 셋업이
달라 일반화하기 어려워 이번 POC 범위에서는 제외한다(agent-action-items.md A4 "위임 시 추가로 정의해야
할 것" 참고) — 1차로 "테스트 파일 동반 여부"만 구현한다.

사용 예:
    python3 test_adequacy.py --repo /path/to/repo --author "cheoljoo"
"""
from __future__ import annotations

import argparse
import re

from git_utils import iter_commits

_TEST_PATH_PATTERNS = [
    re.compile(r"(^|/)tests?/"),
    re.compile(r"(^|/)test_[^/]+\.[a-zA-Z0-9]+$"),
    re.compile(r"(^|/)[^/]+_test\.[a-zA-Z0-9]+$"),
    re.compile(r"(^|/)[^/]+\.test\.[a-zA-Z0-9]+$"),
    re.compile(r"(^|/)[^/]+\.spec\.[a-zA-Z0-9]+$"),
    re.compile(r"(^|/)spec/"),
]

# 프로덕션 코드로 보지 않는(둘 다 아닌 것으로 취급) 파일들 — 문서/설정만 바뀐 커밋은
# "테스트가 필요한 변경"이 아니므로 분모에서 제외해야 비율이 왜곡되지 않는다.
_NON_CODE_PATTERNS = [
    re.compile(r"\.(md|txt|rst|json|yml|yaml|toml|cfg|ini|lock)$"),
    re.compile(r"(^|/)\.gitignore$"),
    re.compile(r"(^|/)LICENSE$"),
]


def _is_test_file(path: str) -> bool:
    return any(p.search(path) for p in _TEST_PATH_PATTERNS)


def _is_non_code_file(path: str) -> bool:
    return any(p.search(path) for p in _NON_CODE_PATTERNS)


def compute_test_adequacy(repo: str, author: str | None, branch: str = "HEAD") -> dict:
    commits = iter_commits(repo, branch, with_files=True)
    if author:
        needle = author.lower()
        commits = [c for c in commits if needle in c.author_name.lower() or needle in c.author_email.lower()]

    total = len(commits)
    code_touching = 0
    code_with_test = 0
    test_only = 0
    prod_only_commits: list[str] = []

    for c in commits:
        files = c.files
        if not files:
            continue
        touches_test = any(_is_test_file(f) for f in files)
        touches_prod = any((not _is_test_file(f)) and (not _is_non_code_file(f)) for f in files)

        if touches_test and not touches_prod:
            test_only += 1
        if touches_prod:
            code_touching += 1
            if touches_test:
                code_with_test += 1
            else:
                prod_only_commits.append(f"{c.commit_hash[:8]} {c.subject}")

    ratio = (code_with_test / code_touching) if code_touching else None

    return {
        "repo": repo,
        "author_filter": author,
        "total_commits": total,
        "code_touching_commits": code_touching,
        "code_commits_with_test_change": code_with_test,
        "test_only_commits": test_only,
        "test_inclusion_ratio": ratio,
        "prod_only_sample": prod_only_commits[:10],
        "prod_only_total": len(prod_only_commits),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="분석할 git 저장소 경로")
    parser.add_argument("--author", default=None, help="특정 작성자(이름/이메일 일부)로 범위 제한")
    parser.add_argument("--branch", default="HEAD", help="분석 대상 브랜치")
    args = parser.parse_args()

    r = compute_test_adequacy(args.repo, args.author, args.branch)

    print(f"# 테스트 충분성(파일 동반 여부) — {r['repo']}")
    if r["author_filter"]:
        print(f"  (작성자 필터: {r['author_filter']})")
    print(f"\n전체 커밋: {r['total_commits']}")
    print(f"프로덕션 코드를 건드린 커밋: {r['code_touching_commits']}")
    print(f"  그 중 테스트 코드도 함께 바뀐 커밋: {r['code_commits_with_test_change']}")
    if r["test_inclusion_ratio"] is not None:
        print(f"  -> 테스트 동반 비율: {r['test_inclusion_ratio']:.1%}")
    else:
        print("  -> 프로덕션 코드를 건드린 커밋이 없어 비율 계산 불가")
    print(f"테스트 파일만 단독으로 바뀐 커밋: {r['test_only_commits']} (리팩터링/보강성 테스트로 추정)")

    if r["prod_only_sample"]:
        print(f"\n테스트 미동반 커밋 샘플 (최대 10개, 총 {r['prod_only_total']}개):")
        for line in r["prod_only_sample"]:
            print(f"  - {line}")

    print(
        "\n※ '테스트가 없다'가 곧 '품질이 낮다'는 뜻은 아닙니다 — 리팩터링/문서/설정 변경일 수 있습니다"
        " (developer_evaluation_metrics.md 1.3절 Goodhart's Law). 1차 스크리닝 신호로만 사용하세요."
    )


if __name__ == "__main__":
    main()
