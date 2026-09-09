# Intent — AGILEDEV-1118: AI로 개발자 등급을 나눠보자

- Jira: http://jira.lge.com/issue/browse/AGILEDEV-1118
- 관련 티켓: Epic [AGILEDEV-279](http://jira.lge.com/issue/browse/AGILEDEV-279) ("adu-기타" — "어디에 속하지 않는 이것 저것", 내용상 특별한 컨텍스트 없음. 2026-09-09에 뒤늦게 연결됨)
- 담당/보고자: cheoljoo.lee, 상태: In Progress, 생성일 2026-09-03, Sprint: SW_QCD_Mgt_Unit 2026-09 (18s)

## 티켓 원문 (그대로 인용)

> **제목**: 개발시 누가 전문가일까요?  AI로 개발자 등급을 나눠보자.
>
> **본문**:
> 개발시 누가 전무가일까요?  AI로 개발자 등급을 나눠보자.
>
> ai  답변 : gerrit을 기준으로 얼마나 patchset이 한번에 만들어지는가?
>
> 추가로, 얼마나 많은 분야에서 활동을 많이 하고 있는가? 등..

**댓글 1** (2026-09-07 14:02): `https://github.com/cheoljoo/ai_resource_management/blob/main/developer_evaluation_metrics.md` (링크만)

**댓글 2** (2026-09-07 14:03): 이미지 첨부 — `developer_evaluation_metrics.md`의 "3. 시스템 메타데이터 실현 가능성 종합 매트릭스" 및 "3대 보완 솔루션" 절 스크린샷(초기 버전, `[O]/[△]/[X]` 분류 표). 이 티켓이 바로 이 저장소/이 문서를 가리키고 있음을 확인.

## 지금까지 한 일 (이 저장소 기준)

이 티켓과 직접 연결된 커밋은 없지만(`git log --grep AGILEDEV-1118` 결과 없음), 이 저장소 자체가 사실상
이 티켓에 대한 응답으로 이미 상당히 진행되어 있다:

- `developer_evaluation_metrics.md` — 5대 대항목(품질/속도/협업/문제정의/웰빙) + Goodhart's Law 경고 +
  `[O]/[△]/[X]` 자동화 가능 여부 + `Claude 직접 수집 가능 여부`(✅/🔑/❌/⏭️) 이중 분류 체계. 최근
  대화에서 크게 보강됨:
  - 1.1 "Patchset 수가 많으면 나쁘다"는 단정을 제거하고 "짧은 기간 집중(정상) vs 장기간 정체(주의)"로
    재해석 (사용자가 "2일 이내 여러 번 바뀌는 게 왜 문제냐"고 지적한 것을 반영).
  - 신규 1.5(REQ/SDD↔코드 매핑), 1.6(Reopen 횟수·재해결 속도), 1.7(테스트 충분성), 1.8(리뷰 피드백
    반영률), 1.9(변경 방식: 세밀 vs Bulk), 1.10(소스 내 설명/추적성 주석), 2.4(Jira 착수 리드타임·실제
    수행시간) 추가.
  - 3.1(코드 리뷰 기여도) 개정 — "의미있는 리뷰"를 라인단위 코멘트 비율·구체성·후속 스레드·반영률의
    4가지 관찰 가능 신호로 분해.
  - 6장(SMILE 플랫폼 활용 방안) 신설 — 사내에 이미 커밋/MR 단위 AI 코드 분석 플랫폼 **SMILE**
    (`https://smile.aise.lge.com`)이 존재하며, REQ/SDD 매핑·코드 리뷰 등급·테스트 검증을 이미 자동
    산출한다는 걸 확인. 다만 **이 프로젝트("VS")는 SMILE에 아직 등록돼 있지 않아** 지금 당장은 활용
    불가(별도 선행 작업 필요 — 이 intent의 범위 밖).
- `dev_metrics_code_map.md` — 위 문서의 `✅ 즉시 가능` 항목에 대응하는 실제 스크립트 매핑, SMILE 조사
  경과 기록.
- `scripts/dev_metrics/` — 로컬 git만으로 도는 스크립트 7종(`refix_frequency.py`, `lead_time.py`,
  `focus_time.py`, `burnout_signals.py`, `poc_branch_history.py`, `change_failure_signals.py`,
  `complexity.py`) + Gerrit/Jira 실 API 연동 스크립트(`gerrit_fetch.py`, `gerrit_metrics.py`,
  `jira_metrics.py`) — 전부 개별 지표를 "계산"만 하고, 이를 종합해 "등급"으로 만드는 단계는 아직 없음.
- `self_performance_report_2026-08.md` — 본인(cheoljoo.lee) 실측 데이터로 위 지표들을 검증한 리포트.
  각 지표값은 보여주지만 **역시 "등급"이나 "점수"로 종합하지는 않음** — 오히려 "인사 평가에 쓰지 말 것"을
  스스로 못박고 있음(문서 5장 원칙).
- 현재 `git status`상 `developer_evaluation_metrics.md`/`dev_metrics_code_map.md`가 아직 **커밋되지
  않은 상태**로 남아 있다(390줄 규모의 변경분).

## 이 intent에서 풀어야 할 것 (원문과 현재 구현 사이의 간극)

1. **"얼마나 많은 분야에서 활동하는가"(활동 폭/다양성) 지표가 문서에 없다.** 티켓 원문이 명시적으로
   요구한 두 가지(Patchset 수, 활동 분야의 폭) 중 Patchset 쪽은 1.1로 이미 다뤘지만, "여러 프로젝트/
   기술 영역에 걸친 활동 폭"을 재는 지표는 `developer_evaluation_metrics.md` 어디에도 아직 없다 —
   `self_performance_report_2026-08.md`에 "31개 프로젝트에 분산" 같은 원시 수치는 있지만 정식 지표로
   정의되지 않았다.
2. **"등급을 나눈다"는 원래 요청의 핵심 산출물이 아직 없다.** 지금까지는 개별 지표를 정의하고
   ([O]/[△]/[X], ✅/🔑/❌) 일부는 스크립트로 계산했지만, 이 지표들을 종합해서 실제로 "개발자를
   구분/등급화"하는 로직·산출물은 존재하지 않는다. 반면 문서 5장은 "인사 평가 직접 연동 금지"를 원칙으로
   못박고 있어, 원래 티켓의 "등급을 나누자"는 표현과 정면으로 충돌할 소지가 있다 — **이 간극을 어떻게
   풀지(리프레이밍 포함)가 이 intent의 핵심 판단 지점**이다.
3. Reopen 위험 등 티켓 원문에 없던 여러 신규 지표(1.5~1.10, 2.4)가 이미 설계돼 있으나, 실제 "등급 산출"
   로직에 이들을 어떻게 가중 결합할지는 아직 아무 결정도 없다.

## 제약/고려사항

- **Goodhart's Law 원칙(문서 1.2절)과 "인사 평가 직접 연동 금지"(문서 5장)를 반드시 준수** — 단일
  점수로 사람을 줄세우는 형태의 산출물을 만들면 안 된다. "등급"이라는 원래 티켓 표현을 그대로 구현할지,
  "다차원 프로필/병목 진단"으로 리프레이밍할지 사용자와 정렬이 필요할 수 있다.
- SMILE 연동은 이 프로젝트가 아직 SMILE에 미등록 상태라 이 intent 범위에서 다루지 않는다(별도 선행
  작업).
- 사내 Gerrit/Jira 실 데이터 조회는 `.env`의 자격증명(`GITLAB_TOKEN`, `LGEP_ID`/`LGEP_PASSWORD` 등)이
  필요하며, worktree에서 작업 시 7-1단계에서 심볼릭 링크된 `.env`를 그대로 쓸 수 있다.
- 동료(타인) 데이터를 다루게 될 경우 개인정보/거버넌스 이슈가 커지므로, 우선은 본인(cheoljoo.lee) 범위로
  검증하는 `self_performance_report_2026-08.md`와 같은 패턴을 유지하는 게 안전하다.
