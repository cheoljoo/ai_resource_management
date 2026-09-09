# 개발자 평가 메트릭 - 자동화 스크립트 매핑 (`scripts/dev_metrics/`)

[developer_evaluation_metrics.md](developer_evaluation_metrics.md)에서 **`✅ 즉시 가능`** (로컬 git 저장소만으로 코드가 바로 값을 산출할 수 있는 항목) 으로 표시된 소항목에 대해 실제 동작하는 Python 스크립트를 작성했다. 사내 Gerrit/Jira/Confluence/Teams API 연동이 필요한 `🔑 API 필요`, `❌ 불가` 항목은 이번에 코드화하지 않았다 (해당 시스템에 연결된 MCP/토큰이 없어 값을 가져올 수 없음).

모든 스크립트는 외부 패키지 없이 Python 표준 라이브러리와 `git` CLI만 사용하며, `--repo` 옵션으로 대상 저장소 경로를 지정해 **어떤 git 저장소에도** 재사용할 수 있다.

## 실행 방법

```bash
cd scripts/dev_metrics
python3 <script>.py --repo /path/to/target/repo [옵션들]
```

각 스크립트는 `python3 <script>.py --help`로 옵션을 확인할 수 있다.

## 코드 ↔ 문서 항목 매핑

| 문서 항목 | 스크립트 | Claude 직접 수집 가능 여부(문서 표기) | 무엇을 계산하는가 | 문서에 명시된 한계 |
| :--- | :--- | :--- | :--- | :--- |
| 1.2 단기 재수정(Re-fix) 빈도 | [refix_frequency.py](scripts/dev_metrics/refix_frequency.py) | ✅ 즉시 가능 (부분) | 파일별 커밋 이력을 시간순으로 정렬해, N일(기본 30일) 이내 재수정된 파일/커밋 쌍을 탐지. 커밋 메시지에 fix/bug/hotfix/issue 키워드가 있으면 "확정적 재작업"으로 구분 | Gerrit Change/Patchset 단위 메타데이터는 반영 못 함 (Gerrit API 필요) |
| 1.3 변경 실패율 (Hotfix/Revert) | [change_failure_signals.py](scripts/dev_metrics/change_failure_signals.py) | 🔑 API 필요 (부분 ✅) | `git revert` 커밋, hotfix/rollback 키워드 커밋, `hotfix/`·`revert-` 브랜치를 탐지 | 장애로 인한 롤백인지 기획 변경인지는 구분 불가 (Jira 장애 티켓 교차검증 필요) |
| 1.4 복잡도 대비 결함 밀도 | [complexity.py](scripts/dev_metrics/complexity.py) | 🔑 API 필요 (복잡도 산출만 ✅) | Python `ast` 모듈로 함수별 순환 복잡도(Cyclomatic Complexity)를 자체 계산 (SonarQube 등 외부 툴 불필요) | 실제 결함 수·도메인 난이도와 연결하려면 Jira 버그 데이터 필요. Python 파일만 지원 |
| 2.1 변경 리드 타임 | [lead_time.py](scripts/dev_metrics/lead_time.py) | ✅ 즉시 가능 (부분) | merge commit 기준으로, 병합된 브랜치의 가장 오래된 커밋 ~ merge 시각까지의 시간차를 계산 | Gerrit First-Upload 실제 시각 등은 Gerrit API 필요 |
| 2.2 몰입 시간 확보율 (Focus Time) | [focus_time.py](scripts/dev_metrics/focus_time.py) | ✅ Git 부분만 / ⏭️ Teams 제외 | 작성자별 커밋 타임스탬프 간격이 임계값(기본 120분) 이내면 하나의 Focus 세션으로 묶어 추정 몰입 시간 산출 (Inter-Event Gap 휴리스틱) | Teams 캘린더 기반 Inverse Calendar Block 분석은 범위 제외 |
| 4.1 선행 검증/PoC 수행 능력 | [poc_branch_history.py](scripts/dev_metrics/poc_branch_history.py) | ✅ 즉시 가능 (부분) | 브랜치별 최초/최근 커밋 시각, 커밋 수, base 브랜치 병합 여부 집계. `poc/`, `spike/`, `experiment/`, `prototype/` 접두사 브랜치를 PoC 후보로 표시 | Collab POC 보고서 존재 여부는 Confluence API 필요 |
| 5.1 번아웃 위험도 | [burnout_signals.py](scripts/dev_metrics/burnout_signals.py) | ✅ Git 부분만 / ⏭️ Teams 제외 | 작성자별 야간(기본 21시~07시)·주말 커밋 비율 집계 | Teams 회의 시간 합산은 범위 제외. 평가가 아닌 웰빙 케어 알림 용도로만 사용 |
| (공통 유틸) | [git_utils.py](scripts/dev_metrics/git_utils.py) | - | 위 스크립트들이 공유하는 `git log`/`git branch` 파싱 헬퍼 (`Commit` dataclass, `iter_commits`, `list_branches`, `default_branch`) | - |

