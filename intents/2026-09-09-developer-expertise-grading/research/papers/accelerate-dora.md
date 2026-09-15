# Accelerate: The Science of Lean Software and DevOps (DORA / State of DevOps Report 연구)

- 저자: Nicole Forsgren, Jez Humble, Gene Kim (책); 기반 연구는 Puppet과 공동 수행한 연례 State of DevOps Report(2014-2019, 23,000명 이상 응답, 2,000개 이상 조직)
- 출처/venue/연도: 단행본 "Accelerate" (IT Revolution Press, 2018) — 4년간의 State of DevOps Report 실증 연구를 정리; 2019년 Google이 DORA(DevOps Research and Assessment)를 인수해 현재는 dora.dev에서 방법론을 계속 발전시킴
- 링크: https://itrevolution.com/product/accelerate/ , https://dora.dev/resources/ , https://dora.dev/guides/dora-metrics-four-keys/ , https://nicolefv.com/research

## 핵심 주장 요약
소프트웨어 배포 성과는 설문(Likert 척도), 군집 분석(cluster analysis), 구조방정식모델(SEM) 등 엄밀한 통계 기법으로 측정 가능하며, 이를 4개(현재는 5개) 핵심 지표로 요약할 수 있다: 배포 빈도(Deployment Frequency), 변경 리드 타임(Lead Time for Changes), 변경 실패율(Change Failure Rate), 서비스 복구 시간(Time/Failed Deployment Recovery Time), 그리고 최근 추가된 배포 재작업(Deployment Rework). 핵심 발견은 "속도와 안정성은 트레이드오프가 아니다"라는 것 — 엘리트 성과 조직은 더 빠르면서 동시에 더 안정적이다. 또한 기술적 역량뿐 아니라 Westrum의 생성적(generative) 조직 문화가 배포 성과를 예측하는 강력한 변수임을 실증했다. 이 지표들은 원래 팀/조직 단위로 설계되었으며 개인 단위 적용은 저자들도 권장하지 않는다.

## 주요 발견/모델
- **4(5) Key Metrics**: 배포 빈도, 변경 리드 타임(커밋→프로덕션), 변경 실패율(배포 중 즉각 개입이 필요했던 비율), 복구 시간(장애 발생 후 정상화까지), (신규) 배포 재작업(프로덕션 인시던트로 인한 계획되지 않은 작업).
- 24개 역량(continuous delivery, trunk-based development, loosely coupled architecture 등)이 5개 카테고리에 걸쳐 배포 성과를 예측.
- 엘리트 성과 그룹은 상업적 목표 달성 가능성이 2배 높음.
- Westrum의 생성적 문화(정보가 자유롭게 흐르고 실패를 비난하지 않는 문화)가 배포 성과의 강력한 예측 변수.
- Goodhart's Law 관련 명시적 경고: 임의의 목표(예: "매일 배포해야 함")를 설정하면 지표를 게이밍하게 되므로, 배치 크기를 줄이는 등 원인 개선에 집중해야 하며 조직 간/애플리케이션 간 단순 비교는 지양해야 한다는 가이드가 dora.dev에 명시되어 있음.

## 이 프로젝트에 적용한다면 (상세)
- **기존 지표 보완**: 2.1(변경 리드 타임)은 DORA의 Lead Time for Changes 정의를 그대로 채택하고 있어 정합성이 좋다. 다만 DORA는 "커밋→프로덕션 배포"까지를 재는 반면 문서는 "최초 커밋~Gerrit Merge"까지만 잰다. 실제 프로덕션 배포 시점(GitLab CI/CD 파이프라인의 배포 job 완료 시각)까지 확장하면 DORA 정의와 완전히 일치시킬 수 있다 — 데이터 소스는 GitLab CI API(`🔑 API 필요`).
  - 1.3(변경 실패율)은 이미 DORA의 Change Failure Rate 개념을 차용했지만, DORA의 "배포" 단위가 아니라 "Change/커밋" 단위로 측정되고 있다. 배포 파이프라인이 있다면 배포 단위로 재정의하는 것이 표준 정의에 더 부합한다는 점을 1.3절 보완 대안에 추가 제안.
  - 신규 "배포 재작업(Deployment Rework)" 개념은 1.2(단기 재수정 빈도)와 개념적으로 겹치므로, 1.2절 설명에 "이는 DORA의 Deployment Rework 지표와 상응한다"는 각주를 추가해 근거를 명확히 할 수 있다.
- **새로 추가할 지표**: 개인 단위로는 "배포 빈도" 자체를 직접 적용하기 어렵지만(배포는 팀 단위 이벤트), 개인 기여 Change가 배포 파이프라인에 포함되기까지의 대기 시간(개인 리드타임 중 "배포 대기" 구간)을 2.1의 하위 분해 지표로 추가할 수 있다.
- **Goodhart's Law/인사평가 오용 방지 시사점**: DORA 자체가 "이 지표들은 팀/조직 성과를 위한 것이며 개인을 비교하거나 순위 매기는 데 쓰면 안 된다"고 공식 문서(dora.dev)에서 명시하고 있다. 이는 `developer_evaluation_metrics.md` 5장의 "인사 평가 직접 연동 금지" 원칙과 정확히 같은 입장이며, spec.md의 "범위 밖 — 단일 수치/등급으로 사람을 줄세우는 산출물" 결정을 뒷받침하는 가장 권위 있는 산업 표준 근거로 인용할 수 있다. 또한 "배치 크기를 줄이는 등 원인을 개선하라"는 DORA의 처방은, 1.1(재작업률)이나 2.3(WIP)의 "보완 대안"을 지표 압박이 아니라 "작업 방식 개선을 위한 진단"으로 프레이밍해야 한다는 근거로 활용 가능하다.
