# MR·PR 메타데이터 취합

실행·의존성 설치·테스트는 모두 `uv`를 사용한다. Python 3.11 이상이 필요하다.
GitLab은 [gitlab_signal.py](gitlab_signal.py), GitHub는 [github_signal.py](github_signal.py)가 담당한다.

## 실행과 인증

[Makefile](Makefile)이 있는 디렉터리에서 `make mr-pr`을 실행하면 지정된 사내 GitLab
프로젝트를 수집한다. `make mr-pr GITHUB_REPOS='owner/repo'`는 GitHub도 수집한다.
`make combine GITHUB_REPOS='owner/repo'`로 두 결과를 결합 리포트에 반영한다.
GitHub 저장소는 자동으로 계정 전체를 탐색하지 않고 사용자가 명시한다.

- `make gitlab`: 기존 6개 사내 프로젝트. `GITLAB_PROJECTS`로 변경 가능.
- `make github GITHUB_REPOS='owner/repo'`: 명시한 GitHub 저장소만 조회.
- `MR_PR_LIMIT=0`: 기본값, 기간 내 선택된 MR/PR 전체. 양수로 상세 조회 상한 설정.
- `SINCE_DAYS=180`: 기본 기간. 생성 건수와 리뷰 활동 기간의 의미는 아래 참고.
- `make test-mr-pr`: 네트워크 없는 수집·결합 회귀 테스트.
- `make all GITHUB_REPOS='owner/repo'`: 기존 파이프라인에 GitHub 수집 추가.

`GITLAB_JSON`은 GitLab 수집 결과 및 결합 입력 파일을 지정한다(기본: 당일 결과).
실패한 실행 뒤 오래된 스냅샷을 자동으로 선택하지 않는다. 부분 범위를 수집할 때는
별도 파일을 지정하고, 결합 시에도 같은 `GITLAB_JSON`을 전달한다.
`GITLAB_SKIP_COMMITS=1`(CLI `--skip-commits`)은 MR과 무관한 레거시 커밋 집계를
명시적으로 제외한다. 이 경우 `commits=null`, `unavailable`을 기록하며 리포트는
`N/A`로 표시한다. 기본값은 커밋도 수집하며, API 실패를 자동으로 무시하지 않는다.

GitLab은 worktree 루트 환경파일의 `GITLAB_TOKEN`과 `GITLAB_BASE_URL`을 사용한다.
`GITLAB_ENV`로 파일을 바꿀 수 있으며 프로세스 환경변수가 우선한다. 토큰은
`PRIVATE-TOKEN` 헤더로 전달한다. 토큰이 없을 때만 기존 `LGEP_ID`/`LGEP_PASSWORD`
Basic 인증을 사용한다. base URL은 `/hub` 같은 경로를 유지하고 `/api/v4`를 정규화한다.
HTTPS 인증서를 검증하며 리다이렉트는 따르지 않는다. 설정 URL이 HTTP이면 인증 토큰이
암호화되지 않으므로 서버가 지원하는 HTTPS 주소 사용을 권장한다.
GitHub는 기존에 인증된 `gh` CLI 세션을 사용한다. 인증 값은 출력하거나 JSON에 저장하지 않는다.

## 보관 범위

두 수집기는 응답 본문을 메모리에서 허용 필드만 골라 변환한다. MR/PR 제목·설명,
리뷰/댓글 본문·코드·diff hunk는 저장하거나 출력하지 않는다.

| 구분 | GitLab MR | GitHub PR |
| --- | --- | --- |
| 요청 | 프로젝트, ID/iid, 상태, 생성·갱신·병합 시각 | 저장소, ID/번호, 상태, merged, 생성·갱신·병합 시각 |
| 작성자/병합자 | author / merged_by (merge_user 호환) | author / merged_by |
| 리뷰 | 현재 approval 스냅샷, 요청된 reviewer | 제출 review의 시각·상태, 요청된 reviewer |
| 댓글 | discussion별 note, system 여부, 해결 상태·위치 | issue 댓글 + review 댓글, 답글·라인 위치 |

요청된 reviewer는 실제 리뷰 참여와 구분한다. GitHub REST가 제공하지 않는 스레드
해결 여부는 추정하지 않는다. `DISMISSED` 리뷰의 원래 승인/거절 값은 복원하지 않는다.
GitLab approval API의 404/405는 해당 스냅샷을 `null`/`unavailable`로 표시한다.
필수 API의 인증·권한·네트워크·파싱 오류는 실패 처리하며 이전 JSON을 유지한다.
GitLab `locked` 상태나 GitHub `closed` 상태만으로 병합됐다고 판단하지 않는다.

