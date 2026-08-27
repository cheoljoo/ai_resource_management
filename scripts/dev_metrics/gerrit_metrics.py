"""Gerrit 변경 이력 기반 지표 계산 (gerrit_fetch.py 결과 JSON을 입력으로 받음)

계산 항목:
  * 1.1 재작업률 근사치 - Change당 patchset(Revision) 개수 분포
  * 상태 분포 - NEW / MERGED / ABANDONED
  * 2.1 변경 리드 타임 - MERGED change의 created ~ submitted 시간차
  * 변경 규모 - insertions/deletions 분포
  * 프로젝트별 작업량 분포

사용 예:
    python3 gerrit_metrics.py --in /tmp/gerrit_self.json
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime

GERRIT_TS_FORMAT = "%Y-%m-%d %H:%M:%S.%f000"


def parse_ts(ts: str) -> datetime:
    return datetime.strptime(ts, GERRIT_TS_FORMAT)


def load_changes(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    changes = []
    for server, items in data.items():
        for c in items:
            c["_server"] = server
            changes.append(c)
    return changes


def compute_metrics(changes: list[dict]) -> dict:
    status_counter = Counter(c["status"] for c in changes)
    patchset_counts = [c.get("current_revision_number", 1) for c in changes]
    project_counter = Counter(c["project"] for c in changes)
    month_counter = Counter(parse_ts(c["created"]).strftime("%Y-%m") for c in changes)

    merged = [c for c in changes if c["status"] == "MERGED"]
    lead_times_hours = []
    for c in merged:
        if not c.get("updated"):
            continue
        created = parse_ts(c["created"])
        updated = parse_ts(c["updated"])  # submitted often null in this dataset; updated ~= last activity
        lead_times_hours.append((updated - created).total_seconds() / 3600)

    insertions = [c.get("insertions", 0) for c in changes]
    deletions = [c.get("deletions", 0) for c in changes]

    high_patchset = sorted(
        [c for c in changes if c.get("current_revision_number", 1) >= 5],
        key=lambda c: -c.get("current_revision_number", 1),
    )

    return {
        "total_changes": len(changes),
        "status_distribution": dict(status_counter),
        "patchset_avg": round(statistics.mean(patchset_counts), 2) if patchset_counts else 0,
        "patchset_median": statistics.median(patchset_counts) if patchset_counts else 0,
        "patchset_max": max(patchset_counts) if patchset_counts else 0,
        "high_patchset_changes": [
            {"number": c["_number"], "project": c["project"], "patchsets": c["current_revision_number"],
             "subject": c["subject"][:60], "status": c["status"]}
            for c in high_patchset
        ],
        "project_distribution": dict(project_counter.most_common()),
        "month_distribution": dict(sorted(month_counter.items())),
        "lead_time_hours_avg": round(statistics.mean(lead_times_hours), 2) if lead_times_hours else None,
        "lead_time_hours_median": round(statistics.median(lead_times_hours), 2) if lead_times_hours else None,
        "insertions_total": sum(insertions),
        "deletions_total": sum(deletions),
        "insertions_avg": round(statistics.mean(insertions), 1) if insertions else 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="in_path", required=True, help="gerrit_fetch.py 결과 JSON 경로")
    args = parser.parse_args()

    changes = load_changes(args.in_path)
    metrics = compute_metrics(changes)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
