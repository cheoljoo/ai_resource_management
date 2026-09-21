# 개발자 평가 메트릭 파이프라인 — 두 브랜치가 병합된 상태 (2026-09-15 정리)
#
# 이 Makefile은 서로 다른 목적의 두 파이프라인을 함께 담고 있다 — 자세한 배경은
# ../../dev_metrics_code_map.md "0. 브랜치별 작업 요약" 절 참고:
#
#   (A) 개인 진단 프로필 (AGILEDEV-1118, intent/2026-09-09-developer-expertise-grading) — "profile"
#       그룹 타겟. 본인 범위 한정(spec.md 원칙), 5대 대항목 다차원 프로필 + 인정/경고 신호를 산출한다.
#       핵심: composite_signals.py, activity_breadth.py, monthly_activity_clusters.py, run_history.py,
#       github_activity.py, experience_atoms.py.
#
#   (B) 전문가 파인더 (Expert Finder, AGILEDEV-1132, intent/2026-09-11-expert-finder) — 기존 5개 소스
#       결합 타겟. 본인 범위 한정 원칙의 명시적 예외(라우팅 목적, 공유 git log만) — "회사 안의 어떤
#       사람이 전문가인지"를 데이터로만 찾는다. 데이터 소스 5종과 담당:
#         git(사내+GitHub) → expert_finder.py         : 로컬 clone, 이 Makefile이 직접 실행
#         Gerrit           → gerrit_signal.py         : ~/code/ccr/global_variables.py 자격증명, 이 Makefile이 직접 실행
#         GitLab(mod.lge.com/hub) → gitlab_signal.py  : .env의 GITLAB_TOKEN/GITLAB_BASE_URL
#         GitHub(선택)      → github_signal.py         : 인증된 gh CLI, Python 실행은 uv
#         Jira             → jira_confluence_signal.py : .env의 JIRA_* 설정으로 REST 조회
#         Confluence       → jira_confluence_signal.py : .env의 CONFLUENCE_* 설정으로 REST 조회
#
# (A)와 (B)를 혼동하지 말 것: (A)는 "나는 어떤가"(본인 회고), (B)는 "이 모듈은 누구에게 물어볼까"
# (조직 전체 라우팅)이다 — 둘 다 인사 평가에는 쓰지 않는다(developer_evaluation_metrics.md 7장).
#
# 결과물은 모두 output/ 아래에 쌓인다(make help 참고).

SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c
DATE := $(shell date +%Y-%m-%d)
OUT := output
SINCE_DAYS ?= 180

REPOS := \
	$(HOME)/code/AutoTest_Cmd \
	$(HOME)/code/LogAnalyzer \
	$(HOME)/code/pvs_crawler \
	$(HOME)/code/pvs_crawler_new \
	$(HOME)/code/new_commit_review_violation_checker \
	$(HOME)/code/pvs_trender \
	$(HOME)/code/ldap \
	$(HOME)/code/swit \
	$(HOME)/code/sage-wiki

REPO_ARGS := $(foreach r,$(REPOS),--repo $(r))

GERRIT_SERVERS := na lamp
GERRIT_SERVER_ARGS := $(foreach s,$(GERRIT_SERVERS),--server $(s))
GERRIT_LIMIT ?= 500

GITLAB_PROJECTS := \
	Tiger/AutoTest_Cmd \
	Tiger/LogAnalyzer \
	Tiger/swit \
	cheoljoo.lee/ldap \
	cheoljoo.lee/new_commit_review_violation_checker \
	cheoljoo.lee/sage-wiki
