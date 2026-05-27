# AI-IT Skill (AI 기반 IT 실무 역량진단 문제은행 플랫폼)

<div align="center">
  <img src="docs/images/logo.png" width="400" alt="AI-IT Skill Logo">
  <p><b>LangGraph 기반 문제 생성 파이프라인 · RRF Hybrid RAG · Human-in-the-loop 검수 워크플로우 · AI 종합 진단 리포트</b></p>
</div>

---

## 목차

* [1. 프로젝트 개요](#1-프로젝트-개요)
* [2. 개발 배경과 문제 정의](#2-개발-배경과-문제-정의)
* [3. 핵심 기능](#3-핵심-기능)
* [4. 기술 스택](#4-기술-스택)
* [5. 시스템 아키텍처](#5-시스템-아키텍처)
* [6. 전체 서비스 흐름](#6-전체-서비스-흐름)
* [7. AI 문제 생성 파이프라인](#7-ai-문제-생성-파이프라인)
* [8. 문서 기반 Hybrid RAG](#8-문서-기반-hybrid-rag)
* [9. AI 결과 분석 리포트](#9-ai-결과-분석-리포트)
* [10. 데이터베이스 구조](#10-데이터베이스-구조)
* [11. 주요 화면](#11-주요-화면)
* [12. 트러블슈팅](#12-트러블슈팅)
* [13. 현재 구현 범위와 향후 계획](#13-현재-구현-범위와-향후-계획)
* [14. 실행 방법](#14-실행-방법)

---

## 1. 프로젝트 개요

**AI-IT Skill**은 기업 및 교육기관에서 IT 역량진단 문항을 효율적으로 출제하고 응시자의 역량을 다각도로 분석하기 위한 문제은행 플랫폼입니다.

생성형 AI(GPT-4o-mini) 기반의 단순 자유 출제가 유발하는 문항 품질 편차를 제어하기 위해 **LangGraph 상태 에이전트 파이프라인**과 **정량 규칙 기반 Validator**를 구축하였습니다. 또한, 사내 기술 규격이나 PDF 문서를 기반으로 출제 정확성을 확보할 수 있는 **ChromaDB + MariaDB FULLTEXT 기반 RRF Hybrid RAG** 구조를 구현했으며, 응시 결과의 오답 정밀 분석과 동일 이메일 매핑 기반 누적 이력 비교가 가능한 **AI 종합 진단 리포트 엔진**을 통합 제공합니다.

---

## 2. 개발 배경과 문제 정의

### 2.1 개발 배경
IT 역량진단 문제은행은 문항의 난이도 균형, 실무 맥락 반영, 정답 근거의 정합성이 중요합니다. 그러나 관리자가 모든 실무 시나리오(SQL 실행 계획, RAG 검색 품질, LLM 구조화 출력 등)를 직접 작성하는 방식은 시간 소모가 크며 기술 흐름을 신속히 반영하기 어렵습니다.

### 2.2 초기 LLM 자유 생성 방식의 한계와 극복
초기에는 GPT-4o-mini에 주제, 난이도 등 파라미터만 전달해 문제를 자유 생성했으나 다음과 같은 평가 신뢰도 저하 문제가 반복되었습니다.
* **정답 힌트 노출**: "무조건", "필요 없음" 등 오답 소거가 쉬운 단어가 오답지에 빈번하게 삽입됨.
* **정답 선택지 길이 편향**: 정답 선택지에만 부연 설명과 예외 조건이 구체적으로 작성되어 정답지만 비정상적으로 길어짐.
* **해설 복사 붙여넣기**: 정답 선택지의 텍스트를 그대로 어미만 바꾸어 해설란을 채우는 현상 발생.
* **어조 및 종결 어미 혼재**: 문항체(평서문)와 존댓말이 문제 본문 및 선택지 내에 일관성 없이 혼용됨.

본 프로젝트는 단순 프롬프트 튜닝을 넘어, 문제 상황과 평가 의도를 사전 설계서(Blueprint)로 제어하고 생성 결과를 정적/정량 규칙으로 검증하는 **다층 검증 에이전트 시스템**으로 구조화하여 이를 해결했습니다.

---

## 3. 핵심 기능

* **AI 문제 생성 파이프라인**: 템플릿/설계서 기반 생성 및 문서 기반 RAG 생성을 지원하며, LangGraph 에이전트로 생성의 각 흐름을 관리합니다.
* **품질 검증 Validator**: 정답 힌트 정적 검사, 선택지 간 길이 격차 비교, 해설 복사-붙여넣기 탐지(SequenceMatcher 86% 이상 기각), 질문 어조 정제 등을 자동 수행합니다.
* **Hybrid RAG 검색 및 출처 보존**: 의미 유사도 검색(Dense Vector)과 키워드 검색(MariaDB MATCH...AGAINST 전문 검색) 결과를 Reciprocal Rank Fusion(RRF) 알고리즘으로 병합하여 컨텍스트를 구성하고, 출제 시 참조한 chunk 메타데이터를 DB에 보관합니다.
* **Human-in-the-loop 검수 흐름**: AI가 생성한 모든 문제는 `pending` 상태로 우선 저장되며, 관리자가 승인(`approved`)해야 평가 문제은행 풀에 반영됩니다.
* **AI 종합 진단 리포트**: 제출된 응시 기록의 오답을 subtopic 분류기로 분석(RAG, LLM, ModelOps 등)하고 이메일 연계 기반 직전 진단 결과와 비교하여 영역별 성취도(Delta) 및 만성 취약 부문을 마크다운 리포트로 자동 생성합니다.

---

## 4. 기술 스택

* **Frontend**: React, TypeScript, Vite
* **Backend**: FastAPI, Python, SQLAlchemy, Pydantic, LangGraph
* **Database**: MariaDB (정형 데이터 관리 및 MATCH AGAINST FULLTEXT 전문 검색)
* **Vector DB**: ChromaDB (임베딩 및 코사인 유사도 검색)
* **AI Engine**: OpenAI API (GPT-4o-mini, text-embedding-3-small)

---

## 5. 시스템 아키텍처

![System Architecture](docs/images/system-architecture.png)

* React 대시보드에서 문제 생성, 검수, RAG 문서 제어 및 결과 조회 요청을 수행합니다.
* FastAPI 백엔드는 문제 생성 시 LangGraph 엔진을 기동하며, RAG 요청 시 ChromaDB(벡터)와 MariaDB(전문 검색)에 동시 질의합니다.
* 생성된 결과물은 Validator 검증 성공 시 questions 테이블에 `pending`으로 기록되어 관리자의 검수를 대기합니다.

---

## 6. 전체 서비스 흐름

### 6.1 관리자 흐름
1. AI 문제 생성 및 유형(일반/RAG) 선택
2. 생성된 pending 문제 조회, 승인/반려/수정 처리
3. 승인된 문항들로 시험지(Diagnosis) 편성 및 만료 기한 설정 배정
4. 응시자 정보 등록 후 응시 고유 토큰 이메일 발송
5. 제출된 기록 확인 및 AI 진단 리포트 발행 후 결과 공개(이메일 알림 연계)

### 6.2 RAG 문서 관리 흐름
1. PDF/MD 문서 업로드
2. 텍스트 정제(text_cleaner) 및 의미/구조 단위 청킹(text_splitter)
3. MariaDB 청크 저장 및 ChromaDB 임베딩 동시 적재
4. Vector/Keyword/Hybrid 모드별 검색 테스트 및 문제 컨텍스트 피딩

### 6.3 응시자 흐름
1. 메일로 수신한 고유 토큰으로 로그인 및 대기화면 진입
2. 배정된 제한시간 내 객관식 답안 작성 및 시험지 최종 제출
3. 관리자의 결과 공개 처리 후 대시보드에서 합격 여부, 점수, 오답지 해설 및 AI 리포트 확인

---

## 7. AI 문제 생성 파이프라인 (LangGraph & Validator)

### 7.1 LangGraph 워크플로우 설계
문제 생성 라이프사이클을 단위 프로세스로 쪼개고, 결합도가 낮은 노드들로 구성된 `StateGraph`를 기동하여 생성 안정성을 확보했습니다.

```
[START] ──> normalize ──> topic_validation ──> route
                                                 │
                                                 ├──> [question_v2] ──────────┐
                                                 │                            │
                                                 └──> [question_v2_rag] ──> retrieval
                                                                              │
                                                                              ▼
[END] <── save <── validation <── question_generation <───────────────────────┘
```

* **`normalize`**: 입력받은 역량 유형 정규화
* **`topic_validation`**: 설정된 세부 주제와 정규화 도메인의 매핑 연관성 판정
* **`route`**: RAG 모드 여부에 따른 RAG retrieval 노드 진입 조건부 분기
* **`retrieval`**: RRF Hybrid Search를 통한 context 및 증적(Evidence) 조립
* **`question_generation`**: 설계서 프롬프트와 컨텍스트 기반 GPT-4o-mini 문항 작성
* **`validation`**: `validator.py`를 거쳐 일련의 문항 품질 정량 규칙 통과 심사
* **`save`**: 정답 셔플링 후 questions 테이블에 pending 상태 적재

### 7.2 검증 규칙 명세 (`validator.py`)
LLM 생성 시 발생하는 일관성 이탈 문제를 통제하기 위해 다음 규칙들을 런타임에 강제합니다.

* **선택지 길이 균형 (`_validate_answer_length_not_obvious`)**: 정답지가 오답지 평균 길이의 1.8배를 초과하거나 35자 이상 차이 날 경우, 정답지가 정답 단서를 흘리고 있는 것으로 판단하여 탈락시킵니다.
* **정답 힌트 정적 검사 (`_validate_no_answer_leak_patterns`)**: 오답지에 극단적 명제나 명백한 배제어(`ANSWER_LEAK_PATTERNS` 45종)가 침투하는 것을 차단합니다.
* **해설 복사 방지 (`_validate_explanation_not_choice_copy`)**: 정답지 원문과 해설 텍스트 간 `difflib.SequenceMatcher` 유사도가 **86% 이상** 일치하는 복사 어미 변형 문항을 기각합니다.
* **어조 통일 (`_validate_body_polite_question`)**: 문제 본문은 격식체 질문형(`"~습니까?"`)으로 통제하고, 평서문 어미 혼용을 검출합니다.

---

## 8. 문서 기반 Hybrid RAG

의미 유사도 기반의 Dense Vector 검색이 기술 고유명사나 특정 커맨드를 완전 매칭하지 못하는 한계를 보완하기 위해, MariaDB MATCH AGAINST BOOLEAN 전문 검색과 ChromaDB 임베딩 검색을 결합한 하이브리드 엔진을 설계했습니다.

```
[업로드 문서] ──> [Text Cleaner] ──> [Text Splitter] ──> [ChromaDB Vector]
                                                        └──> [MariaDB FULLTEXT]
                                                                     │ (병렬 쿼리)
[RAG 문제 생성] <── [증적 JSON 보존] <── [RRF 병합 정렬] <───────────┘
```

1. **텍스트 전처리 (`text_cleaner.py`)**: NCS 교재 특성상 출제와 무관한 줄("교수학습방법", "수행 Tip", "안전 유의사항")이 포함된 상용구 라인을 제거해 컨텍스트 오염을 최소화합니다.
2. **의미 단락 청킹 (`text_splitter.py`)**: 문단 구조를 유지하기 위해 제목(#) 및 수행준거 매핑 마크다운을 결합하고, 700자 크기에 120자 중첩을 적용해 텍스트를 나눕니다.
3. **RRF 병합 및 랭킹**: 두 스토리지의 스코어 편차를 극복하기 위해 `rrf_score = 1 / (60 + Rank)` 가중치 앙상블을 적용하여 최적의 Top K 컨텍스트를 도출합니다.
4. **RAG 증적 보존 (RAG Evidence)**: 출제 단계에서 쿼리, 검색 모드, top_k 정보와 매칭된 chunk의 ID, 순위, 프리뷰, score 정보를 `rag_evidence_json`에 영구 기록하여, 문제 검수 화면에서 원문 출처를 역추적할 수 있게 설계했습니다.

---

## 9. AI 결과 분석 리포트

진단 제출 후 자동 채점이 완료되면, AI 분석 엔진(`report_service.py`)이 기동하여 응시자의 장오답 경향을 정교하게 해부한 마크다운 분석서를 자동 발급합니다.

* **세부 기술 영역 자동 분류 (`subtopic_classifier.py`)**: 각 문항의 메타 데이터와 텍스트 키워드를 분석하여 오답 문항을 `RAG / LLM / ModelOps / ML / DL / AI 기본` 영역으로 자동 분류 및 구조화합니다.
* **누적 이력 비교 (`history_analyzer.py`)**: 응시자 이메일을 기반으로 직전 완료된 기록을 조회합니다. 두 진단 결과 간의 전체 점수 및 세부 영역별 점수 격차(Delta)를 연산하여 **"성장 영역, 만성 취약 부문, 신규 약점 영역"**을 가려내어 종합 코멘트를 생성합니다.

---

## 10. 데이터베이스 구조

![ERD](docs/images/erd.png)

### 핵심 테이블 명세
* **`questions`**: 진단 문항 테이블
  * `source_type`: 'manual', 'ai'
  * `review_status`: 'pending', 'approved', 'rejected'
  * `ai_generation_type`: 'ai_question_v2' (일반 에이전트 생성), 'ai_question_v2_rag' (RAG 에이전트 생성)
  * `rag_evidence_json`: RAG 검색 시 사용된 출처 정보 일체 보관
* **`result_reports`**: AI 결과 보고서 테이블
  * `subtopic_stats_json`: 도메인 세부 영역별 오답률 분석 스탯
  * `history_comparison_json`: 직전 시험 이력 연계 비교 정보
  * `report_text`: OpenAI 기반으로 작성된 맞춤형 분석 마크다운 텍스트
* **`ai_documents` / `ai_document_chunks`**: RAG 문서 메타 및 파싱 청크 테이블

---

## 11. 주요 화면

### 11.1 관리자 대시보드
![Admin Dashboard](docs/images/admin-dashboard.png)
전체 진단, 문항 통계, 응시자 현황 및 AI 검수 현황을 대시보드에서 조회할 수 있습니다.

### 11.2 AI 문제 생성 화면
![AI Question Generation](docs/images/ai-question-generation.png)
역량 도메인, 난이도, 문제 수, 문제 유형을 선택하여 실시간으로 AI 문제 생성을 요청할 수 있습니다.

### 11.3 AI 문제 검토 화면
![AI Question Review 1](docs/images/ai-question-review1.png)
![AI Question Review 2](docs/images/ai-question-review2.png)
생성된 pending 상태의 문제를 확인하고 승인, 반려, 수정할 수 있으며 생성에 쓰인 RAG 증적도 추적할 수 있습니다.

### 11.4 문제 관리 화면
![Question Management](docs/images/question-management.png)
승인 완료된 기술 문항과 수동 등록된 문항을 통합 조회하고 필터링합니다.

### 11.5 RAG 문서 관리 화면
![RAG Document Management 1](docs/images/rag-document-management1.png)
문서를 업로드하고 텍스트 임베딩을 진행하며, chunk 파싱 결과를 조회합니다.

### 11.6 Hybrid RAG 검색 테스트 화면
![Hybrid RAG Search](docs/images/rag-document-management2.png)
Vector, Keyword, Hybrid 모드별 검색을 직접 수행하고 각각의 스코어 및 병합 결과를 테스트합니다.

### 11.7 응시자 신청 화면
![Applicant Apply](docs/images/applicant-apply.png)
응시자는 본인의 이름, 이메일, 기술 스택 등을 작성하여 진단을 신청할 수 있습니다.

### 11.8 응시자 진단 시험 대기화면
![Applicant Waiting Room](docs/images/applicant-test.png)
시험 유의사항과 제한시간 정보를 조회하고 시험 룸에 입장합니다.

### 11.9 응시자 진단 시험 화면
![Applicant Test](docs/images/applicant-test2.png)
제한시간 카운트다운을 제공하며, 답안을 마킹하고 임시 저장할 수 있습니다.

### 11.10 응시자 시험 종료 화면
![Applicant End](docs/images/applicant-end.png)
시험 최종 제출 처리를 완료하고 로그아웃합니다.

### 11.11 관리자 및 응시자 결과 확인 화면
![Applicant Result 1](docs/images/admin-applicant-detail1.png)
![Applicant Result 2](docs/images/admin-applicant-detail2.png)
응시자 결과 대시보드와 더불어, **AI 종합 진단 리포트 모달** 및 문항별 정오답 상세 마킹 지표를 확인할 수 있습니다.

---

## 12. 트러블슈팅

### 12.1 정답 선택지 길이 불균형으로 인한 힌트 노출 오류
* **문제 상황**: 출제된 객관식 문제에서 정답 선택지에만 구체적인 정보와 예외 조건 등 풍부한 묘사가 포함되어, 정답지가 타 선택지보다 길어져 평가 변별력이 훼손됨.
* **원인**: LLM은 정답 문항을 묘사할 때 오답 선택지를 지어낼 때보다 풍부한 기술적 사실 근거를 동반해 문장을 확장하려는 특성(Bias)이 존재함.
* **해결 방법**: `validator.py` 내부 검증 단계에서 정답 선택지의 길이를 오답지들의 평균 글자 수와 정량적으로 대조하는 `_validate_answer_length_not_obvious` 함수를 추가함. 비율이 **1.8배**를 초과하고 글자 수가 **35자** 이상 격차를 보일 경우 예외를 내고 재시도하도록 조치함.
* **관련 파일**: `backend/ai/questions/validator.py`, `backend/ai/questions/service.py`

### 12.2 의미 기반 벡터 검색 시 정확 키워드 누락 문제
* **문제 상황**: RAG 기반 문제 생성 시 `explain`, `filesort`, `vllm` 등 기술 고유 명사가 Dense Vector Search에서 누락되어 문제 출제 컨텍스트에 엉뚱한 정보가 결합하는 오류 발생.
* **원인**: 고밀도 임베딩 유사도 점수는 문장의 의미 유사도를 우선하므로, 고유 명사나 커맨드 형태의 예약어 등 완전 일치 매칭 강도가 취약함.
* **해결 방법**: MariaDB `FULLTEXT INDEX`를 구축하고 `MATCH AGAINST` 전문 검색을 추가로 탑재함. 두 검색 엔진의 랭크 편향을 상쇄하고 적합도를 보장하기 위해 **RRF(Reciprocal Rank Fusion)** 알고리즘을 활용하여 랭킹 결합한 Top K 문단 조각을 조립함.
* **관련 파일**: `backend/ai/rag/document_service.py`, `backend/ai/rag/vector_store.py`

### 12.3 PDF 파싱 청크 내의 무효 교육용 가이드라인 개입 오류
* **문제 상황**: 국가직무능력표준(NCS)이나 공식 교재 PDF 문서를 임베딩할 때 "안전 유의사항", "평가지", "교수학습방법" 등 문제 출제와 직접 관련이 없는 교육 안내용 텍스트 청크가 RAG 검색 상위에 빈번하게 노출됨.
* **원인**: PDF 교재 특유의 목차 구조 및 가이드 서식이 단어 분포상 고유 기술 용어와 엮여 높은 임베딩 유사도로 오검출됨.
* **해결 방법**: 파싱 단에서 불필요한 고정 키워드 행을 일체 거르는 `text_cleaner.py` 가공 필터를 추가함. 더불어 검색 런타임 중에도 `_is_noise_context` 함수를 배치하여 안내성 단어가 밀집되고 정보성 단어 비중이 낮을 경우 컨텍스트에서 최종 배제시킴.
* **관련 파일**: `backend/ai/rag/text_cleaner.py`, `backend/ai/rag/document_service.py`

---

## 13. 현재 구현 범위와 향후 계획

### 13.1 현재 구현된 내용
* LangGraph 기반 상태 에이전트 문제 생성 파이프라인
* ChromaDB Vector Search + MariaDB MATCH AGAINST FULLTEXT 및 RRF 기반 Hybrid Search
* 선택지 편향, 정답 힌트 누출, 해설 복사-붙여넣기를 방지하는 정량 규칙 Validator
* RAG 생성 이력 및 원문 출처(chunk ID, Score 등) 증적 영구 보관 구조
* 6대 기술 분야 subtopic 자동 분류 및 누적 이력 비교 종합 마크다운 보고서 생성 엔진
* Human-in-the-loop 검수 관리자 대시보드 웹 어플리케이션 및 응시자 평가 연동 시스템

### 13.2 한계 및 향후 로드맵
* **문제 유형 제한성 (부분 구현)**: 백엔드 V2 파이프라인 내부 검증 로직은 현재 객관식(`multiple_choice`)만 최종 처리하도록 되어 있습니다. 향후 주관식 서술형 및 코딩 작성형 문제 생성 로직과 채점 프레임워크를 고도화할 예정입니다.
* **Reranker 미도입 (향후 계획)**: 하이브리드 검색 컨텍스트의 순위를 한 번 더 정밀하게 다듬기 위해, Cross-Encoder 기반의 Reranker 모델 연동을 구상하고 있습니다.
* **Approved 데이터 기반 Fine-tuning (향후 계획)**: 관리자 검수를 마친 `approved` 문제 데이터를 수집/가공하여 오픈소스 LLM(Llama 등)을 파인튜닝하고 사내 서버에 자체 서빙(vLLM)하는 파이프라인 구축을 검토 중입니다.
* **서술형 AI 채점 (향후 계획)**: 주관식 서술형 문항의 자동 채점 신뢰도 확보를 위한 프롬프트 가이드라인 설계 및 AI 채점 모듈을 준비 중입니다.

---

## 14. 실행 방법

### 14.1 환경 변수 설정
`backend/.env` 파일을 아래의 설정을 참고하여 생성합니다.

```env
DATABASE_URL=mysql+pymysql://mariadb_user:password@localhost:3306/itskilldb
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
CHROMA_DB_PATH=./chroma_db
CHROMA_COLLECTION_NAME=ai_question_documents
```

### 14.2 DB 구축 및 시딩
최초 실행 시 데이터베이스 스키마를 구성하고 기본 마스터 데이터와 진단 문항을 로드합니다.

```bash
cd backend
# Python 가상환경 생성 및 활성화
python -m venv itskill_venv
itskill_venv\Scripts\activate

# 가상환경 내 의존성 패키지 설치
pip install -r requirements.txt

# DB 초기 구축 및 마스터/더미 데이터 로드
python recreate_db.py
python seed.py
```

### 14.3 백엔드 uvicorn 구동
```bash
# uvicorn API 서버 구동 (8000번 포트 활성화)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 14.4 프론트엔드 구동
루트 디렉토리로 이동하여 로컬 개발 서버를 기동합니다.

```bash
# npm 패키지 설치
npm install

# Vite 개발 서버 구동 (5173번 포트 활성화)
npm run dev
```
