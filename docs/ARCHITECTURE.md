# IT 역량진단 문제은행 프로젝트 아키텍처

본 문서는 IT 역량진단 문제은행 프로젝트의 현재 시스템 구조와 주요 데이터 흐름을 정의합니다. 본 문서는 리팩토링 전의 상태를 기준으로 작성되었으며, 향후 리팩토링의 가이드라인을 포함합니다.

---

## 1. 프로젝트 개요

*   **전체 목적**: 기업 및 교육 기관에서 IT 인재의 역량을 객관적으로 진단하기 위한 문제은행 관리 및 시험 응시 플랫폼.
*   **주요 기능**:
    *   **관리자 기반 문제 관리**: 수동 문제 등록, 수정, 삭제 및 AI 생성 문제 검수.
    *   **응시자 및 시험 관리**: 응시자 정보 등록, 시험지(진단) 구성, 결과 분석.
    *   **AI 문제 생성**: 주제와 난이도에 따른 자동 문제 생성 (일반 생성 및 템플릿 기반 고급 생성).
    *   **RAG 문서 관리**: 지식 베이스(NCS, 기술 문서 등) 업로드 및 이를 기반으로 한 근거 중심 문제 생성.

---

## 2. 전체 시스템 구조

*   **Frontend**: React + TypeScript + Vite 기반의 SPA.
*   **Backend**: FastAPI 기반의 비동기 REST API 서버.
*   **Database**: MariaDB (메인 관계형 데이터 및 전문 검색용 FULLTEXT 인덱스 활용).
*   **AI**: 
    *   OpenAI GPT-4o / GPT-4o-mini (문제 생성 및 검증).
    *   OpenAI Text-Embedding-3-Small (문서 임베딩).
*   **Vector DB**: ChromaDB (벡터 유사도 검색용).
*   **RAG**: ChromaDB(Vector) + MariaDB(Fulltext) + RRF(Reciprocal Rank Fusion) 기반의 **Hybrid RAG**.
*   **LangGraph**: 복잡한 문제 생성 파이프라인(Planner, Template, Validator) 제어 및 상태 관리.

---

## 3. Frontend 구조

*   **src/app/pages**: 각 화면별 컴포넌트가 위치하며, 페이지 단위의 비즈니스 로직을 담당합니다.
*   **src/lib/api.ts**: Axios 인스턴스를 관리하며, Backend API와의 모든 통신을 추상화한 API 클라이언트입니다.
*   **src/lib/types.ts**: API 요청/응답 및 프론트엔드 전반에서 사용하는 TypeScript Interface/Type 정의 파일입니다.
*   **주요 AI 관련 화면**:
    *   `AIQuestionGeneration.tsx`: 일반 문제 생성 및 문서 기반 RAG 문제 생성 요청 화면.
    *   `AIQuestionReview.tsx`: AI가 생성한 'pending' 상태의 문제를 검토하고 승인/반려하는 화면.
    *   `DocumentRAGManagement.tsx`: RAG용 문서 업로드, 임베딩 상태 관리 및 검색 테스트 화면.
    *   `QuestionManagement.tsx`: 승인된 전체 문제 목록 관리 및 필터링 화면.

---

## 4. Backend 구조