GITLAB_PROJECT_ARGS := $(foreach p,$(GITLAB_PROJECTS),--project $(p))
GITLAB_ENV ?= ../../.env
GITLAB_JSON ?= $(OUT)/gitlab_signal_$(DATE).json
GITLAB_SKIP_COMMITS ?= 0
MR_PR_LIMIT ?= 0
# GitHub 저장소는 공개/비공개 여부와 무관하게 명시적으로 선택한다. 예: GITHUB_REPOS=owner/repo
GITHUB_REPOS ?=
GITHUB_REPO_ARGS := $(foreach r,$(GITHUB_REPOS),--repo $(r))
GITHUB_JSON ?= $(OUT)/github_signal_$(DATE).json
GITHUB_COMBINE_ARGS = $(if $(strip $(GITHUB_REPOS)),--github-json "$(GITHUB_JSON)")

# 기존 스냅샷은 명단으로만 재사용하며 건수는 매번 REST API로 수집한다.
JC_ROSTER ?= jira_confluence_signal_2026-09-11.json
JC_ENV ?= ../../.env
JC_JSON ?= $(OUT)/jira_confluence_signal_$(DATE).json

# --- (A) 개인 진단 프로필 (AGILEDEV-1118) 전용 변수 ---
# 본인 범위 한정이므로 PROFILE_AUTHOR를 반드시 본인 것으로 지정할 것(기본값은 예시일 뿐).
PROFILE_AUTHOR ?= cheoljoo
PROFILE_REPO ?= $(HOME)/code/llm_wiki
PROFILE_REPOS ?= $(REPOS)
# activity_breadth.py/composite_signals.py의 --repos는 nargs='+'라 반복 플래그가 아니라
# 한 번의 --repos 뒤에 공백으로 나열해야 한다(expert-finder의 REPO_ARGS와는 다른 형태이니 혼동 주의).
PROFILE_REPO_ARGS := --repos $(PROFILE_REPOS)
GITHUB_LOGIN ?=

.PHONY: help verify test-gerrit test-jira-confluence test-mr-pr expert-finder gerrit gitlab github mr-pr jira-confluence combine all jira-confluence-note clean profile activity-breadth monthly-clusters run-history github-activity test-adequacy review-quality cross-team-review jira-confluence-expansion codebeamer-traceability jenkins

