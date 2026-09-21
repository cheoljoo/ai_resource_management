"""agent-action-items.md C2: 팀 단위 익명 집계 (거버넌스 승인 후 구현)

**거버넌스**: spec.md 기본 원칙("동료 데이터 미사용", 본인 범위 한정)에 대한 명시적 예외.
2026-09-21 사용자 승인: "C2 과정에서 본인 데이터외에 모든 것을 봐도 됩니다. 이제는 범위가
본인에 국한하지 않습니다" — **입력 데이터 범위**가 전체 조직으로 확장됨. 단, 이 승인은
"어떤 사람의 데이터를 입력으로 쓸 수 있는가"에 대한 것이며, **출력은 항상 개인 식별 없는
익명 집계로만 낸다**는 원칙(agent-action-items.md C2 Result)은 그대로 유지한다 — 이 스크립트는
사람 이름이 결과 어디에도 나타나지 않도록 설계되어 있다(로스터 순서/카운트만으로도 역추적이
가능한 극소수 인원 집계는 --min-people 미만이면 결과를 내지 않는다).

`composite_signals.py`의 `compute_profile()`을 사람마다 실행해 5대 대항목 밴드만 취합하고,
밴드별 인원수 분포로만 집계한다(개인별 결과는 어디에도 저장/출력하지 않음).

로스터 파일 형식(JSON): [{"person": "식별자(집계에만 쓰이고 출력 안 됨)", "repo": "...",
"repos": ["...", "..."], "author": "git author 문자열(생략 시 person 사용)"}, ...]

사용 예:
    uv run team_aggregate_signals.py --roster team_roster.json --min-people 3
"""
from __future__ import annotations

import argparse
import json
from collections import Counter

from composite_signals import BAND_GOOD, BAND_NA, BAND_OK, BAND_WATCH, compute_profile

DISCLAIMER = (
    "이 집계는 팀 차원 병목 파악용이며 개인 식별에 다시 쓰일 수 없습니다. "
    "인사평가·개인 비교 목적으로 사용하지 마십시오(developer_evaluation_metrics.md 7장)."
)


def load_roster(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def aggregate_team(roster: list[dict], branch: str) -> dict:
    band_counts: dict[str, Counter] = {}
    included = 0
    skipped: list[str] = []  # 사유만 기록, 누구인지는 기록하지 않음

    for entry in roster:
        person = entry.get("person")
        repo = entry.get("repo") or (entry.get("repos") or [None])[0]
        repos = entry.get("repos") or ([repo] if repo else [])
        author = entry.get("author") or person
        if not repo or not author:
            skipped.append("roster 항목에 repo/author 누락")
            continue
        try:
            profile = compute_profile(repo, repos, author, branch)
        except Exception as exc:  # noqa: BLE001 - POC: 개인 실패는 집계에서 제외하고 계속 진행
            skipped.append(f"실행 실패({type(exc).__name__})")
            continue
        if profile["filled_count"] < 3:
            skipped.append("데이터 부족(filled_count<3)")
            continue
        included += 1
        for category, (band, _evidence) in profile["categories"].items():
            band_counts.setdefault(category, Counter())[band] += 1

    return {
        "included_people": included,
        "skipped_count": len(skipped),
        "skipped_reasons": Counter(skipped),
        "band_distribution": {cat: dict(counter) for cat, counter in band_counts.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--roster", required=True, help="로스터 JSON 경로")
    parser.add_argument("--branch", default="HEAD")
    parser.add_argument("--min-people", type=int, default=5,
                         help="집계에 포함된 인원이 이 값 미만이면 결과를 내지 않는다(소수 인원 역추적 방지, 기본 5)")
    args = parser.parse_args()

    roster = load_roster(args.roster)
    result = aggregate_team(roster, args.branch)

    print(f"# 팀 단위 익명 집계 — 로스터 {len(roster)}명 중 {result['included_people']}명 포함, "
          f"{result['skipped_count']}명 제외")

    if result["included_people"] < args.min_people:
        print(f"\n⚠️ 집계 포함 인원({result['included_people']}명)이 --min-people({args.min_people}) 미만이라 "
              "결과를 출력하지 않습니다 — 소수 인원 집계는 역추적(개인 식별) 위험이 있습니다.")
        return 0

    if result["skipped_reasons"]:
        print("제외 사유:", dict(result["skipped_reasons"]))

    print(f"\n## 대항목별 밴드 분포 ({BAND_WATCH} / {BAND_OK} / {BAND_GOOD} / {BAND_NA})\n")
    for category, dist in result["band_distribution"].items():
        parts = [f"{band} {dist.get(band, 0)}명" for band in (BAND_WATCH, BAND_OK, BAND_GOOD, BAND_NA) if dist.get(band, 0) > 0]
        print(f"- {category}: {', '.join(parts) if parts else '데이터 없음'}")

    print(f"\n※ {DISCLAIMER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