*   **routers/**: FastAPI의 APIRouter를 사용하여 기능별 API Endpoint를 정의합니다.
    *   `ai_questions.py`: 문제 생성 관련 진입점.
    *   `ai_documents.py`: 문서 업로드 및 RAG 검색 진입점.
*   **ai/**: AI 관련 핵심 로직이 위치합니다.
    *   `graph/`: LangGraph 기반 워크플로우 관련 파일들.
    *   `rag/`: 문서 처리 및 Hybrid RAG 검색 로직.
    *   `services/`: 실제 프롬프트 엔지니어링 및 문제 생성 기능 모듈.
*   **models.py**: SQLAlchemy 기반의 MariaDB 테이블 스키마 정의.
*   **schemas.py**: Pydantic 기반의 API 요청/응답 데이터 검증 스키마.
*   **database.py**: DB 연결 세션 관리.

---

## 5. 일반 AI 문제 생성 흐름

1.  **UI**: `AIQuestionGeneration.tsx`에서 주제, 난이도, 개수 선택 후 생성 버튼 클릭.
2.  **API 호출**: `src/lib/api.ts`의 `aiQuestionApi.generateGeneral` 호출.
3.  **Router**: `routers/ai_questions.py`의 `POST /generate-questions` 수신.
4.  **Service**: `ai/services/question_generator.py`의 `generate_questions` 실행.
    *   프롬프트 생성 -> OpenAI 호출 -> JSON 파싱.
5.  **저장**: `save_generated_questions` 함수를 통해 `questions` 테이블에 `review_status='pending'`으로 저장.
6.  **UI**: 생성 완료 후 `AIQuestionReview.tsx`에서 생성된 문제 확인 및 승인.

---

## 6. Template 기반 고급 문제 생성 흐름 (LangGraph)

고급 수준의 전문적인 문제를 생성할 때 사용되는 흐름입니다.

1.  **Router**: `routers/ai_questions.py`의 `POST /generate-questions-graph` 호출.
2.  **Graph 실행**: `ai/graph/question_generation_graph.py`의 `run_question_generation_graph` 실행.
3.  **Template Node**: `ai/services/question_templates.py`에서 정의된 기술별(AI, SQL, Python, Java) 고급 문제 구조를 로드.
4.  **Choice Generation**: `ai/services/question_choice_generator.py`를 통해 고정된 문제 구조에 맞는 매력적인 오답과 해설을 LLM으로 생성.
5.  **Validation**: `ai/services/question_validator.py`를 통해 생성된 결과의 정답 일치 여부 및 형식 검증.
6.  **Save**: 검증 완료된 문제를 DB에 자동 저장.

---

## 7. LangGraph 구조

LangGraph는 독립적인 Agent라기보다, 문제 생성의 단계별 상태(State)를 관리하고 로직의 흐름을 제어하는 파이프라인 관리 도구로 사용됩니다.

*   **question_generation_state.py**: 그래프 내에서 전달되는 상태 데이터 구조(topic, difficulty, plans, questions 등) 정의.
*   **question_generation_nodes.py**: 각 단계별 실행 로직(Node) 구현.
    *   `normalize_node`: 입력 데이터 정규화.
    *   `route_node`: 난이도/역량에 따라 Planner 방식 또는 Template 방식 결정.
    *   `planner_node`: 문제 설계서(Plan) 작성.
    *   `generation_node`: 설계서 또는 템플릿 기반 실제 문제 생성.
    *   `validation_node`: 생성물 검증.
    *   `save_node`: 최종 결과 DB 저장.
*   **question_generation_graph.py**: 노드 간의 연결 관계(Edge) 및 조건부 분기(Conditional Edge) 정의.

---

## 8. 문서 업로드 및 임베딩 흐름

1.  **UI**: `DocumentRAGManagement.tsx`에서 파일 선택 및 업로드.
2.  **Router**: `routers/ai_documents.py`의 `POST /upload` 수신.
3.  **Processing**:
    *   `document_loader.py`: PDF/Docx/Text에서 텍스트 추출.
    *   `text_cleaner.py`: 불필요한 공백 및 특수문자 정제.
    *   `text_splitter.py`: 의미 단위로 텍스트를 Chunk(조각) 분리.
4.  **DB 저장**: 추출된 정보와 Chunk들을 MariaDB `ai_documents`, `ai_document_chunks` 테이블에 저장.
5.  **Embedding (Async/Manual)**: `POST /{document_id}/embed` 호출 시:
    *   `embedding_service.py`: OpenAI API를 통한 벡터화.
    *   `vector_store.py`: ChromaDB에 벡터 및 메타데이터 저장.
    *   MariaDB Chunk 테이블에 `vector_id` 업데이트.

---

## 9. Hybrid RAG 검색 흐름

ChromaDB의 벡터 검색과 MariaDB의 키워드 검색을 결합하여 정확도를 높입니다.

1.  **Entry**: `document_service.py`의 `search_document_chunks` 호출.
2.  **Vector Search**: `vector_store.py`를 통해 유사한 의미의 Chunk 검색.
3.  **Keyword Search**: MariaDB `FULLTEXT` 인덱스를 활용한 `MATCH AGAINST` 쿼리로 키워드 기반 검색.
4.  **RRF Merge**: `merge_hybrid_search_results`에서 두 검색 결과를 RRF 알고리즘으로 병합하여 최종 순위 산출.
5.  **Filtering**: `_is_noise_context` 등을 통해 문제 생성에 부적합한 안내성 텍스트 필터링.
6.  **Context 생성**: `build_context_from_search_results`에서 최종 검색 결과를 LLM 프롬프트용 Context 문자열로 결합.

---

## 10. 문서 기반 RAG 문제 생성 흐름

1.  **UI**: `AIQuestionGeneration.tsx`에서 주제 입력 및 "문서 기반 생성" 옵션 선택.
2.  **Router**: `routers/ai_questions.py`의 `POST /generate-questions-from-document` 수신.
3.  **Search**: `document_service.py`를 호출하여 관련 문서 Context 확보.
4.  **Generation**: `ai/services/question_generator.py`의 `generate_questions_from_context` 호출.
    *   검색된 문서를 "출제 근거"로 사용하여 문제 생성.
5.  **저장**: `questions` 테이블에 `ai_generation_type='rag'`으로 저장.

---

## 11. 데이터 저장 구조

### MariaDB (Main DB)
*   **ai_documents**: 업로드된 문서 정보(제목, 파일 경로, 카테고리, 임베딩 상태).
*   **ai_document_chunks**: 문서의 텍스트 조각들. `vector_id`를 통해 ChromaDB와 연결됨. 전문 검색(FULLTEXT) 인덱스 보유.
*   **questions**: 모든 문제 데이터. `source_type`(manual/ai), `review_status`(pending/approved/rejected) 등을 포함.

### ChromaDB (Vector DB)
*   `ai_document_chunks` 테이블의 각 행에 대응하는 **벡터 데이터**와 **메타데이터**를 저장하여 고속 유사도 검색 지원.

---

## 12. 현재 구조의 문제점 및 복잡도

*   **분산된 로직**: `embedding_service.py`와 `vector_store.py`가 `ai/` 루트에 있어 RAG 관련 로직이 `ai/rag/`와 분산되어 보임.
*   **비대한 services**: `services/` 폴더에 생성기, 플래너, 검증기, 설정, 템플릿이 모두 섞여 있어 구분이 어려움.
*   **그래프 복잡도**: `ai/graph/` 내부 파일들이 외부 서비스 모듈(`planner`, `generator` 등)을 복잡하게 호출하고 있어 의존성 파악이 힘듦.

---

## 13. 향후 리팩토링 추천 구조

시스템 확장성을 위해 다음과 같은 계층적 구조를 추천합니다.

```text
backend/ai/
├── core/               # 공통 기반 인프라
│   ├── openai_client.py
│   └── config.py
├── rag/                # RAG (Retrieval) 전담
│   ├── loader/
│   ├── splitter/
│   ├── embedding/      # (이동 추천)
│   ├── vector_store/   # (이동 추천)
│   └── service.py      # Hybrid Search & Context Builder
└── questions/          # 문제 생성 (Generation) 전담
    ├── graph/          # LangGraph Runner & Nodes
    ├── services/       # Planner, Generator, Validator
    └── templates/      # 기술별 템플릿 정의
```

---

## 14. 리팩토링 시 주의사항

1.  **순차적 이동**: 한 번에 모든 파일을 이동하지 말고, RAG -> 문제 생성 -> LangGraph 순으로 이동하며 테스트를 병행할 것.
2.  **Import 경로 주의**: 파일 위치 변경 시 `sys.path`나 상대 경로 이슈가 발생하지 않도록 절대 경로 임포트를 권장.
3.  **기능 동결**: 리팩토링 중에는 새로운 AI 프롬프트 수정이나 기능 추가를 지양하여 부작용(Side Effect) 최소화.
4.  **검증 필수**: 각 모듈 이동 후 `generate-questions`와 `search` API가 기존과 동일하게 동작하는지 반드시 확인.