help:
	@echo "개발자 평가 메트릭 파이프라인 — 사용 가능한 타겟 (병합 후 정리, 2026-09-15)"
	@echo ""
	@echo "== (A) 개인 진단 프로필 (AGILEDEV-1118, 본인 범위 한정) =="
	@echo "  make profile PROFILE_AUTHOR=<본인> PROFILE_REPO=<주 저장소> - 5대 대항목 다차원 프로필"
	@echo "                          + 인정/경고 신호 산출 (composite_signals.py)"
	@echo "  make activity-breadth  - 여러 저장소에 걸친 활동 폭/다양성(4.4절) 산출"
	@echo "  make monthly-clusters  - 월별 활동 비지도 클러스터링(Montandon et al. 2019 방법)"
	@echo "  make github-activity GITHUB_LOGIN=<계정> - GitHub 기여 이력으로 활동 폭 확장(6.3절)"
	@echo "  make run-history       - 누적 실행 이력 요약 + 임계치 재보정 제안(AI Flywheel 7단계)"
	@echo "  make test-adequacy     - 테스트 파일 동반 여부 비율 (agent-action-items.md A4)"
	@echo ""
	@echo "== agent-action-items.md A1/A2 POC (Gerrit 라이브 조회) =="
	@echo "  make review-quality    - 리뷰 코멘트 라인단위/스레드 비율 (메타데이터 전용, A1)"
	@echo "  make cross-team-review - 오너 vs 리뷰 프로젝트 교차 참여 비율 (A2)"
	@echo "  make jira-confluence-expansion - Jira 교차 프로젝트 참여율 + Confluence 타인 문서 코멘트 (A2/A3)"
	@echo ""
	@echo "== (B) 전문가 파인더 (Expert Finder, AGILEDEV-1132, 조직 전체 라우팅) =="
	@echo "  make expert-finder    - git 기반 저장소/모듈별 전문가 랭킹 산출"
	@echo "                          -> $(OUT)/expert_finder_<날짜>.txt"
	@echo "  make gerrit           - Gerrit(na/lamp) 리뷰·댓글·병합·submitter 메타데이터 수집"
	@echo "                          -> $(OUT)/gerrit_signal_<날짜>.json, .txt"
	@echo "                          GERRIT_LIMIT=$(GERRIT_LIMIT) (0: 기간 내 모든 change, 기본 500개/서버)"
	@echo "  make gitlab           - 사내 GitHub/GitLab(mod.lge.com/hub) 커밋/MR 신호 수집"
	@echo "                          -> $(OUT)/gitlab_signal_<날짜>.json, .txt"
	@echo "  make github GITHUB_REPOS='owner/repo' - GitHub PR·리뷰·댓글·실제 병합자 수집"
	@echo "  make mr-pr            - GitLab MR + 지정된 GitHub PR 수집 (MR_PR_LIMIT=0: 전체)"
	@echo "  make jira-confluence  - .env의 PAT로 Jira/Confluence 신호 수집"
	@echo "                          -> $(JC_JSON)"
	@echo "  make combine          - git+Gerrit+GitLab+수집된 Jira/Confluence JSON을 결합한"
	@echo "                          최종 리포트 산출 -> $(OUT)/combined_report_<날짜>.txt"
	@echo "  make all              - gerrit + gitlab + jira-confluence (+ 지정된 github) 후 combine"
	@echo ""
	@echo "== 공통 =="
	@echo "  make verify           - 모든 스크립트가 --help로 정상 동작하는지 확인"
	@echo "  make test-jira-confluence - Jira/Confluence 수집기 단위 테스트 (네트워크 불필요)"
	@echo "  make test-gerrit       - Gerrit 수집/결합 리포트 단위 테스트 (네트워크 불필요)"
	@echo "  make test-mr-pr        - MR/PR 수집기 및 결합 테스트 (uv, 네트워크 불필요)"
	@echo "  make clean            - $(OUT)/ 삭제"
	@echo ""
	@echo "SINCE_DAYS=$(SINCE_DAYS) (예: make all SINCE_DAYS=90 으로 기간 변경 가능)"
	@echo "PROFILE_AUTHOR=$(PROFILE_AUTHOR) PROFILE_REPO=$(PROFILE_REPO) (반드시 본인 값으로 지정할 것)"

$(OUT):
	mkdir -p $(OUT)

verify: $(OUT)
	@echo "== experience_atoms.py =="; uv run experience_atoms.py --help > $(OUT)/verify_experience_atoms.txt
	@echo "== composite_signals.py =="; uv run composite_signals.py --help > $(OUT)/verify_composite_signals.txt
	@echo "== activity_breadth.py =="; uv run activity_breadth.py --help > $(OUT)/verify_activity_breadth.txt
	@echo "== monthly_activity_clusters.py =="; uv run monthly_activity_clusters.py --help > $(OUT)/verify_monthly_activity_clusters.txt
	@echo "== run_history.py =="; uv run run_history.py --help > $(OUT)/verify_run_history.txt
	@echo "== github_activity.py =="; uv run github_activity.py --help > $(OUT)/verify_github_activity.txt
	@echo "== expert_finder.py =="; uv run expert_finder.py --help > $(OUT)/verify_expert_finder.txt
	@echo "== gerrit_signal.py =="; uv run gerrit_signal.py --help > $(OUT)/verify_gerrit_signal.txt
	@echo "== gitlab_signal.py =="; uv run gitlab_signal.py --help > $(OUT)/verify_gitlab_signal.txt
	@echo "== github_signal.py =="; uv run github_signal.py --help > $(OUT)/verify_github_signal.txt
	@echo "== jira_confluence_signal.py =="; uv run jira_confluence_signal.py --help > $(OUT)/verify_jira_confluence_signal.txt
	@echo "== combine_expert_signals.py =="; uv run combine_expert_signals.py --help > $(OUT)/verify_combine.txt
	@echo "13개 스크립트 모두 정상 동작 확인 완료 (결과: $(OUT)/verify_*.txt)"

