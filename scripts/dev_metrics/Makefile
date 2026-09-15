# 전문가 파인더 (Expert Finder, AGILEDEV-1132) — 5개 소스 결합 파이프라인
#
# 데이터 소스 5종과 담당:
#   git(사내+GitHub) → expert_finder.py         : 로컬 clone, 이 Makefile이 직접 실행
#   Gerrit           → gerrit_signal.py         : ~/code/ccr/global_variables.py 자격증명, 이 Makefile이 직접 실행
#   GitLab(mod.lge.com/hub) → gitlab_signal.py  : .env의 GITLAB_TOKEN/GITLAB_BASE_URL
#   GitHub(선택)      → github_signal.py         : 인증된 gh CLI, Python 실행은 uv
#   Jira             → jira_confluence_signal.py : .env의 JIRA_* 설정으로 REST 조회
#   Confluence       → jira_confluence_signal.py : .env의 CONFLUENCE_* 설정으로 REST 조회
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

.PHONY: help verify test-gerrit test-jira-confluence test-mr-pr expert-finder gerrit gitlab github mr-pr jira-confluence combine all jira-confluence-note clean

help:
	@echo "전문가 파인더 (AGILEDEV-1132) — 사용 가능한 타겟"
	@echo ""
	@echo "  make verify           - 7개 스크립트가 정상 동작하는지 --help로 확인"
	@echo "  make test-jira-confluence - Jira/Confluence 수집기 단위 테스트 (네트워크 불필요)"
	@echo "  make test-gerrit       - Gerrit 수집/결합 리포트 단위 테스트 (네트워크 불필요)"
	@echo "  make expert-finder    - git 기반 저장소/모듈별 전문가 랭킹 산출"
	@echo "                          -> $(OUT)/expert_finder_<날짜>.txt"
	@echo "  make gerrit           - Gerrit(na/lamp) 리뷰·댓글·병합·submitter 메타데이터 수집"
	@echo "                          -> $(OUT)/gerrit_signal_<날짜>.json, .txt"
	@echo "                          GERRIT_LIMIT=$(GERRIT_LIMIT) (0: 기간 내 모든 change, 기본 500개/서버)"
	@echo "  make gitlab           - 사내 GitHub/GitLab(mod.lge.com/hub) 커밋/MR 신호 수집"
	@echo "                          -> $(OUT)/gitlab_signal_<날짜>.json, .txt"
	@echo "  make github GITHUB_REPOS='owner/repo' - GitHub PR·리뷰·댓글·실제 병합자 수집"
	@echo "  make mr-pr            - GitLab MR + 지정된 GitHub PR 수집 (MR_PR_LIMIT=0: 전체)"
	@echo "  make test-mr-pr        - MR/PR 수집기 및 결합 테스트 (uv, 네트워크 불필요)"
	@echo "  make jira-confluence  - .env의 PAT로 Jira/Confluence 신호 수집"
	@echo "                          -> $(JC_JSON)"
	@echo "  make combine          - git+Gerrit+GitLab+수집된 Jira/Confluence JSON을 결합한"
	@echo "                          최종 리포트 산출 -> $(OUT)/combined_report_<날짜>.txt"
	@echo "  make all              - gerrit + gitlab + jira-confluence (+ 지정된 github) 후 combine"
	@echo "  make clean            - $(OUT)/ 삭제"
	@echo ""
	@echo "SINCE_DAYS=$(SINCE_DAYS) (예: make all SINCE_DAYS=90 으로 기간 변경 가능)"

$(OUT):
	mkdir -p $(OUT)

verify: $(OUT)
	@echo "== experience_atoms.py =="; uv run experience_atoms.py --help > $(OUT)/verify_experience_atoms.txt
	@echo "== expert_finder.py =="; uv run expert_finder.py --help > $(OUT)/verify_expert_finder.txt
	@echo "== gerrit_signal.py =="; uv run gerrit_signal.py --help > $(OUT)/verify_gerrit_signal.txt
	@echo "== gitlab_signal.py =="; uv run gitlab_signal.py --help > $(OUT)/verify_gitlab_signal.txt
	@echo "== github_signal.py =="; uv run github_signal.py --help > $(OUT)/verify_github_signal.txt
	@echo "== jira_confluence_signal.py =="; uv run jira_confluence_signal.py --help > $(OUT)/verify_jira_confluence_signal.txt
	@echo "== combine_expert_signals.py =="; uv run combine_expert_signals.py --help > $(OUT)/verify_combine.txt
	@echo "7개 스크립트 모두 정상 동작 확인 완료 (결과: $(OUT)/verify_*.txt)"

test-jira-confluence:
	uv run --with 'requests>=2.32,<3' --with 'python-dotenv>=1,<2' python -m unittest discover -s tests -p 'test_jira_confluence_signal.py' -v

test-gerrit:
	uv run --with 'requests>=2.32,<3' python -m unittest discover -s tests -p '*gerrit*.py' -v

test-mr-pr:
	uv run --with 'requests>=2.32,<3' --with 'python-dotenv>=1,<2' python -m unittest discover -s tests -p 'test_git*signal.py' -v
	uv run python -m unittest discover -s tests -p 'test_combine_mr_pr_signals.py' -v

expert-finder: $(OUT)
	uv run expert_finder.py $(REPO_ARGS) --since-days $(SINCE_DAYS) --top 3 \
		| tee $(OUT)/expert_finder_$(DATE).txt

gerrit: $(OUT)
	uv run gerrit_signal.py $(GERRIT_SERVER_ARGS) --since-days $(SINCE_DAYS) \
		--limit-per-server $(GERRIT_LIMIT) --top 3 --json-out $(OUT)/gerrit_signal_$(DATE).json \
		| tee $(OUT)/gerrit_signal_$(DATE).txt

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
