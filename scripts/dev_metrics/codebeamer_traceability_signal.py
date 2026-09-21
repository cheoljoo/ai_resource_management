"""전문가 파인더(B, AGILEDEV-1132) 확장: CodeBeamer person x day x tracker traceability

CodeBeamer(CB) 4개 인스턴스(cb/vwcb/vscb/acb)에서 배치 조회한 활동 스냅샷(JSON)을 입력받아,
"누가 어느 영역(tracker)에서 언제 무엇을 했는지"를 사람 x 날짜 x 트래커 단위로 집계하고,
각 항목 이름(name)에서 Jira 이슈 키(예: DCM24HEN-2312)를 추출해 함께 붙인다.

이 스크립트는 스냅샷 JSON만 입력으로 받는다(pvs_crawler에 대한 실시간 CBQL 배치 조회는
네트워크 지연이 도메인당 수 분~15분 걸려 이 저장소의 CI/반복 실행에 맞지 않음 — 조회는
`../pvs_crawler`의 `SWPMUtil.worklog.codebeamer._cb_batch_discover` 등을 별도로 실행해 스냅샷을
만들고, 이 스크립트는 그 결과만 소비한다. 스냅샷 레코드 스키마:
    {person, domain, item_id, tracker, type, name, modified_at, submitted_at}

governance (Makefile 상단 주석 (B) 전문가 파인더 원칙 그대로 적용): 이 집계는 "이 영역은
누구에게 물어볼까"를 위한 라우팅/traceability 목적이며, 개인별 순위 매기기·인사평가에는
쓰지 않는다(developer_evaluation_metrics.md 7장).

사용 예:
    uv run codebeamer_traceability_signal.py --snapshot codebeamer_signal_2026-09-21.json
    uv run codebeamer_traceability_signal.py --snapshot codebeamer_signal_2026-09-21.json --person vy4.nguyen
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict

_JIRA_KEY_PATTERN = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d+\b")


def load_snapshot(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_jira_keys(name: str | None) -> list[str]:
    if not name:
        return []
    # 중복 제거하되 등장 순서는 유지
    seen: dict[str, None] = {}
    for m in _JIRA_KEY_PATTERN.findall(name):
        seen.setdefault(m, None)
    return list(seen)


def _day_of(record: dict) -> str | None:
    ts = record.get("modified_at") or record.get("submitted_at")
    if not ts:
        return None
    return ts[:10]  # 'YYYY-MM-DD'


def build_person_day_tracker_table(records: list[dict]) -> list[dict]:
    """person x day x tracker 단위로 건수를 묶고, 그 그룹에서 발견된 Jira 키를 합쳐 반환한다."""
    grouped: dict[tuple[str, str, str, str], dict] = {}
    for r in records:
        day = _day_of(r)
        if day is None:
            continue
        key = (r["person"], day, r["domain"], r.get("tracker") or "?")
        bucket = grouped.setdefault(key, {"count": 0, "jira_keys": set(), "item_ids": []})
        bucket["count"] += 1
        bucket["jira_keys"].update(extract_jira_keys(r.get("name")))
        bucket["item_ids"].append(r.get("item_id"))

    rows = []
    for (person, day, domain, tracker), bucket in sorted(grouped.items()):
        rows.append({
            "person": person,
            "day": day,
            "domain": domain,
            "tracker": tracker,
            "count": bucket["count"],
            "jira_keys": sorted(bucket["jira_keys"]),
            "item_ids": bucket["item_ids"],
        })
    return rows


def tracker_experts(records: list[dict]) -> list[dict]:
    """(domain, tracker) 영역별 활동량 상위 인물 — "이 영역은 누구에게 물어볼까" 라우팅용."""
    area_counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for r in records:
        area_counts[(r["domain"], r.get("tracker") or "?")][r["person"]] += 1

    rows = []
    for (domain, tracker), counter in area_counts.items():
        total = sum(counter.values())
        rows.append({
            "domain": domain,
            "tracker": tracker,
            "total": total,
            "top": counter.most_common(3),
        })
    rows.sort(key=lambda r: -r["total"])
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--snapshot", required=True, help="codebeamer_signal_*.json 스냅샷 경로")
    parser.add_argument("--person", default=None, help="이 사람의 person x day x tracker 행만 출력")
    parser.add_argument("--experts", action="store_true", help="person x day 테이블 대신 영역별 전문가 랭킹만 출력")
    args = parser.parse_args()

    records = load_snapshot(args.snapshot)

    if args.experts:
        result = tracker_experts(records)
    else:
        result = build_person_day_tracker_table(records)
        if args.person:
            result = [r for r in result if r["person"] == args.person]

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
