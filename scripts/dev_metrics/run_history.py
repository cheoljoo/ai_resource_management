"""AI Flywheel 7단계(배포·테스트·학습 루프)의 뼈대: composite_signals.py 실행 결과를
JSON Lines로 누적 기록하고, 누적된 원시 근거치의 분포로 "1차 하드코딩" 임계치를
재보정할지 여부를 제안한다.

developer_evaluation_metrics.md의 여러 소항목이 "임계치는 1차로 하드코딩하고 추후
실측 데이터로 보정 필요"라고 명시해뒀는데, 지금까지는 실측을 쌓을 방법 자체가 없었다
(1회성 실행만 있었음). 이 모듈이 그 축적 메커니즘이다 — 아직 자동 재보정은 하지 않고,
"이 정도 데이터가 쌓이면 이런 재보정이 가능하다"는 제안만 출력한다(최종 결정은 사람이
문서를 고쳐야 반영됨 — 자동 조치 금지 원칙, 1.6절과 동일 정신).

기록되는 내용은 개인 원시 지표(커밋 수, 비율 등)뿐이며 코드/문서 본문은 포함하지
않는다 (developer_evaluation_metrics.md 7장 "소스코드 원본 유출 완전 차단" 원칙).

사용 예:
    python3 run_history.py --show  # 누적 이력 요약 + 재보정 제안 출력
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
from datetime import datetime, timezone

DEFAULT_HISTORY_PATH = os.path.expanduser("~/.cache/dev_metrics/composite_signals_history.jsonl")

# metric_key -> (표시명, "higher_is_bad" 여부, 현재 developer_evaluation_metrics.md에 적힌 1차 하드코딩 임계치)
METRIC_SPECS = {
    "quality.confirmed_refix_rate": ("품질: 확정적 재수정 비율", True, 0.15),
    "quality.failure_rate": ("품질: 변경 실패 신호 비율", True, 0.05),
    "velocity.lead_time_median_hours": ("속도: 리드 타임 중앙값(시간)", True, 120.0),
    "wellbeing.after_hours_pct": ("웰빙: 야간 커밋 비율(%)", True, 30.0),
    "wellbeing.weekend_pct": ("웰빙: 주말 커밋 비율(%)", True, 20.0),
}


def _derive_metrics(record: dict) -> dict[str, float]:
    """profile record의 evidence에서 METRIC_SPECS 키에 대응하는 값을 뽑아낸다."""
    metrics: dict[str, float] = {}
    categories = record.get("categories", {})  # {name: evidence_dict}

    quality_ev = next((ev for name, ev in categories.items() if name.startswith("1.")), None)
    if quality_ev and quality_ev.get("total_commits"):
        total = quality_ev["total_commits"]
        metrics["quality.confirmed_refix_rate"] = quality_ev.get("confirmed_refix_events", 0) / total
        failure_count = (
            quality_ev.get("revert_commits", 0)
            + quality_ev.get("hotfix_keyword_commits", 0)
            + quality_ev.get("hotfix_branches", 0)
        )
        metrics["quality.failure_rate"] = failure_count / total

    velocity_ev = next((ev for name, ev in categories.items() if name.startswith("2.")), None)
    if velocity_ev and "lead_time_median_hours" in velocity_ev:
        metrics["velocity.lead_time_median_hours"] = velocity_ev["lead_time_median_hours"]

    wellbeing_ev = next((ev for name, ev in categories.items() if name.startswith("5.")), None)
    if wellbeing_ev:
        if "after_hours_pct" in wellbeing_ev:
            metrics["wellbeing.after_hours_pct"] = wellbeing_ev["after_hours_pct"]
        if "weekend_pct" in wellbeing_ev:
            metrics["wellbeing.weekend_pct"] = wellbeing_ev["weekend_pct"]

    return metrics


def append_run(profile: dict, repo: str, author: str | None, history_path: str = DEFAULT_HISTORY_PATH) -> None:
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "repo": repo,
        "author": author,
        "categories": {name: ev for name, (band, ev) in profile["categories"].items()},
        "bands": {name: band for name, (band, ev) in profile["categories"].items()},
    }
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_history(history_path: str = DEFAULT_HISTORY_PATH) -> list[dict]:
    if not os.path.exists(history_path):
        return []
    records = []
    with open(history_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def suggest_recalibration(history: list[dict], min_samples: int = 5) -> list[dict]:
    """metric별로 누적 샘플이 min_samples 이상이면 75번째 백분위수 기반 재보정안을 제안."""
    values_by_metric: dict[str, list[float]] = {k: [] for k in METRIC_SPECS}
    for record in history:
        derived = _derive_metrics(record)
        for key, value in derived.items():
            values_by_metric[key].append(value)

    suggestions = []
    for key, (label, higher_is_bad, current_threshold) in METRIC_SPECS.items():
        values = values_by_metric[key]
        if len(values) < min_samples:
            suggestions.append(
                {
                    "metric": key, "label": label, "sample_count": len(values),
                    "status": "데이터 부족", "current_threshold": current_threshold,
                }
            )
            continue
        sorted_values = sorted(values)
        p75 = statistics.quantiles(sorted_values, n=4)[2] if len(sorted_values) >= 4 else sorted_values[-1]
        suggestions.append(
            {
                "metric": key, "label": label, "sample_count": len(values),
                "status": "재보정 가능", "current_threshold": current_threshold,
                "suggested_threshold_p75": round(p75, 3),
            }
        )
    return suggestions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history-file", default=DEFAULT_HISTORY_PATH, help="실행 이력 JSONL 경로")
    parser.add_argument("--show", action="store_true", help="누적 이력 요약과 재보정 제안을 출력")
    parser.add_argument("--min-samples", type=int, default=5, help="재보정을 제안할 최소 샘플 수 (기본 5)")
    args = parser.parse_args()

    if args.show:
        history = load_history(args.history_file)
        print(f"# 실행 이력 요약 ({args.history_file}, 총 {len(history)}회 실행 기록)\n")
        for r in history:
            print(f"  {r['timestamp']}  repo={r['repo']}  author={r.get('author')}  bands={r['bands']}")

        print("\n## 임계치 재보정 제안 (developer_evaluation_metrics.md의 '1차 하드코딩' 임계치 대상)\n")
        for s in suggest_recalibration(history, args.min_samples):
            if s["status"] == "데이터 부족":
                print(
                    f"  - {s['label']}: 샘플 {s['sample_count']}개(최소 {args.min_samples}개 필요) — "
                    f"현재 하드코딩값 {s['current_threshold']} 유지"
                )
            else:
                print(
                    f"  - {s['label']}: 샘플 {s['sample_count']}개 — 현재 {s['current_threshold']} vs "
                    f"실측 75번째 백분위 {s['suggested_threshold_p75']} "
                    f"(문서/스크립트 수정은 사람이 검토 후 반영)"
                )


if __name__ == "__main__":
    main()
