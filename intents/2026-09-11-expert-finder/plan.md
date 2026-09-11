# Plan — AGILEDEV-1132

**상태**: 착수 전 확인 완료(2026-09-11). 실제 구현 착수 단계.

## 착수 전 확인 — 완료 (2026-09-11 `AskUserQuestion`으로 정렬)

- [x] **베이스 브랜치** → `main`으로 확정. 기존 worktree(`intent/2026-09-09-developer-expertise-grading`
      기반)를 제거하고 `main`(`a66db81`) 기준으로 재생성 완료(`intent/2026-09-11-expert-finder`).
      `.env` 심볼릭 링크도 재연결 완료.
- [x] **접근 방식** → spec.md A+B+C 전부 + 5개 데이터 소스(사내 git/GitHub/Gerrit/Jira/Confluence)
      결합으로 확정. 상세는 `intent.md`/`spec.md` 참고.
- [x] **AGILEDEV-1118과의 관계** → 나머지 부분(Recognition/Warning Signal)은 신경 쓰지 않음으로 확정.
- [x] **접근 경로 확정**: git=로컬 clone, Jira/Confluence=`mcp-atlassian` MCP, GitHub=`gh` CLI(인증 완료
      확인), Gerrit=`~/code/ccr/gerrit/global_variables.py` 자격증명 재사용.
- [x] **거버넌스 확장 승인**: Gerrit/Jira 동료(타인) 데이터 수집을 라우팅 목적 한정으로 승인받음
      (spec.md "거버넌스 확장" 절 참고). 성과평가·개인 비교 전용은 여전히 금지.
- [x] `scripts/dev_metrics/`에 main 기준으로 무엇이 있고 없는지 확인 — `gerrit_metrics.py`/
      `jira_metrics.py`/`git_utils.py` 등은 main에 이미 존재, `expert_finder.py`/`experience_atoms.py`/
      `monthly_activity_clusters.py`는 main에 없어 **새로 작성 필요**.
- [x] 검증용 다중 기여자 저장소 후보 스캔 완료 — 최근 14일 기준 `pvs_crawler`(4명)·`sage-wiki`(3명)가
      활성 후보, 60일로 넓히면 `my-llm-wiki`(2명) 등 추가.

## 단계별 체크리스트 (main 기준으로 갱신)

### 1. 설계
- [ ] git/Gerrit/Jira/Confluence/GitHub 5개 신호를 어떤 단위(모듈? 프로젝트? 사람?)로 결합해 "전문가"를
      산출할지 스키마를 먼저 정의한다 — 완료조건 1·4번의 전제.
- [ ] 여러 저장소를 합쳐 ~20명 규모를 채울 구체적 저장소 조합을 확정한다(`pvs_crawler` + `sage-wiki` +
      필요시 추가).

### 2. 구현 (main 기준 새로 작성)
- [ ] `experience_atoms.py` 재작성 — Mockus & Herbsleb EA 방법(모듈/기술/목적 3축, breadth/depth).
- [ ] `expert_finder.py` 재작성 — 전체 기여자 대상 (모듈, 기여자)별 EA 집계 + 랭킹, `--since-days`
      옵션화(기본값과 근거를 코드 주석/문서에 명시) — 완료조건 2번.
- [ ] Gerrit 신호 결합 — `gerrit_fetch.py`의 owner 제한을 라우팅 목적으로 완화해 리뷰 활동 신호 추가.
- [ ] Jira 신호 결합 — `mcp-atlassian`(`jira_search` 등)으로 이슈 처리 이력 신호 추가(로컬 CSV
      파이프라인이 아니라 MCP 직접 조회).
- [ ] Confluence 신호 결합 — `mcp-atlassian`(`confluence_search` 등)으로 문서 기여/편집 이력 신호 추가.
- [ ] GitHub 신호 결합 — `gh` CLI로 PR/이슈/커밋 메타데이터 신호 추가.
- [ ] 5개 신호를 사람 단위로 합산하는 결합 로직 작성(가중치/정규화 방식을 문서에 근거와 함께 기록).
- [ ] 정성적 평가가 섞여 있지 않은지 최종 점검 — 완료조건 1번.

### 3. 검증 실행
- [ ] 여러 저장소를 합쳐 총 ~20명 규모로 실제 실행 결과를 만들고, "회사 안의 어떤 사람들이 전문가인지"에
      답하는 출력 예시를 확보한다 — 완료조건 3·4번.

### 4. 문서화
- [ ] `developer_evaluation_metrics.md` 6.6절 갱신(또는 spec.md C안에 따라 `expert_finder.md`로 분리) —
      완료조건 5번. 거버넌스 확장 사실을 반드시 명시.
- [ ] `dev_metrics_code_map.md` 매핑 표 갱신 — 완료조건 6번.

### 5. Jira 갱신
- [ ] AGILEDEV-1132에 진행 요약 댓글 게시(사용자 확인 후) — 완료조건 7번.
- [ ] 필요하면 AGILEDEV-1118과의 관계(독립 범위임)도 댓글에 함께 남긴다.

이 저장소는 `/wiki-log`로 llm_wiki 중앙 저장소에 세션 로그를 남기는 관례를 쓴다 — 작업 완료 후
`/wiki-log` 실행을 잊지 않는다.