## JSON 및 집계 의미

`schema_version=2`, `collected_at`, `window_days`, `requests`에 수집 메타데이터와
개별 MR/PR이 들어간다. `truncated_projects`/`truncated_repos`가 있으면 상세 수집이
상한으로 제한된 것이므로 해당 기간의 완전한 활동량으로 해석하면 안 된다.
`projects`(GitLab)/`repos`(GitHub)는 0건인 저장소도 포함한 실제 조회 범위이다.
리포트에도 범위를 표시하며 범위 밖 저장소는 활동 0건을 의미하지 않는다.

| Counter | 의미 |
| --- | --- |
| `mrs` / `prs` | 기간 내 생성된 MR/PR 작성자 건수. 기존 생성 지표 유지 |
| `request_author_total` | 기간 내 갱신되어 선택된 MR/PR의 작성자별 건수 |
| `reviewer_total` | 작성자 자신을 제외한 참여자별 고유 MR/PR 수 |
| `comment_total` | 기간 내 생성된 일반 댓글 수. GitLab system note 제외 |
| `review_total` | GitLab: 현재 승인 스냅샷 수 / GitHub: 기간 내 제출된 리뷰 수 |
| `merged_author_total` | 선택된 MR/PR 중 현재 병합된 요청의 작성자별 건수 |
| `merger_total` | 기간 내 병합 시각과 실제 병합자가 확인된 건수 |

GitLab reviewer 참여는 최근 일반 댓글 또는 현재 approval에 근거한다. 현재 approval은
기간 내 승인 이벤트를 보장하지 않는다. GitHub 참여는 기간 내 제출 리뷰/생성 댓글에
근거한다. 병합자가 누락됐을 때 작성자나 committer로 대신 추정하지 않는다.
개별 요청의 과거 댓글 목록 길이는 기간으로 제한된 집계와 다를 수 있다.

[결합 리포트](combine_expert_signals.py)는 기존 표 옆에 열을 계속 늘리는 대신 별도
MR/PR 표를 제공한다. 구버전 JSON에서 누락된 지표는 `N/A`, 수집한 빈 지표는 0이다.
approval 미수집, 상세 조회 상한, 서로 다른 수집 기간/종료 시각을 경고한다.
GitHub 입력을 생략하면 수집되지 않았음을 명시하고 GitLab만 표시한다.

계정 이름이 같아도 동일인이라는 보장은 없고 자동화 계정도 포함될 수 있다.
이 데이터는 전문가 라우팅 참고용이며 개인 성과 비교·평가 점수로 사용하지 않는다.

## 2026-09-15 실수집 검증

- 최근 180일, 상세 개수 제한 없이 GitLab 5개 프로젝트를 조회했다:
	`Tiger/AutoTest_Cmd`, `Tiger/LogAnalyzer`, `cheoljoo.lee/ldap`,
	`cheoljoo.lee/new_commit_review_violation_checker`, `cheoljoo.lee/sage-wiki`.
- MR 6건(모두 AutoTest_Cmd): 병합 5건, 닫힘 1건. 병합 5건 모두 실제 병합자를 확인했다.
- discussion note 메타데이터 18건, 기간 내 일반 댓글 0건, 현재 승인 스냅샷 1건.
- `Tiger/swit`: 프로젝트 정보는 조회되지만 커밋 API 404, MR API 403이므로 제외했다.
	접근 불가 원인이 권한인지 서버 기능 설정인지는 확인되지 않았다.
- `cheoljoo.lee/sage-wiki` 커밋 API는 페이지 2·3에서 기존 커밋을 반복 반환했다.
	따라서 이번 실행은 `GITLAB_SKIP_COMMITS=1`로 5개 프로젝트의 커밋 집계를 모두 제외했다.
- GitHub `cheoljoo/sage-wiki`(비공개 저장소)는 해당 기간 PR 0건.
	실제 GitHub 리뷰/댓글 응답은 이번 실행으로 검증되지 않았으며 모의 테스트로 검증했다.
- 결과: [GitLab MR JSON](output/gitlab_signal_accessible5_2026-09-15.json),
	[GitHub PR JSON](output/github_signal_2026-09-15.json),
	[결합 리포트](output/combined_report_2026-09-15.txt).
	출력 디렉터리는 Git 추적 대상이 아니며 위 링크는 로컬 수집 결과이다.
- 본문·제목·설명·diff 필드가 결과 JSON에 없음을 재귀 검사했다.