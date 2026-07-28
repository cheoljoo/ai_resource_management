# Gerrit Re-fix 탐지 설계

## 개요

100개의 서로 다른 Gerrit change(모두 Merged) 중에서, **동일한 함수/코드 영역이 여러 번 수정된 것**을 탐지하는 방법을 정리한다.  
즉, "A 함수를 고쳤는데 이후에 다시 A 함수를 고쳤다" → **re-fix 패턴**을 자동으로 발견하는 것이 목표다.

---

## 핵심 아이디어: diff hunk 헤더 파싱

Git/Gerrit diff의 hunk 헤더에는 변경된 **함수 이름**이 포함된다:

```diff
@@ -120,8 +120,12 @@ int calculateTimeout(int retries)
```

이 `@@` 컨텍스트를 파싱하면 **"어떤 파일의 어떤 함수"**가 수정되었는지 추출할 수 있다.

### 핵심 정규식

```python
import re

HUNK_CTX = re.compile(r'^@@[^@]+@@\s*(.+)$', re.MULTILINE)
# 매칭된 그룹에서 함수 시그니처 추출
```

---

## 저장 데이터 구조

### 테이블 설계

```
(file_path, function_name) → [(gerrit_id, merged_at), ...]
```

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `gerrit_id` | str | Gerrit change ID (예: `12345`) |
| `file_path` | str | repo root 기준 상대 경로 |
| `function_name` | str | `@@` 헤더에서 추출한 함수 이름 (정규화) |
| `merged_at` | datetime | Merge된 시각 |

### 예시 데이터

| gerrit_id | file_path | function_name | merged_at |
|-----------|-----------|---------------|-----------|
| 12345 | src/net/tcp.c | `tcp_connect` | 2026-01-10 |
| 12389 | src/net/tcp.c | `tcp_connect` | 2026-01-18 |
| 12401 | src/net/tcp.c | `tcp_connect` | 2026-02-03 |

위처럼 `tcp_connect`가 3번 수정되었음 → **re-fix 후보**.

---

## 탐지 쿼리

```sql
SELECT file_path, function_name,
       COUNT(*) AS fix_count,
       MIN(merged_at) AS first_fix,
       MAX(merged_at) AS last_fix,
       GROUP_CONCAT(gerrit_id ORDER BY merged_at) AS gerrit_sequence
FROM function_changes
GROUP BY file_path, function_name
HAVING COUNT(*) >= 2
   AND DATEDIFF(MAX(merged_at), MIN(merged_at)) <= 90  -- 90일 이내 재수정만
ORDER BY fix_count DESC, last_fix DESC;
```

> `DATEDIFF` 조건으로 **시간 창(time window)** 을 좁혀 정상적인 기능 발전(years 단위)과 re-fix를 구분한다.

---

## 파이프라인 흐름

```
Gerrit API          diff 파싱            정규화 저장           분석
(merged changes) → (@@ 헤더 추출) → (file+function → DB) → (GROUP BY → re-fix 목록)
```

### Gerrit REST API 엔드포인트

```
GET /changes/{change-id}/revisions/current/files/{file-path}/diff
```

응답의 `content` 배열에서 `@@` 패턴을 파싱한다.

---

## 인덱스 전략

```sql
-- 빠른 GROUP BY를 위한 복합 인덱스
CREATE INDEX idx_file_func ON function_changes(file_path, function_name, merged_at);
```

---

## 함수명 정규화 주의사항

| 항목 | 처리 방법 |
|------|-----------|
| 대소문자 | 소문자로 통일 |
| 공백/탭 | 제거 |
| 파일 경로 | repo root 기준 상대 경로로 통일 |
| 익명 함수/람다 | `파일명:라인번호범위` 로 대체 |
| 함수 rename | git similarity 또는 별도 추적 필요 |

---

## 방법별 비교

| 방법 | 정확도 | 구현 복잡도 | 비고 |
|------|--------|-------------|------|
| `@@` 헤더 파싱 | 중 | **낮음 ✅** | C/C++/Java 양호, Python 불안정 |
| AST diff (tree-sitter 등) | 높음 | 높음 | 언어별 파서 필요 |
| 라인 범위 오버랩 | 낮음 | 중간 | 라인 이동으로 오탐 많음 |
| 토큰/라인 유사도 (MinHash) | 높음 | 매우 높음 | fuzzy 매칭 |

