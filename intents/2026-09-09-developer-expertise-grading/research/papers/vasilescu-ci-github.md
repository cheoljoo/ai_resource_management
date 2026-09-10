# Quality and Productivity Outcomes Relating to Continuous Integration in GitHub

- 저자: Bogdan Vasilescu, Yue Yu, Huaimin Wang, Premkumar Devanbu, Vladimir Filkov
- 출처/venue/연도: ESEC/FSE 2015 (Proceedings of the 2015 10th Joint Meeting on Foundations of Software Engineering), pp. 805-816
- 링크: https://dl.acm.org/doi/10.1145/2786805.2786850 , https://web.cs.ucdavis.edu/~filkov/papers/pr_soc_lan.pdf , https://www.researchgate.net/publication/291187145

## 핵심 주장 요약
GitHub 오픈소스 프로젝트를 대상으로 대규모 마이닝 연구를 수행해, 지속적 통합(Continuous Integration, CI) 도입이 팀의 생산성과 코드 품질에 미치는 실증적 영향을 분석한 논문이다. CI를 도입한 프로젝트에서 병합되는 Pull Request 처리량(throughput)이 늘어나는 등 생산성 지표가 개선되는 것으로 나타났으며, 동시에 프로젝트 규모 확장(scaling)에도 긍정적 영향을 준다는 근거를 제시했다. 다만 이 논문은 "CI 도입 = 무조건 좋다"는 단순한 결론이 아니라, 기존 통념보다 더 미묘한(nuanced) 그림 — 즉 CI 효과가 프로젝트 특성과 도입 방식에 따라 달라진다는 점 — 을 보여준다. 대규모 계량서지학적(archival) 데이터 마이닝 방법론을 소프트웨어 공학 생산성 연구에 적용한 대표 사례로 자주 인용된다.

## 주요 발견/모델
- CI 도입 프로젝트에서 병합된 Pull Request 수(처리량)가 유의미하게 증가.
- CI가 프로젝트의 확장성(더 많은 기여자, 더 큰 코드베이스)에도 긍정적으로 연관.
- 품질 측면에서는 단순한 선형적 개선이 아니라 조건부(nuanced) 효과 — 후속 연구(같은 저자 그룹의 "Initial and Eventual Software Quality Relating to CI in GitHub")에서 CI 실패가 소수 파일에 집중되고 최종 결함과의 상관관계가 생각보다 약하다는 점을 추가로 규명.
- 방법론적으로 GitHub 이벤트 로그(PR 생성/병합 타임스탬프, CI 상태)를 대규모로 마이닝해 인과관계에 가까운 준실험(quasi-experimental) 설계(CI 도입 전후 비교)를 사용 — 저장소 메타데이터만으로 생산성 신호를 뽑아내는 접근법의 좋은 선례.

## 이 프로젝트에 적용한다면 (상세)
- **기존 지표 보완**: 2.1(변경 리드 타임)과 2.3(WIP 관리)는 이 논문의 "PR 처리량" 개념과 밀접하다. 이 논문의 방법론(도입 전/후 비교)을 참고해, 향후 이 프로젝트에서 새로운 CI 파이프라인이나 프로세스 변경(예: 리뷰 정책 변경)을 도입했을 때 "도입 전후 리드타임/처리량 비교"라는 준실험적 분석 틀을 2장 전체의 표준 분석 절차로 제안할 수 있다 — 즉 절대 수치보다 "변화 전후 비교"가 더 신뢰할 수 있는 신호라는 방법론적 근거.
  - 1.3(변경 실패율)의 "CI 실패가 소수 파일에 집중된다"는 후속 발견은, 결함 위험이 특정 모듈에 쏠려 있을 수 있음을 시사하므로 1.4(복잡도 대비 결함 밀도)에 "CI 빌드 실패 빈도가 높은 파일/모듈 목록"을 보조 데이터로 추가하는 것을 제안 — 데이터 소스는 GitLab CI 실패 로그(`🔑 API 필요`).
- **새로 추가할 지표**: 이 프로젝트에도 CI(GitLab CI/Jenkins 등)가 있다면, "CI green 통과율(첫 시도 성공률)"을 1.1(재작업률)의 보조 지표로 추가할 수 있다 — Patchset 재제출과 유사하게, 첫 CI 실행에서 바로 통과하는 비율이 낮으면 초기 구현 완성도 부족 신호로 해석 가능.
- **Goodhart's Law/인사평가 오용 방지 시사점**: 이 논문 자체가 "CI 효과는 생각보다 미묘하다"는 결론으로 끝나며, 단순 상관관계를 인과관계로 과잉 해석하지 말라는 방법론적 경고를 담고 있다. 이는 `developer_evaluation_metrics.md`의 전반적 태도 — "지표 하나로 단정하지 말고 맥락과 함께 해석하라" — 를 학술적으로 뒷받침한다. 특히 저장소 마이닝 기반 지표(1.1~2.3 다수)는 "CI 도입 같은 프로세스 변화가 있으면 이전 기간과 비교 시 전제가 깨진다"는 점을 명시해, 시계열 비교 시 프로세스 변경 이벤트를 반드시 주석으로 남기라는 실무 지침을 추가할 근거가 된다.