test-jira-confluence:
	uv run --with 'requests>=2.32,<3' --with 'python-dotenv>=1,<2' python -m unittest discover -s tests -p 'test_jira_confluence_signal.py' -v

test-gerrit:
	uv run --with 'requests>=2.32,<3' python -m unittest discover -s tests -p '*gerrit*.py' -v

test-mr-pr:
	uv run --with 'requests>=2.32,<3' --with 'python-dotenv>=1,<2' python -m unittest discover -s tests -p 'test_git*signal.py' -v
	uv run python -m unittest discover -s tests -p 'test_combine_mr_pr_signals.py' -v

# --- (A) 개인 진단 프로필 타겟 (AGILEDEV-1118) ---

profile: $(OUT)
	uv run composite_signals.py --repo "$(PROFILE_REPO)" $(PROFILE_REPO_ARGS) --author "$(PROFILE_AUTHOR)" \
		| tee $(OUT)/profile_$(DATE).txt

activity-breadth: $(OUT)
	uv run activity_breadth.py $(PROFILE_REPO_ARGS) --author "$(PROFILE_AUTHOR)" \
		| tee $(OUT)/activity_breadth_$(DATE).txt

monthly-clusters: $(OUT)
	uv run monthly_activity_clusters.py --repo "$(PROFILE_REPO)" --author "$(PROFILE_AUTHOR)" \
		| tee $(OUT)/monthly_clusters_$(DATE).txt

github-activity: $(OUT)
	@test -n "$(strip $(GITHUB_LOGIN))" || { echo "ERROR: GITHUB_LOGIN=<본인 GitHub 계정>을 지정하세요."; exit 1; }
	uv run github_activity.py --login "$(GITHUB_LOGIN)" \
		| tee $(OUT)/github_activity_$(DATE).txt

run-history: $(OUT)
	uv run run_history.py --show

test-adequacy: $(OUT)
	uv run test_adequacy.py --repo "$(PROFILE_REPO)" --author "$(PROFILE_AUTHOR)" \
		| tee $(OUT)/test_adequacy_$(DATE).txt

# --- agent-action-items.md A1/A2 POC (Gerrit 라이브 조회, 소규모 표본) ---

review-quality: $(OUT)
	uv run review_quality_signal.py $(GERRIT_SERVER_ARGS) --since-days 60 --limit-per-server 5 \
		| tee $(OUT)/review_quality_$(DATE).txt

cross-team-review: $(OUT)
	uv run cross_team_review_signal.py $(GERRIT_SERVER_ARGS) --since-days 60 --limit-per-server 100 \
		| tee $(OUT)/cross_team_review_$(DATE).txt

jira-confluence-expansion: $(OUT)
	uv run jira_confluence_expansion.py --env-file "$(JC_ENV)" --roster "$(JC_ROSTER)" \
		--since-days $(SINCE_DAYS) --max-jira-issues 50 --max-comments-per-person 10 \
		| tee $(OUT)/jira_confluence_expansion_$(DATE).txt

expert-finder: $(OUT)
	uv run expert_finder.py $(REPO_ARGS) --since-days $(SINCE_DAYS) --top 3 \
		| tee $(OUT)/expert_finder_$(DATE).txt

# CB_SNAPSHOT: ../pvs_crawler의 CBQL 배치 조회로 미리 만든 스냅샷 JSON (실시간 조회는 이 Makefile이
# 하지 않음 — codebeamer_traceability_signal.py 상단 docstring 참고). 기본값은 최근 생성분.
CB_SNAPSHOT ?= codebeamer_signal_2026-09-21.json