**권장**: `@@` 헤더 파싱으로 시작 → 필요 시 AST diff로 고도화.

---

## Python 구현 스케치

```python
import re
import requests
from datetime import datetime

HUNK_FUNC = re.compile(r'^@@[^@]+@@\s*(.+)$', re.MULTILINE)

def extract_functions_from_diff(diff_text: str) -> list[str]:
    """diff 텍스트에서 변경된 함수 이름 목록을 추출."""
    matches = HUNK_FUNC.findall(diff_text)
    funcs = []
    for m in matches:
        # 함수 시그니처에서 이름만 추출 (첫 번째 단어 또는 괄호 앞)
        name = m.strip().split("(")[0].strip().split()[-1] if m.strip() else ""
        if name:
            funcs.append(name.lower())
    return list(set(funcs))


def fetch_diff_for_change(gerrit_url: str, change_id: str, auth) -> dict[str, list[str]]:
    """Gerrit change의 파일별 변경 함수 목록 반환.
    반환: {file_path: [function_name, ...]}
    """
    # 1) 변경된 파일 목록 조회
    files_url = f"{gerrit_url}/changes/{change_id}/revisions/current/files"
    files_resp = requests.get(files_url, auth=auth)
    files_resp.raise_for_status()
    # Gerrit REST API는 응답 앞에 ")]}'" 가 붙으므로 제거
    files_data = files_resp.text.lstrip(")]}'\\n")
    import json
    files = json.loads(files_data)

    result: dict[str, list[str]] = {}
    for file_path in files:
        if file_path == "/COMMIT_MSG":
            continue
        diff_url = f"{gerrit_url}/changes/{change_id}/revisions/current/files/{requests.utils.quote(file_path, safe='')}/diff"
        diff_resp = requests.get(diff_url, auth=auth)
        if diff_resp.status_code != 200:
            continue
        diff_text = diff_resp.text.lstrip(")]}'\\n")
        diff_obj = json.loads(diff_text)
        # diff content를 텍스트로 재조합
        raw_diff = "\n".join(
            seg.get("ab", seg.get("b", [""]))[0] if seg.get("ab") or seg.get("b") else ""
            for seg in diff_obj.get("content", [])
        )
        funcs = extract_functions_from_diff(raw_diff)
        if funcs:
            result[file_path] = funcs
    return result


def index_merged_changes(gerrit_url: str, change_ids: list[str], auth, db_cursor) -> None:
    """Merged change 목록을 순회하며 function_changes 테이블에 색인."""
    for change_id in change_ids:
        # merged_at 조회
        info_url = f"{gerrit_url}/changes/{change_id}?o=DETAILED_LABELS"
        info = requests.get(info_url, auth=auth).json()
        merged_at = info.get("submitted", "")[:19]  # "YYYY-MM-DD HH:MM:SS"

        file_funcs = fetch_diff_for_change(gerrit_url, change_id, auth)
        for file_path, funcs in file_funcs.items():
            for func_name in funcs:
                db_cursor.execute(
                    "INSERT INTO function_changes (gerrit_id, file_path, function_name, merged_at) VALUES (?, ?, ?, ?)",
                    (change_id, file_path, func_name, merged_at),
                )


def find_refix_candidates(db_cursor, window_days: int = 90, min_count: int = 2) -> list[dict]:
    """re-fix 후보 목록 반환."""
    db_cursor.execute("""
        SELECT file_path, function_name,
               COUNT(*) AS fix_count,
               MIN(merged_at) AS first_fix,
               MAX(merged_at) AS last_fix,
               GROUP_CONCAT(gerrit_id) AS gerrit_sequence
        FROM function_changes
        GROUP BY file_path, function_name
        HAVING COUNT(*) >= ?
           AND JULIANDAY(MAX(merged_at)) - JULIANDAY(MIN(merged_at)) <= ?
        ORDER BY fix_count DESC, last_fix DESC
    """, (min_count, window_days))
    cols = [d[0] for d in db_cursor.description]
    return [dict(zip(cols, row)) for row in db_cursor.fetchall()]
```

---

## 출력 예시

```
[re-fix 후보]
file_path              function_name    fix_count  first_fix    last_fix     gerrit_sequence
---------------------  ---------------  ---------  -----------  -----------  ---------------
src/net/tcp.c          tcp_connect              3  2026-01-10   2026-02-03   12345,12389,12401
src/auth/session.cpp   validate_token           2  2026-01-15   2026-01-28   12350,12380
```

