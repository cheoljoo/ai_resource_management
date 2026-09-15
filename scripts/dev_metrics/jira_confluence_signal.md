# Jira·Confluence 신호 수집

[jira_confluence_signal.py](jira_confluence_signal.py)는 기존 MCP 수동 수집을
Jira Server/Data Center·Confluence REST API의 읽기 전용 조회로 대체한다.
`uv run`이 스크립트의 PEP 723 선언을 읽어 `requests`, `python-dotenv`를 준비한다.
별도 pip 설치나 가상환경 활성화는 필요하지 않다.

## 실행

아래 명령은 이 문서가 있는 디렉터리에서 실행한다.

```sh
make jira-confluence
make jira-confluence SINCE_DAYS=90
uv run jira_confluence_signal.py --person cheoljoo.lee@lge.com --since-days 180
uv run jira_confluence_signal.py --help
make test-jira-confluence
```

- `make jira-confluence`: 기본 20명 명단을 조회하고 날짜별 JSON·텍스트를 output 하위에 저장.
- `make combine`: 해당 날짜의 JSON을 기존 git/Gerrit/GitLab 자료와 결합.
- `make all`: Gerrit/GitLab/Jira/Confluence 수집이 성공한 뒤 결합. `make -j all`도 결합은 마지막.
- `JC_ENV`, `JC_ROSTER`, `JC_JSON` Make 변수로 환경설정·명단·출력 경로 변경 가능.
- 스크립트 기본 환경설정 경로는 현재 디렉터리가 아닌 **worktree 루트** 기준이다.
- 기본 명단은 [기존 스냅샷](jira_confluence_signal_2026-09-11.json)의 `people` 키만 재사용한다.
  예전 건수는 사용하지 않는다. `--person`을 반복하면 해당 인원만 조회한다.

## 환경설정

worktree 루트의 로컬 환경설정 파일에서 다음 키를 읽는다. 프로세스 환경변수가 우선한다.

| 키 | 용도 |
| --- | --- |
| `JIRA_URL` | Jira 기본 URL. `/jira` 같은 context path 포함, `/rest/api/...` 제외 |
| `JIRA_PERSONAL_TOKEN` | Jira PAT, `Authorization: Bearer` 인증 |
| `CONFLUENCE_URL` | Confluence 기본 URL. `/main` 같은 context path 포함 |
| `CONFLUENCE_PERSONAL_TOKEN` | Confluence PAT, `Authorization: Bearer` 인증 |
| `JIRA_SSL_VERIFY`, `CONFLUENCE_SSL_VERIFY` | 기본 true. false이면 경고 후 인증서 검증 해제 |

기존 `JIRA_USERNAME`, `CONFLUENCE_USERNAME`은 PAT 인증에 필요하지 않다.
Cloud의 이메일+API token Basic 인증은 지원하지 않는다.
가능하면 HTTPS와 인증서 검증을 사용한다. 토큰·응답 본문은 오류 로그/결과에 기록하지 않는다.
로그인 화면이나 다른 호스트로 리다이렉트되면 따라가지 않고 실패한다.

## 계정 식별자

기본적으로 `person@domain`의 `person`을 두 시스템의 계정 ID로 사용한다.
이 규칙이 맞지 않으면 별도의 명단 JSON에서 실제 서비스별 ID를 지정한다.
자동 계정 검색/추정은 하지 않으며, 0건은 계정 매핑과 권한도 확인해야 한다.

```json
{
  "people": {
    "person@example.com": {
      "jira_user": "jira-login",
      "confluence_user": "confluence-login"
    }
  }
}
```

`--roster`로 해당 JSON을 전달한다. 식별자를 생략한 항목은 기본 규칙을 적용한다.

## 집계 의미 및 한계

- Jira: `(assignee = USER OR reporter = USER) AND updated >= -Nd`의 `total`.
  이슈 본문 없이 총건수만 조회하며, 담당자·보고자 양쪽에 해당해도 중복되지 않는다.
- Confluence: `contributor = USER AND lastmodified >= now("-Nd")`에 맞는 콘텐츠의
  고유 ID 수. REST pagination을 끝까지 읽으므로 기존 MCP 스냅샷의 50건 상한이 없다.
  본문을 확장하거나 저장하지 않는다. 모든 콘텐츠 유형을 대상으로 하며 수정 이벤트 수가 아니다.
- 해당 사용자가 **기간 내 직접 수정했다는 뜻은 아니다**. 과거 기여 문서를 다른 사람이
  최근 수정했어도 포함될 수 있다. Jira 역시 다른 사람이 갱신한 담당/보고 이슈가 포함된다.
- 조회 토큰의 접근 권한에 한정된다. 조회 도중 변경되는 데이터는 일관된 DB 스냅샷이 아니다.
- JSON의 `people`별 `jira_total_180d`/`confluence_hits`는 기존 결합기 호환 형식이다.
  `jira_total_180d`는 레거시 키 이름이며 **실제 기간은 `window_days`** 및 각 JQL/CQL에 기록한다.
  `combine` 실행 시에도 수집 때와 같은 `SINCE_DAYS`를 사용한다.
- 인증/권한/네트워크/응답 오류는 0건으로 숨기지 않고 종료 코드 1로 중단한다.
  수집 실패 시 기존 JSON은 덮어쓰지 않으며, Make의 `pipefail`로 `tee` 뒤의 실패도 전파한다.
- 전문가 라우팅 참고용 메타데이터이며 **개인 성과 비교·평가로 전용하지 않는다**.