## 코드화하지 않은 항목과 이유

문서에서 `🔑 API 필요`(수집 자체가 사내 API 필요) 또는 `❌ 불가`(정성적 판단 영역)로 표기된 항목은 이번에 스크립트를 만들지 않았다:

* **1.1 패치셋 패턴, 2.3 WIP 관리, 3.2 지식 자산화** — Gerrit/Jira/Confluence REST API 및 인증 토큰이 있어야 값을 가져올 수 있음.
* **3.1 코드 리뷰 기여도** — 리뷰 코멘트 원문 자체를 Gerrit API로 가져와야 함 (원문만 확보되면 이후 LLM 시맨틱 분류는 가능).
* **3.3 블로커 해결/멘토링, 4.2 요구사항 분석, 4.3 오버엔지니어링 지양** — 정성적 판단 영역이라 애초에 코드/API로 산출 불가.
* **5.2 주도적 개선(Post-mortem)** — Collab/Jira API 필요.

## 3차 작업: Gerrit 리뷰/코드 품질 심화 항목 (2026-09-07 반영, 스크립트 미작성)

사용자 피드백("Gerrit 하나를 보더라도 리뷰 내용·Patchset 간격·REQ/SDD 매핑·Bulk 여부·코드 내 설명까지
봐야 진짜 일을 제대로 하는지 알 수 있다")을 반영해 [developer_evaluation_metrics.md](developer_evaluation_metrics.md)에
1.5(개정)·1.8·1.9·1.10, 3.1(개정)을 추가/보강했다. 이번에는 **문서만 갱신**했고 스크립트는 아직 작성하지
않았다 — 항목별 착수 우선순위와 이유는 아래와 같다:

| 문서 항목 | Claude 직접 수집 가능 여부(문서 표기) | 스크립트화 난이도 | 비고 |
| :--- | :--- | :--- | :--- |
| 1.9 변경 방식(세밀 vs Bulk) | ✅ 즉시 가능 | **낮음** — 로컬 git diff의 hunk 개수/블록 크기 분포만 있으면 됨. 기존 `refix_frequency.py`와 유사하게 `git diff`/`git show` 파싱으로 바로 구현 가능 | **가장 먼저 스크립트화할 후보** |
| 1.10 소스 내 설명/추적성 주석 | ✅ 즉시 가능 | **낮음** — diff에서 추가된 라인 중 주석 비율, 정규식(`AGILEDEV-\d+` 등) 매칭은 표준 라이브러리만으로 구현 가능 | 1.9와 함께 스크립트화 용이 |
| 1.5 REQ/SDD↔코드 매핑 | 🔑 수집(Jira/Confluence API) / ✅ 매칭분석(LLM) | **중간** — 문서 원문 수집은 API 필요하지만, 일단 REQ/SDD 텍스트와 diff를 파일로 준비해주면 매칭 자체는 스크립트가 아니라 Claude가 그 자리에서 직접 분석 가능(별도 파이썬 스크립트 불필요) | 자동화 대상이 "스크립트"가 아니라 "LLM 프롬프트"에 가까움 |
| 1.8 리뷰 피드백 반영률 | 🔑 수집(Gerrit API) / ✅ 반영분석 | **중간** — Gerrit 코멘트+Patchset diff를 JSON으로 확보하면(`gerrit_fetch.py` 확장), 코멘트 위치와 다음 Patchset diff를 대조하는 로직은 스크립트화 가능. "취지가 반영됐는지"의 최종 판단은 LLM 보조 필요 | `gerrit_fetch.py`에 코멘트 조회 기능 추가가 선행 조건 |
| 3.1 코드 리뷰 기여도(개정) | 🔑 수집 / ✅ 분석 | 위 1.8과 동일 선행 조건 | 라인단위 코멘트 비율·구체성 판별은 코멘트 원문 확보 후 LLM으로 |

## 4차 작업: SMILE 플랫폼 발견 — 1.5/1.7/3.1의 스크립트화 계획 보류 (2026-09-07)

Collab SAAD 스페이스의 [SMILE User Guide](http://collab.lge.com/main/spaces/SAAD/pages/3800498513/)와
[Release Notes](http://collab.lge.com/main/spaces/SAAD/pages/3815244051/)(v1.0.0-preview, 2026-09-04)를
원문으로 확인한 결과, 사내에 이미 **SMILE**(커밋/MR 단위 AI 코드 변경 영향 분석 플랫폼)이 존재하며
Requirement 추적(PRD/SRS/FBS/UI 자동 매칭), Code Review(Critical/Warning/Info 등급), Unit/System Test
자동 생성·검증(Pass/Fail/Unverified/Out of Scope/Existing Coverage)을 이미 제공하고 있음을 확인했다.

이에 따라 바로 위 "3차 작업"에서 **1.5(REQ/SDD 매핑)·1.7(테스트 충분성)·3.1(코드 리뷰 기여도)를 커스텀
스크립트/LLM 프롬프트로 직접 구현하려던 계획은 보류**한다 — SMILE이 이미 같은 결과를 구조화된 형태로
산출하고 있다면, 직접 만드는 대신 SMILE의 API(`POST /api/analyses` 등, API Key + curl 연동)를 통해 그
결과를 가져오는 것이 우선순위가 높다. 자세한 배경은 [developer_evaluation_metrics.md 6장](developer_evaluation_metrics.md#6-smile-플랫폼-활용-방안-2026-09-신규-반영) 참고.

**다음 단계로 확인이 필요한 것** (아직 스크립트/연동 작업 착수 전):

1. ✅ **[절차 확인, 2026-09-07]** SMILE API Key 발급 절차 확인 완료 — [API 기반 분석 연동](http://collab.lge.com/main/spaces/SAAD/pages/3789454123/)
   원문을 조회함. 절차: SMILE 웹 UI 로그인 → 설정 → `API Keys` → 이름/만료 지정 → 발급 → 평문 키(`smile_...`)를
   **그 순간에만** 복사 가능. 추가로 계정에 **SAVE Key**가 선등록돼 있어야 하며(`설정 → 연동 API Keys`),
   없으면 모든 요청이 `400 save_key_required`로 거부됨. 자세한 내용은
   [developer_evaluation_metrics.md 6.4](developer_evaluation_metrics.md#64-api-key-발급-절차-2026-09-07-확인--api-기반-분석-연동-원문) 참고.
   * **🚧 [시도, 2026-09-07 16:xx KST] 실제 발급 시도 — SMILE 점검 중으로 중단.** `../headless-browser-with-ai`의
     `scripts/steel_browser.sh`(self-host Steel Docker, CDP로 AI가 DOM 조작)로 `https://smile.aise.lge.com`을
     열고, `.env`의 `LGEP_ID`/`LGEP_PASSWORD`로 SEL SSO(Keycloak, `sso.sel.lge.com`) 로그인 폼(`#username`,
     `#password`, `#kc-login`)을 채워 제출 → **로그인 자체는 성공**(SMILE 홈으로 리다이렉트, 우측 상단에
     로그인 사용자 아바타 표시됨). 다만 SMILE이 **서비스 점검 중**(점검 시작 2026-09-08 01:30 ~ 종료
     2026-09-08 08:59, 한국시)이라 설정 화면에 진입할 수 없어 API Key 발급까지는 못 감. 컨테이너는 정리
     (`stop`)했음 — **점검 종료(2026-09-08 09시 이후) 후 같은 절차로 재시도 필요**.
   * **확인된 것**: 이 SSO는 표준 Keycloak 로그인 폼이라 자격증명만 있으면 브라우저 자동화(CDP)로 로그인
     자체는 문제없이 통과된다. 즉 "Claude가 로그인은 절대 못 한다"는 이전 판단은 **틀렸음** — 로그인은
     자동화 가능했고, 이번에 막힌 것은 순전히 SMILE 서비스 자체의 점검 스케줄 때문.
   * **비밀번호 노출 방지**: 스크립트(`sso_login.py`)는 `.env`에서 읽은 비밀번호를 CDP `Runtime.evaluate`
     파라미터로만 전달했고, 어떤 로그·스크린샷·파일에도 평문으로 남기지 않았다(스크린샷은 로그인 완료
     후의 화면만 캡처).
2. SMILE API로 **과거 이력(본인이 이미 작업한 커밋/MR)까지 소급 조회**가 가능한지, 아니면 신규 분석
   요청만 가능한지 — 확인된 `POST /api/analyses`는 두 리비전(base/change) 간 diff를 **그때그때 새로
   생성**하는 방식이라, 이미 분석된 적 없는 과거 커밋은 소급 분석 시 비용/시간이 다시 든다. 목록 조회
   (listing analyses) 엔드포인트가 있다는 언급은 있으나 상세 스펙은 이번 페이지에 없어 **여전히 미확인**
   — 실제 키를 받으면 1건 시험 호출로 확인.
3. 🔴 **[확인 완료, 2026-09-08 — 결과: 미등록]** 이 저장소(`ai_resource_management`)를 포함해 실제 분석
   대상 저장소들이 SMILE `Project Settings`에 PRD/SRS/FBS/UI/Test Case 문서 링크와 함께 등록되어 있는지
   확인한 결과, **"VS" 프로젝트용으로 SMILE에 아무것도 설정된 것이 없다**(사용자 확인). 즉 지금 시점에는
   SMILE을 통한 1.5/1.7/3.1 대체·보강이 **적용 불가** — 등록(저장소 연결 + 문서 링크 등록)이 선행돼야
   하며, 그 전까지는 기존 커스텀 방식(1.5/1.7/3.1의 로컬 git/LLM 기반 접근)을 그대로 써야 한다. 이 항목이
   이번 SMILE 조사에서 **가장 중요한 결론**이다 — API Key를 발급받는다 해도 프로젝트 미등록 상태면 의미
   있는 분석 결과를 가져올 수 없다.
4. 위 3번의 등록 작업이 끝나면 `scripts/dev_metrics/smile_fetch.py`(가칭)를 `gerrit_fetch.py`와 같은
   패턴으로 추가해, SMILE 분석 결과 JSON을 1.5/1.7/3.1 지표로 변환하는 스크립트를 작성한다.

**1.9(변경 방식 세밀 vs Bulk), 1.10(소스 내 추적성 주석)은 SMILE과 무관하게 여전히 로컬 git만으로 즉시
스크립트화 가능**하므로 이 계획에 영향받지 않는다 — 우선순위 그대로 유지.

## 검증 방법

각 스크립트는 이 저장소([ai_resource_management](.))와 히스토리가 풍부한 외부 저장소(`yt-dlp`)를 대상으로 실행해 정상 동작을 확인했다. 예:

```bash
python3 scripts/dev_metrics/lead_time.py --repo /path/to/yt-dlp --top 5
python3 scripts/dev_metrics/complexity.py --path /path/to/yt-dlp/yt_dlp/utils
```

## 추가 (2차 작업): Gerrit/Jira API 연동 스크립트 — 실제 사내 시스템 데이터로 검증 완료

위 "코드화하지 않은 항목"의 일부(1.1 재작업률, 2.1 리드 타임의 Gerrit 시각, Jira 이슈 분포 등)를 실제 사내 Gerrit/Jira REST API로 조회하는 스크립트를 추가로 작성하고, 본인(cheoljoo.lee) 계정 범위로 실행해 실제 값이 정상적으로 반환되는지 확인했다. 결과와 재현 방법은 [self_performance_report_2026-08.md](self_performance_report_2026-08.md) 참고.

* [scripts/dev_metrics/gerrit_fetch.py](scripts/dev_metrics/gerrit_fetch.py) — 여러 Gerrit 서버(`~/code/ccr/global_variables.py`의 자격증명, 저장소에는 포함되지 않음)에서 `owner:` 기준으로 Change 목록을 페이지네이션 조회. 자격증명은 리포지토리 밖 파일에서 동적으로 로드하며 하드코딩하지 않음.
* [scripts/dev_metrics/gerrit_metrics.py](scripts/dev_metrics/gerrit_metrics.py) — `gerrit_fetch.py` 결과 JSON을 입력받아 1.1 재작업률(Patchset 수 분포), 상태 분포, 2.1 리드 타임(Gerrit `created`~`updated`), 변경 규모, 프로젝트별 분포를 계산.
* [scripts/dev_metrics/jira_metrics.py](scripts/dev_metrics/jira_metrics.py) — 기존 `~/code/_worklog` 도구로 수집한 Jira CSV를 입력받아 상태/이슈타입/우선순위 분포와 월별 추이를 계산.
* `focus_time.py`, `burnout_signals.py`에 `--author` 옵션을 추가해 특정 작성자로 범위를 좁혀 자기 진단 목적으로 사용할 수 있게 함.