---

## 확장 아이디어

- **Negative review 연계**: 이미 수집 중인 `gerrit_code_change_after_negative_review.json` 데이터와 결합하여 "부정 리뷰 이후 re-fix" 패턴 분석 가능
- **시간 창 조정**: `window_days` 파라미터로 단기(30일) / 중기(90일) / 장기(365일) re-fix 분류
- **담당자 분석**: `author` 필드 추가로 "같은 사람이 두 번 고쳤는지" vs "다른 사람이 수정했는지" 구분
- **LLM 연계**: re-fix된 함수에 대해 LLM으로 "왜 다시 고쳤는지" 자동 요약 생성

---

# 매일 활동 추적 (Daily Activity Tracking)

## Merged 추적 vs 매일 활동 추적 비교

Merged만 보면 **결과**만 보이고, 매일 활동 추적은 **과정** 전체를 볼 수 있다.

| 대상 | Merged 추적 | 매일 활동 추적 |
|------|-------------|--------------|
| 범위 | 최종 완료만 | 진행 중 + 완료 + abandon |
| 이벤트 | merge 1회 | upload / patchset 추가 / comment / review / merge |
| 활동 주체 | author | author + reviewer + commenter |

---

## Gerrit REST API — 일별 수집 쿼리

### 기본 일별 변경 조회

```
GET /changes/?q=after:2026-07-15+before:2026-07-16&o=DETAILED_ACCOUNTS&o=MESSAGES&o=DETAILED_LABELS&n=500
```

Gerrit 쿼리 연산자 조합:

```
# 특정 날 업로드된 모든 change
after:2026-07-15 before:2026-07-16

# 특정 사람의 활동
owner:alice@company.com after:2026-07-15

# 특정 사람이 리뷰한 것
reviewer:bob@company.com after:2026-07-15

# 특정 날 patchset이 추가된 것 (재작업 감지)
after:2026-07-15 before:2026-07-16 -age:1d
```

### Python으로 일별 수집

```python
from datetime import date, timedelta
import requests, json

def fetch_daily_changes(gerrit_url: str, auth, target_date: date) -> list[dict]:
    d_str   = target_date.strftime("%Y-%m-%d")
    d_next  = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")
    query   = f"after:{d_str} before:{d_next}"
    options = ["DETAILED_ACCOUNTS", "MESSAGES", "DETAILED_LABELS",
               "CURRENT_FILES", "CURRENT_REVISION"]
    params  = {"q": query, "n": 500}
    for o in options:
        params["o"] = o   # 실제로는 &o=A&o=B 형태로 반복

    url  = f"{gerrit_url}/changes/"
    resp = requests.get(url, params=params, auth=auth)
    raw  = resp.text.lstrip(")]}'\\n")
    return json.loads(raw)
```

---

## 수집해야 할 이벤트 종류

```
change 1건당 발생하는 이벤트들:
┌─────────────────────────────────────────────────────┐
│ change_id │ event_type     │ actor  │ timestamp      │
├───────────┼────────────────┼────────┼────────────────┤
│ 12345     │ UPLOADED       │ alice  │ 2026-07-15 09  │  ← 최초 upload
│ 12345     │ PATCHSET_ADDED │ alice  │ 2026-07-15 14  │  ← 수정 후 재업로드
│ 12345     │ COMMENT        │ bob    │ 2026-07-15 15  │  ← 리뷰 코멘트
│ 12345     │ VOTE           │ bob    │ 2026-07-15 15  │  ← Code-Review +2
│ 12345     │ MERGED         │ system │ 2026-07-15 16  │  ← merge
└─────────────────────────────────────────────────────┘
```

`messages` 배열에서 위 이벤트들을 파싱:

