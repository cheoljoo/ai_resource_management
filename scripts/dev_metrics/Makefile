# 전문가 파인더 (Expert Finder, AGILEDEV-1132) — 5개 소스 결합 파이프라인
#
# 데이터 소스 5종과 담당:
#   git(사내+GitHub) → expert_finder.py         : 로컬 clone, 이 Makefile이 직접 실행
#   Gerrit           → gerrit_signal.py         : ~/code/ccr/global_variables.py 자격증명, 이 Makefile이 직접 실행
#   GitLab(mod.lge.com/hub) → gitlab_signal.py  : .env의 LGEP_ID/LGEP_PASSWORD, 이 Makefile이 직접 실행
#   Jira             → mcp-atlassian MCP        : Claude(에이전트)만 호출 가능 — make로 자동화 불가, 아래 참고
#   Confluence       → mcp-atlassian MCP        : 위와 동일
#
# 결과물은 모두 output/ 아래에 쌓인다(make help 참고).

SHELL := /bin/bash
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

GITLAB_PROJECTS := \
	Tiger/AutoTest_Cmd \
	Tiger/LogAnalyzer \
	Tiger/swit \
	cheoljoo.lee/ldap \
	cheoljoo.lee/new_commit_review_violation_checker \
	cheoljoo.lee/sage-wiki
GITLAB_PROJECT_ARGS := $(foreach p,$(GITLAB_PROJECTS),--project $(p))

# Jira/Confluence는 Claude가 mcp-atlassian MCP로 직접 조회해 만든 JSON이다.
# make로 재생성할 수 없으므로 이미 만들어둔 파일을 그대로 쓴다.
JC_JSON := jira_confluence_signal_2026-09-11.json

.PHONY: help verify expert-finder gerrit gitlab combine all jira-confluence-note clean

help:
	@echo "전문가 파인더 (AGILEDEV-1132) — 사용 가능한 타겟"
	@echo ""
	@echo "  make verify           - 5개 스크립트가 정상 동작하는지 --help로 확인"
	@echo "  make expert-finder    - git 기반 저장소/모듈별 전문가 랭킹 산출"
	@echo "                          -> $(OUT)/expert_finder_<날짜>.txt"
	@echo "  make gerrit           - Gerrit(na/lamp) 리뷰/변경 신호 수집"
	@echo "                          -> $(OUT)/gerrit_signal_<날짜>.json, .txt"
	@echo "  make gitlab           - 사내 GitHub/GitLab(mod.lge.com/hub) 커밋/MR 신호 수집"
	@echo "                          -> $(OUT)/gitlab_signal_<날짜>.json, .txt"
	@echo "  make jira-confluence-note - Jira/Confluence는 make로 자동 수집 불가한 이유와"
	@echo "                          현재 사용 중인 JSON 파일을 안내"
	@echo "  make combine          - 위 4개(git+Gerrit+GitLab+기존 Jira/Confluence json) 결합한"
	@echo "                          최종 리포트 산출 -> $(OUT)/combined_report_<날짜>.txt"
	@echo "  make all              - gerrit + gitlab + combine 순서로 전체 파이프라인 실행"
	@echo "  make clean            - $(OUT)/ 삭제"
	@echo ""
	@echo "SINCE_DAYS=$(SINCE_DAYS) (예: make all SINCE_DAYS=90 으로 기간 변경 가능)"

$(OUT):
	mkdir -p $(OUT)

verify: $(OUT)
	@echo "== experience_atoms.py =="; uv run experience_atoms.py --help > $(OUT)/verify_experience_atoms.txt
	@echo "== expert_finder.py =="; uv run expert_finder.py --help > $(OUT)/verify_expert_finder.txt
	@echo "== gerrit_signal.py =="; uv run --with requests gerrit_signal.py --help > $(OUT)/verify_gerrit_signal.txt
	@echo "== gitlab_signal.py =="; uv run --with requests gitlab_signal.py --help > $(OUT)/verify_gitlab_signal.txt
	@echo "== github_signal.py =="; uv run github_signal.py --help > $(OUT)/verify_github_signal.txt
	@echo "== combine_expert_signals.py =="; uv run combine_expert_signals.py --help > $(OUT)/verify_combine.txt
	@echo "5개 스크립트 모두 정상 동작 확인 완료 (결과: $(OUT)/verify_*.txt)"

expert-finder: $(OUT)
	uv run expert_finder.py $(REPO_ARGS) --since-days $(SINCE_DAYS) --top 3 \
		| tee $(OUT)/expert_finder_$(DATE).txt

gerrit: $(OUT)
	uv run --with requests gerrit_signal.py $(GERRIT_SERVER_ARGS) --since-days $(SINCE_DAYS) \
		--limit-per-server 500 --top 3 --json-out $(OUT)/gerrit_signal_$(DATE).json \
		| tee $(OUT)/gerrit_signal_$(DATE).txt

gitlab: $(OUT)
	# gitlab_signal.py는 worktree 루트의 .env(LGEP_ID/LGEP_PASSWORD)를 읽어야 하므로 루트에서 실행한다.
	cd ../.. && uv run --with requests scripts/dev_metrics/gitlab_signal.py $(GITLAB_PROJECT_ARGS) \
		--since-days $(SINCE_DAYS) \
		--json-out scripts/dev_metrics/$(OUT)/gitlab_signal_$(DATE).json \
		| tee scripts/dev_metrics/$(OUT)/gitlab_signal_$(DATE).txt

jira-confluence-note:
	@echo "Jira/Confluence는 mcp-atlassian MCP를 통해 Claude(에이전트)가 직접 조회해야 하며,"
	@echo "make(셸)에서는 그 MCP 도구를 호출할 수 없다 — 따라서 자동화 타겟이 없다."
	@echo "현재 combine이 사용하는 파일: $(JC_JSON)"
	@echo "새로 갱신하려면 Claude에게 '20명 로스터로 Jira/Confluence 신호 다시 수집해줘'라고 요청한다."

combine: $(OUT)
	@if [ ! -f $(JC_JSON) ]; then \
		echo "ERROR: $(JC_JSON) 이 없습니다. 'make jira-confluence-note' 참고."; exit 1; \
	fi
	uv run combine_expert_signals.py $(REPO_ARGS) --since-days $(SINCE_DAYS) \
		--gerrit-json $$(ls -t $(OUT)/gerrit_signal_*.json 2>/dev/null | head -1) \
		--gitlab-json $$(ls -t $(OUT)/gitlab_signal_*.json 2>/dev/null | head -1) \
		--jira-confluence-json $(JC_JSON) \
		--top-people 25 \
		| tee $(OUT)/combined_report_$(DATE).txt

all: gerrit gitlab combine
	@echo "전체 파이프라인 완료 — 결과는 $(OUT)/ 아래 참고:"
	@ls -la $(OUT)/

clean:
	rm -rf $(OUT)
