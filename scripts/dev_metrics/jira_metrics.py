"""Jira 티켓 이력 기반 지표 계산 (fetch_worklog.py + process_worklog.py 결과 CSV 입력)

계산 항목:
  * 상태/이슈타입/우선순위 분포
  * 월별 티켓 생성 추이 (Velocity)
  * assignee vs reporter 역할 비중

사용 예:
    python3 jira_metrics.py --raw-csv /tmp/cj_raw.csv --owner "cheoljoo.lee"
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter


def load_rows(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def compute_metrics(rows: list[dict], owner_key: str) -> dict:
    status_counter = Counter(r["status"] for r in rows)
    type_counter = Counter(r["issuetype"] for r in rows)
    priority_counter = Counter(r["priority"] for r in rows)
    month_counter = Counter(r["created"][:7] for r in rows if r["created"])

    assignee_count = sum(1 for r in rows if owner_key in r["assignee"])
    reporter_count = sum(1 for r in rows if owner_key in r["reporter"])

    return {
        "total_tickets": len(rows),
        "status_distribution": dict(status_counter.most_common()),
        "issuetype_distribution": dict(type_counter.most_common()),
        "priority_distribution": dict(priority_counter.most_common()),
        "month_distribution": dict(sorted(month_counter.items())),
        "as_assignee": assignee_count,
        "as_reporter": reporter_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-csv", required=True, help="process_worklog.py가 생성한 worklog_raw.csv 경로")
    parser.add_argument("--owner", required=True, help="assignee/reporter 필드에서 찾을 이름 (예: cheoljoo.lee)")
    args = parser.parse_args()

    rows = load_rows(args.raw_csv)
    import json
    print(json.dumps(compute_metrics(rows, args.owner), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