```python
def parse_events(change: dict) -> list[dict]:
    events = []
    change_id  = change["id"]
    author     = change.get("owner", {}).get("email", "?")
    created_at = change.get("created", "")

    # 1) 최초 upload
    events.append({"change_id": change_id, "actor": author,
                   "event": "UPLOADED", "ts": created_at})

    # 2) messages에서 patchset / comment / vote 분리
    for msg in change.get("messages", []):
        actor = msg.get("author", {}).get("email", "?")
        text  = msg.get("message", "")
        ts    = msg.get("date", "")

        if text.startswith("Uploaded patch set"):
            events.append({"change_id": change_id, "actor": actor,
                           "event": "PATCHSET_ADDED", "ts": ts, "detail": text})
        elif "Code-Review" in text or "Verified" in text:
            events.append({"change_id": change_id, "actor": actor,
                           "event": "VOTE", "ts": ts, "detail": text})
        elif text.strip():
            events.append({"change_id": change_id, "actor": actor,
                           "event": "COMMENT", "ts": ts, "detail": text[:200]})

    # 3) merge 여부
    if change.get("status") == "MERGED":
        events.append({"change_id": change_id, "actor": author,
                       "event": "MERGED", "ts": change.get("submitted", "")})
    return events
```

---

## 개인별 분석 — 효율적인 쿼리 패턴

### (A) 개인 일별 활동량

```sql
SELECT actor,
       DATE(ts) AS work_date,
       SUM(event = 'UPLOADED')       AS uploads,
       SUM(event = 'PATCHSET_ADDED') AS reworks,
       SUM(event = 'COMMENT')        AS comments,
       SUM(event = 'VOTE')           AS reviews,
       SUM(event = 'MERGED')         AS merges
FROM daily_events
WHERE work_date >= '2026-07-01'
GROUP BY actor, work_date
ORDER BY actor, work_date;
```

### (B) 재작업률 (patchset 수 = 품질 지표)

```sql
-- patchset 2개 이상 = 한 번 이상 수정한 change
SELECT author_email,
       COUNT(*)                                              AS total_changes,
       SUM(patchset_count >= 2)                             AS reworked,
       ROUND(AVG(patchset_count), 1)                        AS avg_patchsets,
       ROUND(SUM(patchset_count >= 2) * 100.0 / COUNT(*), 1) AS rework_rate_pct
FROM (
    SELECT author_email, change_id, COUNT(*) AS patchset_count
    FROM daily_events
    WHERE event IN ('UPLOADED', 'PATCHSET_ADDED')
    GROUP BY author_email, change_id
)
GROUP BY author_email
ORDER BY rework_rate_pct DESC;
```

### (C) 리뷰 기여도 (누가 얼마나 리뷰했나)

```sql
SELECT actor,
       COUNT(DISTINCT change_id) AS changes_reviewed,
       COUNT(*)                  AS total_comments
FROM daily_events
WHERE event IN ('COMMENT', 'VOTE')
  AND actor != (SELECT owner FROM changes WHERE changes.id = daily_events.change_id)
GROUP BY actor
ORDER BY changes_reviewed DESC;
```

### (D) 어떤 파일/모듈을 작업했나

```sql
SELECT e.actor,
       DATE(e.ts) AS work_date,
       f.file_path,
       COUNT(*)   AS touch_count
FROM daily_events e
JOIN change_files f ON e.change_id = f.change_id
WHERE e.event = 'UPLOADED'
GROUP BY e.actor, work_date, f.file_path
ORDER BY e.actor, work_date, touch_count DESC;
```

---

## 개인 활동 요약 — 종합 대시보드 개념

```
[2026-07-15 활동 요약]
─────────────────────────────────────────────────────
alice@company.com
  업로드    : 3건  (src/net/tcp.c, src/auth/login.cpp, tests/test_tcp.py)
  재작업    : 1건  (12345 → patchset 3회)
  리뷰      : 0건
  모듈      : net, auth, tests

bob@company.com
  업로드    : 1건  (src/storage/cache.cpp)
  재작업    : 0건
  리뷰      : 5건  (12345, 12350, 12360, 12370, 12380)
  코멘트    : 12건
  역할      : 주로 리뷰어
─────────────────────────────────────────────────────
```

---

## 핵심 지표 정리

| 지표 | 측정 방법 | 의미 |
|------|-----------|------|
| **upload 수** | `UPLOADED` 이벤트 집계 | 새 작업 시작량 |
| **patchset 수** | `PATCHSET_ADDED` 집계 | 재작업 빈도 (높을수록 초기 품질 낮음) |
| **리뷰 참여 수** | `VOTE/COMMENT` 집계 | 팀 기여도 |
| **merge까지 시간** | `UPLOADED`→`MERGED` 시간 차 | 리뷰 속도 |
| **touch한 파일/모듈** | `change_files` JOIN | 담당 영역 |
| **re-fix 관여** | 동일 함수 반복 수정 | 불안정 코드 담당 여부 |