codebeamer-traceability: $(OUT)
	uv run codebeamer_traceability_signal.py --snapshot $(CB_SNAPSHOT) \
		| tee $(OUT)/codebeamer_traceability_$(DATE).json
	uv run codebeamer_traceability_signal.py --snapshot $(CB_SNAPSHOT) --experts \
		| tee $(OUT)/codebeamer_experts_$(DATE).json
	uv run codebeamer_traceability_signal.py --snapshot $(CB_SNAPSHOT) --format markdown \
		| tee $(OUT)/codebeamer_traceability_$(DATE).md
	uv run codebeamer_traceability_signal.py --snapshot $(CB_SNAPSHOT) --experts --format markdown \
		| tee $(OUT)/codebeamer_experts_$(DATE).md

gerrit: $(OUT)
	uv run gerrit_signal.py $(GERRIT_SERVER_ARGS) --since-days $(SINCE_DAYS) \
		--limit-per-server $(GERRIT_LIMIT) --top 3 --json-out $(OUT)/gerrit_signal_$(DATE).json \
		| tee $(OUT)/gerrit_signal_$(DATE).txt

JENKINS_JOB_PATTERN ?= acp-master-engineering
JENKINS_TOP ?= 20

jenkins: $(OUT)
	uv run jenkins_signal.py --job-pattern "$(JENKINS_JOB_PATTERN)" --since-days $(SINCE_DAYS) \
		--top $(JENKINS_TOP) --json-out $(OUT)/jenkins_signal_$(DATE).json \
		| tee $(OUT)/jenkins_signal_$(DATE).txt

gitlab: $(OUT)
	uv run gitlab_signal.py $(GITLAB_PROJECT_ARGS) --env-file "$(GITLAB_ENV)" \
		$(if $(filter 1,$(GITLAB_SKIP_COMMITS)),--skip-commits) \
		--since-days $(SINCE_DAYS) --limit-per-project $(MR_PR_LIMIT) \
		--json-out "$(GITLAB_JSON)" \
		| tee $(OUT)/gitlab_signal_$(DATE).txt

github: $(OUT)
	@test -n "$(strip $(GITHUB_REPOS))" || { echo "ERROR: GITHUB_REPOS=owner/repo 를 지정하세요."; exit 1; }
	uv run github_signal.py $(GITHUB_REPO_ARGS) --since-days $(SINCE_DAYS) \
		--limit-per-repo $(MR_PR_LIMIT) --json-out "$(GITHUB_JSON)" \
		| tee $(OUT)/github_signal_$(DATE).txt

mr-pr: gitlab $(if $(strip $(GITHUB_REPOS)),github)

jira-confluence: $(OUT)
	uv run jira_confluence_signal.py --env-file "$(JC_ENV)" --roster "$(JC_ROSTER)" \
		--since-days $(SINCE_DAYS) --json-out "$(JC_JSON)" \
		| tee $(OUT)/jira_confluence_signal_$(DATE).txt

jira-confluence-note:
	@echo "make jira-confluence: .env의 JIRA/CONFLUENCE_URL, PERSONAL_TOKEN, SSL_VERIFY로 REST 조회"
	@echo "명단: $(JC_ROSTER), 환경설정: $(JC_ENV), 결과: $(JC_JSON)"

combine: $(OUT)
	@if [[ ! -f "$(JC_JSON)" ]]; then \
		echo "ERROR: $(JC_JSON) 이 없습니다. 먼저 'make jira-confluence'를 실행하세요."; exit 1; \
	fi
	uv run combine_expert_signals.py $(REPO_ARGS) --since-days $(SINCE_DAYS) \
		--gerrit-json $$(ls -t $(OUT)/gerrit_signal_*.json 2>/dev/null | head -1) \
		--gitlab-json "$(GITLAB_JSON)" \
		--jira-confluence-json "$(JC_JSON)" \
		$(GITHUB_COMBINE_ARGS) \
		--top-people 25 \
		| tee $(OUT)/combined_report_$(DATE).txt

all: gerrit gitlab jira-confluence $(if $(strip $(GITHUB_REPOS)),github)
	$(MAKE) combine
	@echo "전체 파이프라인 완료 — 결과는 $(OUT)/ 아래 참고:"
	@ls -la $(OUT)/

clean:
	rm -rf $(OUT)
