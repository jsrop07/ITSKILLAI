<div align="center">
  <h1>AI-IT Skill<br />AI 기반 IT 실무 역량진단 문제은행 플랫폼</h1>
  <div align="center" style="margin: 16px 0 20px 0">
    <img src="docs/images/logo.png" width="400" alt="AI-IT Skill Logo">
  </div>
  <b>AI-Powered IT Competency Diagnosis & Question Bank System</b>
  <p>설계서 기반 AI 문항 생성 · LIKE 기반 Hybrid RAG MVP · Human-in-the-loop 검수 워크플로우 · 실무 시나리오 기반 IT 역량진단</p>
</div>

<br />

## 목차

* [1. 프로젝트 개요](#1-프로젝트-개요)
* [2. 개발 배경과 문제 정의](#2-개발-배경과-문제-정의)
* [3. 핵심 기능](#3-핵심-기능)
* [4. 기술 스택](#4-기술-스택)
* [5. 전체 시스템 아키텍처](#5-전체-시스템-아키텍처)
* [6. 화면 흐름도](#6-화면-흐름도)
* [7. AI 문제 생성 파이프라인](#7-ai-문제-생성-파이프라인)
* [8. 설계서/템플릿 기반 문제 생성 구조](#8-설계서템플릿-기반-문제-생성-구조)
* [9. 문서 기반 RAG 문제 생성 구조](#9-문서-기반-rag-문제-생성-구조)
* [10. Hybrid RAG MVP 구현](#10-hybrid-rag-mvp-구현)
* [11. 데이터 구조 및 ERD](#11-데이터-구조-및-erd)
* [12. 주요 화면](#12-주요-화면)
* [13. 트러블슈팅](#13-트러블슈팅)
* [14. 현재 구현 범위와 한계](#14-현재-구현-범위와-한계)
* [15. 향후 고도화 계획](#15-향후-고도화-계획)
* [16. 실행 방법](#16-실행-방법)
* [17. 핵심 성과](#17-핵심-성과)

---

## 1. 프로젝트 개요

AI-IT Skill은 기업 또는 교육기관에서 사용할 수 있는 IT 실무 역량진단 문제은행 플랫폼입니다.

단순히 문제를 등록하고 응시 결과를 확인하는 CRUD형 문제은행이 아니라, 관리자가 AI를 활용해 IT 역량별 문제를 생성하고, 생성된 문제를 검수한 뒤 실제 진단에 사용할 수 있도록 설계한 시스템입니다.

특히 본 프로젝트는 다음 두 가지 문제 생성 방식을 함께 제공합니다.

| 생성 방식               | 설명                                              | 주요 목적          |
| ------------------- | ----------------------------------------------- | -------------- |
| 설계서/템플릿 기반 AI 문제 생성 | 사전에 정의된 문제 형식과 고급 문제 템플릿을 기반으로 LLM이 선택지와 해설을 생성 | 고급 문제 품질 안정화   |
| 문서 기반 RAG 문제 생성     | 업로드한 문서를 검색하고, 검색된 chunk를 context로 사용해 문제 생성    | 문서 근거 기반 문제 생성 |

생성된 문제는 바로 확정되지 않고 `pending` 상태로 저장되며, 관리자가 검수 후 승인해야 문제은행에 반영됩니다. 이를 통해 AI 생성 결과를 사람의 검수 흐름과 결합하는 Human-in-the-loop 구조를 구성했습니다.

---

## 2. 개발 배경과 문제 정의

### 2.1 왜 이 프로젝트를 만들었는가

IT 역량진단 문제은행은 단순히 문제 수가 많다고 좋은 시스템이 아닙니다. 실제 역량을 평가하려면 문제의 난이도, 실무 맥락, 정답 근거, 오답 품질이 모두 중요합니다.

하지만 관리자가 모든 문제를 직접 작성하는 방식에는 한계가 있습니다.

* 역량별 문제를 수작업으로 작성하는 데 시간이 많이 걸림
* 고급 문제일수록 실무 상황과 제약 조건을 설계하기 어려움
* SQL 실행 계획, RAG 검색 품질, LLM 구조화 출력, Agent workflow 같은 최신 기술 주제를 지속적으로 반영하기 어려움
* 문제 수가 늘어날수록 난이도와 품질을 일관되게 유지하기 어려움
* AI를 그대로 사용하면 정답/해설 불일치, 쉬운 오답, 근거 부족 문제가 발생할 수 있음

따라서 본 프로젝트는 단순한 문제은행을 넘어, AI 문제 생성과 관리자 검수 흐름을 결합한 IT 역량진단 플랫폼을 목표로 개발했습니다.

### 2.2 초기 LLM 자유 생성 방식의 한계

초기에는 GPT-4o-mini에 다음과 같은 정보만 전달해 문제를 생성했습니다.

| 입력값             | 예시              |
| --------------- | --------------- |
| topic           | RAG 검색 품질       |
| difficulty      | 고급              |
| count           | 5               |
| competency_type | ai              |
| question_type   | multiple_choice |

하지만 단순 자유 생성 방식에서는 다음 문제가 반복적으로 발생했습니다.

| 문제          | 실제 발생한 현상                                                |
| ----------- | -------------------------------------------------------- |
| 고급 문제 품질 부족 | 고급 문제인데 단순 정의형 또는 일반론 문제로 생성됨                            |
| 선택지 품질 저하   | “무조건 증가시킨다”, “필요 없다”, “모든 컬럼에 인덱스를 추가한다”처럼 쉽게 제거되는 오답 생성 |
| 정답 위치 편향    | 정답이 1번 또는 2번에 몰림                                         |
| 정답/해설 불일치   | answer 값과 explanation의 정답 번호가 다름                         |
| 근거 부족       | AI/RAG 문제인데 query, top_k, chunk, similarity 같은 검색 근거가 없음 |
| 역량별 형식 불일치  | SQL 문제인데 SQL 쿼리나 실행 계획 없이 일반론으로 생성됨                      |
| 문체 불일치      | 문제 본문과 선택지는 문항체여야 하는데 존댓말과 반말이 섞임                        |

이 문제를 해결하기 위해 단순히 프롬프트를 길게 만드는 방식이 아니라, 문제 생성 구조 자체를 단계적으로 개선했습니다.

---

## 3. 핵심 기능

### 3.1 관리자 기반 문제은행 관리

관리자는 문제를 생성, 검토, 승인, 반려, 수정할 수 있습니다.

주요 기능은 다음과 같습니다.

* 전체 문제 목록 조회
* 문제 상세 확인
* 문제 생성 방식 확인
* 생성일시 확인
* 검수 상태 관리
* 문제 승인/반려
* 진단에 사용할 문제 관리

### 3.2 AI 문제 생성

관리자는 역량 유형, 난이도, 문제 수, 문제 유형을 선택해 AI 문제를 생성할 수 있습니다.

지원하는 주요 역량 유형은 다음과 같습니다.

| 역량 유형                    | 설명                                 |
| ------------------------ | ---------------------------------- |
| software_engineering     | 요구사항, 설계, 테스트, 품질, 유지보수            |
| java                     | Java 문법, 객체지향, 컬렉션, 예외 처리          |
| python                   | Python 문법, 자료형, 예외 처리, 코드 실행 결과    |
| c_language               | 포인터, 배열, 문자열, 동적 메모리               |
| sql                      | SELECT, JOIN, GROUP BY, 인덱스, 실행 계획 |
| data_structure_algorithm | 자료구조, 알고리즘, 시간복잡도                  |
| security                 | 인증, 인가, 취약점, 보안 설계                 |
| ai                       | LLM, RAG, 임베딩, 평가 지표, 검색 품질        |

### 3.3 설계서/템플릿 기반 고급 문제 생성

AI 또는 SQL 고급 문제는 LLM 자유 생성에만 의존하지 않고, 사전에 정의된 템플릿과 문제 의도 정보를 사용합니다.

핵심 구조는 다음과 같습니다.

* `question_templates.py`가 문제의 body와 평가 상황을 제공
* `answer_intent`로 정답 선택지의 핵심 의도 정의
* `distractor_intents`로 오답 선택지의 방향 정의
* LLM은 title/body를 새로 만드는 것이 아니라 choices와 explanation을 생성
* validator가 선택지 품질과 정답 정합성을 검증
* 실패 시 retry 또는 fallback choices 사용

이 구조를 통해 LLM의 자유도를 줄이고, 고급 문제의 실무 맥락과 평가 포인트를 안정적으로 유지했습니다.

### 3.4 문서 기반 RAG 문제 생성

관리자는 PDF 또는 Markdown 문서를 업로드하고, 해당 문서를 기반으로 문제를 생성할 수 있습니다.

문서 기반 문제 생성 흐름은 다음과 같습니다.

1. 문서 업로드
2. 텍스트 추출
3. 노이즈 제거
4. chunk 분리
5. 임베딩 생성
6. ChromaDB 저장
7. 검색 query 기반 Hybrid RAG 검색
8. 검색 context 구성
9. GPT-4o-mini 문제 생성
10. validator 검증
11. pending 저장
12. 관리자 검수

문서 기반 RAG 생성은 설계서 기반 문제보다 문제 형식의 안정성은 낮을 수 있지만, 업로드된 문서 근거를 활용해 문제를 생성한다는 장점이 있습니다.

### 3.5 Hybrid RAG MVP

기존 Vector RAG는 의미적으로 유사한 문서를 찾는 데는 유리하지만, 정확히 일치해야 하는 기술 키워드를 놓칠 수 있습니다.

예를 들어 다음과 같은 키워드는 의미 유사도보다 정확 매칭이 중요합니다.

* EXPLAIN
* filesort
* top_k
* metadata_filter
* reranker
* vector_score
* keyword_score
* hybrid_score

이를 보완하기 위해 현재 프로젝트에서는 ChromaDB vector search와 MariaDB LIKE 기반 keyword search를 결합한 Hybrid RAG MVP를 구현했습니다.

정확한 표현은 다음과 같습니다.

| 구분             | 현재 상태                           |
| -------------- | ------------------------------- |
| Vector Search  | ChromaDB 기반 구현                  |
| Keyword Search | MariaDB LIKE 기반 구현              |
| Hybrid Score   | vector_score와 keyword_score 가중합 |
| BM25           | 미구현, 향후 계획                      |
| FULLTEXT       | 미구현, 향후 계획                      |
| Reranker       | 미구현, 향후 계획                      |
| LangGraph      | 미구현, 향후 계획                      |

현재 구현은 BM25나 reranker까지 적용한 완성형 Hybrid Search가 아니라, LIKE 기반 keyword search를 결합한 Hybrid RAG MVP입니다.

### 3.6 관리자 검수 흐름

AI가 생성한 문제는 바로 서비스에 반영되지 않고 `pending` 상태로 저장됩니다.

관리자는 AI 문제 검토 화면에서 문제를 확인한 뒤 다음 작업을 수행할 수 있습니다.

* 승인
* 반려
* 수정
* 문제 관리 화면에서 확인

이를 통해 AI 생성 결과를 그대로 신뢰하지 않고, 최종 품질 판단은 관리자가 수행하는 Human-in-the-loop 구조를 적용했습니다.

### 3.7 생성 방식 및 생성일시 표시

생성된 문제가 어떤 방식으로 만들어졌는지 화면에서 확인할 수 있도록 개선했습니다.

| 표시값       | 의미                       |
| --------- | ------------------------ |
| 설계서 기반    | 일반 AI 생성 또는 템플릿 기반 생성    |
| 문서 기반 RAG | 업로드 문서 검색 context 기반 생성  |
| 수동/기존     | 기존 등록 문제 또는 생성 방식이 없는 문제 |

AI 문제 검토, AI 문제 생성 결과, 문제 관리 화면에서 생성 방식과 생성일시를 확인할 수 있습니다.

---

## 4. 기술 스택

| 영역             | 기술                                                  |
| -------------- | --------------------------------------------------- |
| Frontend       | React, TypeScript, Vite                             |
| Backend        | FastAPI, Python, SQLAlchemy, Pydantic               |
| Database       | MariaDB                                             |
| Vector DB      | ChromaDB                                            |
| LLM            | OpenAI GPT-4o-mini                                  |
| Embedding      | OpenAI text-embedding-3-small                       |
| RAG Search     | ChromaDB Vector Search, MariaDB LIKE Keyword Search |
| Admin Workflow | pending / approved / rejected 검수 흐름                 |
| API Test       | Swagger                                             |

---

## 5. 전체 시스템 아키텍처

본 시스템은 관리자 화면, FastAPI 백엔드, AI 문제 생성 서비스, RAG 검색 서비스, MariaDB, ChromaDB, OpenAI API로 구성됩니다.

### 5.1 아키텍처 이미지

![System Architecture](docs/images/system-architecture.png)

이미지 설명:

* React 기반 관리자 화면에서 문제 생성/검토/문서 관리 요청
* FastAPI가 문제 생성 요청을 처리
* 설계서 기반 생성은 question_templates.py와 question_choice_generator.py를 사용
* 문서 기반 생성은 Hybrid RAG 검색 후 GPT-4o-mini로 문제 생성
* 생성된 문제는 questions 테이블에 pending 상태로 저장
* 관리자는 검토 후 approved 또는 rejected 처리

### 5.2 핵심 구성 요소

| 구성 요소                         | 역할                                               |
| ----------------------------- | ------------------------------------------------ |
| Frontend                      | 관리자 대시보드, AI 문제 생성, 문제 검토, 문제 관리, RAG 문서 관리      |
| FastAPI Router                | 프론트 요청을 받아 서비스 계층으로 전달                           |
| Question Generator            | 문제 생성 흐름 제어                                      |
| Question Templates            | 고급 문제 body, answer_intent, distractor_intents 제공 |
| Question Choice Generator     | LLM을 사용해 choices와 explanation 생성                 |
| Question Validator            | 문제 구조, 정답, 해설, 선택지 품질 검증                         |
| RAG Document Service          | 문서 업로드, chunk 저장, 검색 context 구성                  |
| Vector Store Service          | ChromaDB 기반 vector search                        |
| Keyword Search                | MariaDB LIKE 기반 keyword search                   |
| MariaDB                       | 문제, 문서, chunk, 진단, 응시 기록 저장                      |
| ChromaDB                      | 문서 chunk embedding 저장                            |
| OpenAI GPT-4o-mini            | 문제 생성 및 해설 생성                                    |
| OpenAI text-embedding-3-small | 문서 및 query embedding 생성                          |

---

## 6. 화면 흐름도

관리자와 응시자의 화면 흐름은 분리되어 있습니다.

### 6.1 화면 흐름도 이미지

![Screen Flow](docs/images/screen-flow.svg)

### 6.2 관리자 흐름

1. 로그인
2. 관리자 대시보드 접근
3. AI 문제 생성
4. 설계서 기반 또는 문서 기반 RAG 생성 선택
5. 생성된 문제 pending 저장
6. AI 문제 검토
7. 승인/반려/수정
8. 문제 관리 화면 반영
9. 진단 구성
10. 응시자에게 진단 배정

### 6.3 RAG 문서 관리 흐름

1. RAG 문서 관리 화면 접근
2. PDF 또는 Markdown 문서 업로드
3. 텍스트 추출 및 전처리
4. chunk 분리
5. embedding 생성
6. MariaDB와 ChromaDB 저장
7. vector / keyword / hybrid 검색 테스트
8. 문서 기반 문제 생성

### 6.4 응시자 흐름

1. 응시자 로그인 또는 진단 접근
2. 배정된 진단 선택
3. 문제 풀이
4. 답안 제출
5. 결과 저장
6. 관리자가 응시 기록 확인

---

## 7. AI 문제 생성 파이프라인

### 7.1 전체 흐름

AI 문제 생성은 단순히 LLM에게 모든 문제를 자유롭게 작성시키는 방식이 아닙니다.

현재 문제 생성은 다음 흐름으로 구성됩니다.

1. 사용자 입력 수신
2. competency_type 정규화
3. 난이도와 역량에 따라 생성 경로 선택
4. 설계서 또는 템플릿 기반 문제 구조 구성
5. GPT-4o-mini를 통한 choices/explanation 생성
6. validator 검증
7. 정답 위치 재배치
8. 해설 정리
9. questions 테이블 pending 저장
10. 관리자 검수

### 7.2 생성 방식 구분

| 생성 방식        | 사용 조건        | 특징                                        |
| ------------ | ------------ | ----------------------------------------- |
| 설계서 기반 생성    | 일반 AI 문제 생성  | 문제 형식과 평가 포인트를 먼저 설계                      |
| 템플릿 기반 고급 생성 | AI/SQL 고급 문제 | body는 템플릿 고정, LLM은 choices/explanation 생성 |
| 문서 기반 RAG 생성 | 문서 검색 기반 문제  | 검색 context를 기반으로 문제 생성                    |

### 7.3 설계서 기반 생성이 필요한 이유

초기 자유 생성에서는 LLM이 문제를 그럴듯하게 작성하더라도 실제 평가 품질이 불안정했습니다.

예를 들어 “RAG 검색 품질”이라는 주제를 주면, LLM은 다음처럼 일반적인 문제를 만들 수 있습니다.

* RAG의 장점은 무엇인가?
* 검색 품질을 높이는 방법은 무엇인가?
* 벡터 검색이 중요한 이유는 무엇인가?

이런 문제는 고급 역량진단 문제로는 부족합니다.

따라서 먼저 다음 항목을 정의하는 방식으로 바꿨습니다.

| 설계 항목                | 설명                        |
| -------------------- | ------------------------- |
| question_format      | 문제 형식                     |
| target_concept       | 평가할 핵심 개념                 |
| scenario             | 실무 상황                     |
| constraints          | 문제 조건                     |
| evidence_type        | 필요한 근거 유형                 |
| evidence_detail      | body에 포함되어야 할 코드/쿼리/검색 로그 |
| answer_decision_rule | 정답 판단 기준                  |
| distractor_strategy  | 오답 구성 방향                  |

이렇게 하면 LLM이 자유롭게 문제를 만드는 것이 아니라, 설계된 평가 구조 안에서 문제를 생성하게 됩니다.

---

## 8. 설계서/템플릿 기반 문제 생성 구조

### 8.1 템플릿 기반 생성이란?

AI와 SQL 고급 문제는 자유 생성보다 더 강한 제어가 필요했습니다.

따라서 `question_templates.py`에 고급 문제의 기본 body와 평가 상황을 코드로 정의했습니다.

템플릿은 다음 정보를 포함합니다.

| 필드                 | 역할                      |
| ------------------ | ----------------------- |
| title              | 문제 제목                   |
| body               | 문제 본문, 실무 상황, 로그, 제약 조건 |
| choices            | fallback 선택지            |
| answer             | fallback 정답             |
| explanation        | fallback 해설             |
| template_format    | 문제 유형                   |
| answer_intent      | 정답 선택지가 만족해야 하는 핵심 의도   |
| distractor_intents | 오답 선택지의 방향              |
| competency_tags    | 문제 태그                   |

### 8.2 LLM이 바꾸는 부분과 바꾸지 않는 부분

템플릿 기반 생성에서 LLM이 문제 전체를 마음대로 작성하지 않습니다.

| 항목                 | 생성 주체          | 설명                                         |
| ------------------ | -------------- | ------------------------------------------ |
| title              | 코드             | template_format에 따라 제목 variant 선택          |
| body               | 템플릿            | 문제 상황과 로그는 고정                              |
| choices            | LLM            | answer_intent와 distractor_intents를 바탕으로 생성 |
| answer             | LLM 생성 후 검증/보정 | 정답 위치는 이후 재배치 가능                           |
| explanation        | LLM 생성 후 재정리   | 정답 번호와 문체 정리                               |
| template_format    | 코드             | 문제 다양성 확보                                  |
| answer_intent      | 템플릿            | 정답 방향 제어                                   |
| distractor_intents | 템플릿            | 오답 방향 제어                                   |

즉, LLM은 출제자 전체 역할이 아니라, 이미 구성된 문제 body에 맞는 선택지와 해설을 작성하는 역할을 수행합니다.

### 8.3 예시: RAG 검색 품질 고급 문제

요청값:

| 항목              | 값         |
| --------------- | --------- |
| topic           | RAG 검색 품질 |
| difficulty      | 고급        |
| competency_type | ai        |
| count           | 5         |

선택된 template_format 예시:

| template_format             | 평가 포인트                                 |
| --------------------------- | -------------------------------------- |
| hybrid_search_choice        | vector search 한계와 keyword search 결합 판단 |
| context_filtering           | 검색 chunk를 LLM context로 넘기기 전 근거 적합성 판단 |
| query_rewrite_failure       | query rewrite가 과도하게 일반화되는 문제           |
| retrieval_quality_diagnosis | category가 다른 chunk가 검색 결과에 섞이는 문제      |
| chunking_issue              | chunk_size, overlap, 의미 단위 분할 문제       |

이 방식으로 같은 “RAG 검색 품질” 주제 안에서도 서로 다른 평가 포인트를 가진 문제를 생성할 수 있습니다.

### 8.4 answer_intent와 distractor_intents

예를 들어 `hybrid_search_choice` 문제의 answer_intent가 다음과 같다고 가정합니다.

`combine_vector_keyword_and_metadata_filter`

이 경우 정답 선택지는 다음 내용을 포함해야 합니다.

* vector search
* keyword search
* metadata_filter
* 검색 결과 결합 또는 hybrid search

반면 distractor_intents는 다음과 같은 오답 방향을 만듭니다.

| distractor_intent                   | 오답 방향                              |
| ----------------------------------- | ---------------------------------- |
| increase_vector_top_k_only          | top_k만 늘리는 선택지                     |
| replace_embedding_model_only        | embedding 모델 교체만 고려하는 선택지          |
| reranker_only_without_candidate_fix | 후보군 문제를 해결하지 않고 reranker만 적용하는 선택지 |
| simplify_query_for_latency_only     | 검색 속도만 보고 query를 단순화하는 선택지         |

이 구조를 통해 정답과 오답의 방향을 LLM에게 명확히 전달하고, validator가 정답 선택지의 핵심 키워드 누락 여부를 검사할 수 있습니다.

### 8.5 실패 처리

LLM이 선택지를 생성했지만 검증을 통과하지 못하면 다음 흐름으로 처리합니다.

1. choices/explanation 생성
2. answer_intent 기준 검증
3. 실패 시 retry
4. retry도 실패하면 템플릿 fallback choices/explanation 사용
5. validate_questions 최종 검증
6. pending 저장

이 구조 덕분에 일부 선택지 생성이 실패해도 전체 문제 생성 요청이 실패하지 않도록 안정성을 높였습니다.

---

## 9. 문서 기반 RAG 문제 생성 구조

### 9.1 문서 기반 생성 목적

문서 기반 RAG 문제 생성은 업로드한 문서의 내용을 근거로 문제를 생성하기 위한 기능입니다.

이 방식은 설계서 기반 문제보다 문제 형태는 덜 안정적일 수 있지만, 다음 목적에 유용합니다.

* 특정 문서 기반 문제 생성
* 사내 기술 문서 기반 진단 문제 생성
* NCS 문서 기반 문제 생성
* 공식 문서나 기준 문서에 근거한 문제 생성
* LLM 일반 지식이 아닌 검색 context 기반 생성

### 9.2 문서 인덱싱 흐름

문서 인덱싱은 다음 순서로 동작합니다.

1. 관리자가 문서 업로드
2. PDF 또는 Markdown 텍스트 추출
3. 불필요한 노이즈 제거
4. 의미 단위 chunk 분리
5. chunk에 metadata 추가
6. OpenAI text-embedding-3-small로 embedding 생성
7. chunk 원문과 metadata는 MariaDB에 저장
8. embedding은 ChromaDB에 저장

### 9.3 chunk metadata

각 chunk에는 검색 품질을 높이기 위해 metadata를 함께 저장합니다.

| metadata       | 설명            |
| -------------- | ------------- |
| document_title | 문서 제목         |
| source_type    | 문서 출처 유형      |
| category       | 역량 유형         |
| chunk_index    | 문서 내 chunk 순서 |

검색 시 category filter를 사용해 현재 생성하려는 역량과 관련된 문서만 검색할 수 있습니다.

### 9.4 문서 기반 문제 생성 흐름

1. 관리자가 topic, difficulty, top_k, competency_type, search_query 입력
2. backend가 Hybrid RAG 검색 수행
3. vector search와 keyword search 결과 병합
4. hybrid_score 기준 상위 chunk 선택
5. context 구성
6. GPT-4o-mini에 context 전달
7. 문제 생성
8. validator 검증
9. 정답 위치 재배치
10. questions 테이블 pending 저장

---

## 10. Hybrid RAG MVP 구현

### 10.1 기존 Vector RAG 구조

초기 RAG 구조는 다음과 같았습니다.

1. 문서 업로드
2. chunk 분리
3. embedding 생성
4. ChromaDB 저장
5. query embedding 생성
6. vector similarity 기반 검색
7. context 구성
8. 문제 생성

Vector Search는 의미적으로 유사한 문서를 찾는 데 유리하지만, 정확 키워드 검색에는 한계가 있습니다.

### 10.2 Vector RAG의 한계

실제 테스트에서 다음 문제가 발생했습니다.

| 문제            | 설명                                                       |
| ------------- | -------------------------------------------------------- |
| 정확 키워드 누락     | EXPLAIN, filesort, metadata_filter 같은 키워드가 검색에서 누락될 수 있음 |
| category 불일치  | 검색 의도와 다른 category의 chunk가 섞일 수 있음                       |
| similarity 한계 | similarity가 높아도 실제 문제 생성 근거로는 부적절할 수 있음                  |
| chunk 노이즈     | PDF 안내 문구, 수행 tip, 장비, 안전유의사항 등이 검색될 수 있음                |

### 10.3 LIKE 기반 Keyword Search 결합

이를 보완하기 위해 MariaDB LIKE 기반 keyword search를 추가했습니다.

현재 Hybrid RAG MVP는 다음 두 검색 결과를 결합합니다.

| 검색 방식                       | 역할                   |
| --------------------------- | -------------------- |
| ChromaDB Vector Search      | 의미적으로 유사한 chunk 검색   |
| MariaDB LIKE Keyword Search | 정확 키워드가 포함된 chunk 검색 |

### 10.4 Hybrid Score 계산

검색 결과는 chunk_id 기준으로 병합하고, 다음 점수를 계산합니다.

| 점수            | 설명                               |
| ------------- | -------------------------------- |
| vector_score  | vector search 유사도 기반 점수          |
| keyword_score | keyword search 매칭 기반 점수          |
| hybrid_score  | vector_score와 keyword_score의 가중합 |

현재 MVP에서는 다음 가중치를 사용합니다.

hybrid_score = vector_score × 0.7 + keyword_score × 0.3

### 10.5 검색 모드

문서 검색 테스트에서는 다음 모드를 지원합니다.

| search_mode | 설명                                |
| ----------- | --------------------------------- |
| vector      | ChromaDB vector search만 사용        |
| keyword     | MariaDB LIKE keyword search만 사용   |
| hybrid      | vector search와 keyword search를 결합 |

### 10.6 현재 구현의 정확한 범위

현재 구현은 “LIKE 기반 keyword search를 결합한 Hybrid RAG MVP”입니다.

아직 구현되지 않은 것:

* BM25
* MariaDB FULLTEXT 기반 ranking
* reranker
* LangGraph workflow
* fine-tuning
* QLoRA
* vLLM 자체 서빙

이 기능들은 향후 고도화 계획으로 분리했습니다.

---

## 11. 데이터 구조 및 ERD

### 11.1 ERD 이미지

![ERD](docs/images/erd.png)

본 ERD는 실제 서비스 흐름을 설명하기 위한 주요 테이블 중심의 개념 ERD입니다. 일부 관계는 실제 Foreign Key가 아니라 애플리케이션 레벨에서 관리될 수 있습니다.

### 11.2 핵심 테이블

| 테이블                | 역할                                |
| ------------------ | --------------------------------- |
| questions          | 문제 본문, 선택지, 정답, 해설, 난이도, 검수 상태 저장 |
| ai_documents       | 업로드 문서 메타데이터 저장                   |
| ai_document_chunks | 문서 chunk 원문과 metadata 저장          |
| applicants         | 응시자 정보 저장                         |
| diagnoses          | 진단 시험 정보 저장                       |
| records            | 응시 결과 저장                          |
| record_answers     | 응시자별 문제 답안 저장                     |

### 11.3 questions 테이블 주요 필드

| 필드                 | 설명                            |
| ------------------ | ----------------------------- |
| id                 | 문제 ID                         |
| title              | 문제 제목                         |
| body               | 문제 본문                         |
| choices            | 객관식 선택지                       |
| answer             | 정답                            |
| explanation        | 해설                            |
| difficulty         | 난이도                           |
| score              | 배점                            |
| competency_type    | 역량 유형                         |
| source_type        | 문제 출처                         |
| ai_generation_type | 설계서 기반 / 문서 기반 RAG 구분         |
| review_status      | pending / approved / rejected |
| created_at         | 생성일시                          |
| updated_at         | 수정일시                          |

### 11.4 AI 문서 관련 테이블

| 테이블                 | 주요 역할                                           |
| ------------------- | ----------------------------------------------- |
| ai_documents        | 문서 제목, 출처, category, 파일 경로 저장                   |
| ai_document_chunks  | chunk 내용, chunk_index, category, document_id 저장 |
| ChromaDB collection | chunk embedding 저장 및 vector search 수행           |

---

## 12. 주요 화면
관리자 화면과 응시자 화면 기준입니다.

### 12.1 관리자 대시보드

![Admin Dashboard](docs/images/admin-dashboard.png)

관리자는 전체 진단, 문제, 응시자, 검수 현황을 확인할 수 있습니다.

### 12.2 AI 문제 생성 화면


![AI Question Generation](docs/images/ai-question-generation.png)

역량 유형, 난이도, 문제 수, 문제 유형을 선택해 AI 문제를 생성할 수 있습니다.

### 12.3 AI 문제 검토 화면

![AI Question Review](docs/images/ai-question-review1.png)
![AI Question Review](docs/images/ai-question-review2.png)

AI가 생성한 pending 문제를 확인하고 승인, 반려, 수정할 수 있습니다. 생성 방식과 생성일시도 함께 표시됩니다.

### 12.4 문제 관리 화면

![Question Management](docs/images/question-management.png)

기본 및 필터링을 통해 승인된 문제와 기존 문제를 조회하고 수동으로 문제를 추가하고 관리할 수 있습니다.

### 12.5 RAG 문서 관리 화면

![RAG Document Management](docs/images/rag-document-management1.png)
문서를 업로드하고, chunk 검색 테스트를 수행할 수 있습니다.

### 12.6 Hybrid RAG 검색 테스트 화면

![Hybrid RAG Search](docs/images/rag-document-management2.png)

vector, keyword, hybrid 검색 모드를 선택하고 vector_score, keyword_score, hybrid_score를 확인할 수 있습니다.

### 12.7 응시자 신청 화면

![Applicant Apply](docs/images/applicant-apply.png)

응시자는 신청화면에서 기본적인 정보를 입력한 후에 진단 신청을 할 수 있습니다.

### 12.8 응시자 진단 시험 대기화면


![Applicant Waiting Room](docs/images/applicant-test.png)


### 12.9 응시자 진단 시험 화면

![Applicant Test](docs/images/applicant-test2.png)

### 12.10 응시자 시험 종료 화면

![Applicant End](docs/images/applicant-end.png)

### 12.11 관리자 및 응시자 결과 확인 화면

![Applicant Result](docs/images/admin-applicant-detail1.png)
![Applicant Result](docs/images/admin-applicant-detail2.png)

---

## 13. 트러블슈팅

### 13.1 LLM 자유 생성 문제 품질 불안정

문제:
초기에는 GPT-4o-mini에 topic, difficulty, count만 전달해 문제를 생성했습니다. 하지만 고급 문제에서도 단순 정의형 문제가 생성되거나, 실무 상황과 제약 조건이 부족한 문제가 반복되었습니다.

원인:
LLM 자유 생성 방식은 문제 형식, 평가 포인트, evidence, 오답 방향을 안정적으로 제어하기 어렵습니다.

해결:
설계서 기반 문제 생성과 템플릿 기반 고급 문제 생성을 도입했습니다. 특히 AI/SQL 고급 문제는 문제 body를 템플릿으로 고정하고, LLM은 choices와 explanation을 생성하도록 역할을 제한했습니다.

결과:
RAG 검색 품질 주제에서 hybrid_search_choice, context_filtering, query_rewrite_failure, retrieval_quality_diagnosis, chunking_issue처럼 서로 다른 평가 포인트의 고급 문제를 생성할 수 있게 되었습니다.

---

### 13.2 정답 번호 1번 편향

문제:
LLM이 생성한 객관식 문제에서 정답이 1번에 몰리는 현상이 발생했습니다.

원인:
LLM은 프롬프트의 JSON 예시나 일반적인 패턴을 따라 정답을 앞쪽 선택지에 배치하는 경향이 있습니다.

해결:
검증 통과 후 `_rebalance_answer_positions()`를 통해 choices 순서를 재배치하고, answer 번호를 함께 수정했습니다.

결과:
정답 위치가 1~5번 사이에 분산되도록 개선했습니다.

---

### 13.3 choices 재배치 후 explanation 불일치

문제:
선택지 순서를 재배치하면 explanation의 “정답은 N번입니다.” 문장이나 “1번은”, “2번은” 같은 오답 설명이 깨지는 문제가 발생했습니다.

원인:
기존 explanation이 선택지 번호 기준으로 오답을 설명하고 있었기 때문입니다.

해결:
정답 번호를 새 answer 값으로 치환하고, 번호 기반 오답 설명을 제거했습니다. 필요한 경우 `_repair_multiple_choice_explanations()`로 explanation만 다시 생성했습니다.

결과:
정답 번호와 explanation 첫 문장이 일치하고, 오답 설명도 번호가 아니라 선택지의 핵심 조치 기준으로 설명되도록 개선했습니다.

---

### 13.4 고급 문제 선택지 품질 저하

문제:
고급 문제인데 다음과 같은 쉬운 오답이 생성되었습니다.

* top_k를 무조건 증가시킨다
* 모든 컬럼에 인덱스를 추가한다
* keyword search는 필요 없다
* filesort는 항상 오류다
* 인덱스는 필요 없다

원인:
LLM이 오답을 만들 때 정답과 쉽게 구분되는 단정적 표현을 사용하는 경향이 있었습니다.

해결:
다음 검증과 규칙을 추가했습니다.

* 선택지 최소 길이 기준
* 극단 표현 금지
* 정답 선택지만 과도하게 길어지는 패턴 감지
* answer_intent 기반 정답 키워드 검증
* distractor_intents 기반 오답 방향 제어

결과:
오답도 실무자가 실제로 고려할 수 있는 대안처럼 보이되, 현재 문제의 핵심 조건을 해결하지 못하는 방향으로 개선했습니다.

---

### 13.5 AI/RAG 고급 문제의 evidence 부족

문제:
AI/RAG 문제인데 query, top_k, chunk, similarity, metadata_filter 같은 검색 근거가 포함되지 않는 문제가 생성되었습니다.

원인:
LLM이 RAG 검색 품질 문제를 일반론적으로 요약하면서 실제 검색 로그를 body에 반영하지 않았습니다.

해결:
AI/RAG 고급 문제에는 다음 evidence를 요구하도록 검증 기준을 강화했습니다.

* query
* top_k
* chunk
* similarity
* vector_score
* keyword_score
* hybrid_score
* metadata_filter
* vector search
* keyword search
* hybrid search
* context filtering

결과:
검색 근거가 부족한 문제는 validator에서 제외되도록 개선했습니다.

---

### 13.6 PDF Chunk 품질 문제

문제:
NCS PDF 문서를 그대로 RAG에 넣었을 때 교수학습방법, 수행 tip, 장비, 안전유의사항 같은 문제 생성과 관련 낮은 내용이 검색되었습니다.

원인:
PDF 원문에는 문제 생성에 직접 필요하지 않은 안내성 문구가 많고, 단순 글자 수 기준 chunking은 의미 단위를 깨뜨릴 수 있습니다.

해결:
PDF 전처리와 chunk 분리 방식을 개선했습니다.

* 불필요한 안내성 문구 제거
* 페이지 번호 및 짧은 노이즈 제거
* 문단/제목/수행준거 단위 유지
* chunk_size와 overlap 조정
* category metadata prefix 추가

결과:
검색 결과에서 문제 생성에 더 직접적으로 사용할 수 있는 chunk가 상위에 노출되도록 개선했습니다.

---

### 13.7 Vector Search만 사용했을 때 정확 키워드 누락

문제:
Vector Search는 의미적으로 유사한 chunk를 찾지만, EXPLAIN, filesort, metadata_filter, reranker 같은 정확 키워드를 놓치는 경우가 있었습니다.

원인:
Dense vector search는 의미 유사도 기반이므로 정확 문자열 매칭이 중요한 기술 키워드 검색에는 한계가 있습니다.

해결:
MariaDB LIKE 기반 keyword search를 추가하고, ChromaDB vector search 결과와 병합했습니다.

결과:
vector_score와 keyword_score를 결합한 hybrid_score 기준으로 검색 결과를 정렬할 수 있게 되었습니다.

---

### 13.8 일반 생성과 문서 기반 생성 구분 문제

문제:
AI 문제 검토 화면과 문제 관리 화면에서 생성된 문제가 설계서 기반인지 문서 기반 RAG인지 구분하기 어려웠습니다.

원인:
생성 방식 정보가 화면에 표시되지 않았습니다.

해결:
문제 저장 시 생성 방식 정보를 함께 저장하고, 프론트에서 다음과 같이 표시했습니다.

| 값              | 표시        |
| -------------- | --------- |
| general        | 설계서 기반    |
| rag            | 문서 기반 RAG |
| null 또는 manual | 수동/기존     |

결과:
AI 문제 생성, AI 문제 검토, 문제 관리 화면에서 생성 방식과 생성일시를 확인할 수 있게 되었습니다.

---

### 13.9 문체 불일치 문제

문제:
문제 본문과 선택지는 시험 문항체여야 하는데, 일부 문제에서 존댓말과 반말이 섞였습니다.

예시:

* 어떤 접근 방식을 선택해야 할까요?
* 검색 품질을 개선해야 합니다.
* 정답은 1번입니다.

원하는 기준:

| 항목          | 문체      |
| ----------- | ------- |
| body        | 시험 문항체  |
| choices     | 시험 선택지체 |
| explanation | 존댓말     |

해결:
프롬프트에 문체 규칙을 추가하고, body/choices 후처리 함수를 적용했습니다.

결과:
body와 choices는 “무엇인가?”, “판단한다”, “적용한다” 형태로 정리하고, explanation은 “정답은 N번입니다.”로 시작하는 존댓말 문체를 유지하도록 개선했습니다.

---

## 14. 현재 구현 범위와 한계

### 14.1 현재 구현된 것

| 기능                              | 구현 여부 |
| ------------------------------- | ----- |
| 관리자 문제은행 관리                     | 구현    |
| 응시자/진단/기록 관리                    | 구현    |
| GPT-4o-mini 기반 AI 문제 생성         | 구현    |
| 설계서 기반 문제 생성                    | 구현    |
| 템플릿 기반 AI/SQL 고급 문제 생성          | 구현    |
| choices/explanation LLM 생성      | 구현    |
| validator 기반 문제 검증              | 구현    |
| 정답 위치 재배치                       | 구현    |
| 해설 번호 보정                        | 구현    |
| 문서 업로드                          | 구현    |
| PDF/Markdown 텍스트 처리             | 구현    |
| OpenAI embedding                | 구현    |
| ChromaDB vector search          | 구현    |
| MariaDB LIKE keyword search     | 구현    |
| Hybrid RAG MVP                  | 구현    |
| category metadata filter        | 구현    |
| vector / keyword / hybrid 검색 모드 | 구현    |
| 생성 방식 표시                        | 구현    |
| 생성일시 표시                         | 구현    |
| 관리자 pending 검수 흐름               | 구현    |

### 14.2 현재 한계

| 한계              | 설명                                    |
| --------------- | ------------------------------------- |
| 문서 기반 RAG 문제 품질 | 설계서 기반 문제보다 body와 choices 품질이 낮을 수 있음 |
| Keyword Search  | BM25가 아니라 MariaDB LIKE 기반 MVP         |
| Reranker        | 실제 reranker 모델 미적용                    |
| LangGraph       | 생성-검증-수정 workflow는 아직 미적용             |
| Fine-tuning     | approved 문제 기반 학습은 아직 미구현             |
| QLoRA/vLLM      | 자체 모델 튜닝 및 서빙은 검토 단계                  |
| AI 채점           | 서술형/코드작성형 자동 채점은 향후 계획                |
| 역량 분석 리포트       | 응시자별 AI 분석 리포트는 향후 계획                 |

---

## 15. 향후 고도화 계획

### 15.1 FULLTEXT/BM25 기반 Keyword Search 고도화

현재 keyword search는 MariaDB LIKE 기반입니다. 향후에는 MariaDB FULLTEXT 또는 BM25 기반 랭킹을 도입해 keyword_score 품질을 개선할 계획입니다.

### 15.2 Reranker 적용

Hybrid Search 이후 cross-encoder 또는 LLM 기반 reranker를 적용해 chunk 순위를 재정렬할 계획입니다.

고려할 지표:

* Recall@K
* MRR
* 검색 정확도
* p95 latency
* 운영 비용

### 15.3 LangGraph 기반 Workflow

현재는 함수 기반 생성/검증 흐름으로 구성되어 있습니다. 향후에는 LangGraph를 사용해 생성-검증-수정-저장 흐름을 명시적인 graph로 구성할 계획입니다.

예상 workflow:

* input_node
* query_rewrite_node
* retrieval_node
* context_filter_node
* question_generation_node
* json_validation_node
* quality_review_node
* repair_node
* save_node
* human_review_node

### 15.4 Approved 문제 기반 Fine-tuning Dataset 구축

관리자 검수를 통과한 approved 문제만 학습 데이터 후보로 사용합니다.

구성 계획:

* approved 문제 export
* answer/explanation 정합성 검증
* competency_type 정규화
* quality_score 기반 필터링
* JSONL 변환
* train/validation/test 분리

### 15.5 Fine-tuning / QLoRA 실험

먼저 OpenAI fine-tuning을 실험하고, 충분한 데이터가 쌓인 뒤 QLoRA 기반 오픈소스 모델 튜닝을 검토할 계획입니다.

### 15.6 vLLM 자체 서빙 검토

자체 모델을 운영할 경우 다음 기준을 비교할 예정입니다.

* 품질 통과율
* p95 latency
* 월 추론 비용
* GPU 운영 부담
* 장애 대응 난이도
* canary 배포 가능성

### 15.7 AI 채점 및 역량 분석 리포트

향후 서술형과 코드작성형 문제에 대해 AI 채점을 적용하고, 응시자의 역량별 약점 분석 리포트를 자동 생성하는 기능을 추가할 계획입니다.

---

## 16. 실행 방법

### 16.1 Backend 실행

```
cd backend
python -m venv itskill_venv
itskill_venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

macOS 또는 Linux 환경에서는 가상환경 활성화 명령어를 다음처럼 사용합니다.

```
source itskill_venv/bin/activate
```

### 16.2 Frontend 실행

프로젝트 구조에 따라 frontend 또는 root 디렉토리에서 실행합니다.

```
npm install
npm run dev
```

### 16.3 환경 변수

실제 API Key는 README에 작성하지 않습니다.

예시:

```
OPENAI_API_KEY=
DATABASE_URL=
CHROMA_DB_PATH=
CHROMA_COLLECTION=
FRONTEND_URL=
```

### 16.4 DB 설정

MariaDB를 실행한 뒤 프로젝트의 SQLAlchemy 설정 또는 환경 변수에 맞게 DB 연결 정보를 설정합니다.

예시:

```
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/DB_NAME
```

---

## 17. 핵심 성과

### 17.1 단순 LLM 사용이 아닌 구조적 문제 생성

본 프로젝트는 단순히 “LLM에게 문제를 만들어달라”고 요청하는 방식에서 출발했지만, 실제 테스트 과정에서 고급 문제 품질 부족, 정답 위치 편향, 오답 품질 저하, 해설 불일치 문제가 반복적으로 발생했습니다.

이를 해결하기 위해 다음 구조를 도입했습니다.

* 설계서 기반 생성
* 템플릿 기반 고급 문제 생성
* answer_intent / distractor_intents
* validator 기반 검증
* 정답 위치 재배치
* 해설 재생성
* 관리자 검수 흐름

이를 통해 LLM의 자유도를 줄이고, 코드 레벨에서 문제 품질을 통제하는 구조를 만들었습니다.

### 17.2 Hybrid RAG MVP 직접 구현

문서 기반 문제 생성을 위해 ChromaDB vector search를 적용했고, 정확 키워드 검색 한계를 보완하기 위해 MariaDB LIKE 기반 keyword search를 결합했습니다.

현재 구현은 BM25나 reranker 기반 완성형 검색 시스템은 아니지만, 다음 흐름을 구현했습니다.

* vector search
* keyword search
* metadata filter
* score merge
* hybrid_score 계산
* context 구성
* 문서 기반 문제 생성

### 17.3 Human-in-the-loop 검수 구조

AI가 생성한 문제는 바로 확정되지 않고 pending 상태로 저장됩니다. 관리자가 직접 검수하고 approved 처리해야 실제 문제은행에 반영됩니다.

이 구조는 AI 생성 결과의 불확실성을 서비스 흐름 안에서 관리하기 위한 장치입니다.

### 17.4 실무형 IT 역량진단 문제 생성

SQL 실행 계획, RAG 검색 품질, LLM 구조화 출력, Agent workflow, ModelOps 등 실무와 연결된 고급 문제를 생성할 수 있도록 문제 형식과 템플릿을 구성했습니다.

### 17.5 현재 프로젝트의 핵심 메시지

AI-IT Skill은 단순 문제은행이 아니라, AI 생성 결과를 구조화하고 검증하며, 문서 기반 근거 검색과 관리자 검수 흐름을 결합한 IT 역량진단 플랫폼입니다.
