# IT 역량진단 문제은행 파일 역할 정의서 (FILE_ROLE_MAP)

본 문서는 리팩토링 전 현재 프로젝트의 각 파일별 역할과 의존 관계를 파악하기 위한 지도입니다.

---

## 1. 문서 목적
*   리팩토링 시 파일 이동의 근거로 활용.
*   각 모듈의 책임(Responsibility)을 명확히 정의.
*   주요 비즈니스 로직 흐름(문제 생성, RAG)별 파일 연결 관계 확인.

---

## 2. Backend Entry Files

| 파일 경로 | 역할 | 주요 호출 파일 | 호출 위치 |
| :--- | :--- | :--- | :--- |
| `backend/main.py` | FastAPI 앱 초기화 및 Router 등록 | `routers/*` | 서비스 시작점 (uvicorn) |
| `backend/database.py` | DB 연결 설정 및 Session 생성 | `sqlalchemy` | Routers, Services |
| `backend/models.py` | DB 테이블(MariaDB) 스키마 정의 | `database.Base` | Routers, Services |
| `backend/schemas.py` | API 요청/응답 Pydantic 스키마 정의 | `pydantic` | Routers |

---

## 3. Backend Routers

| 파일 경로 | 역할 | 주요 호출 서비스 |
| :--- | :--- | :--- |
| `routers/ai_questions.py` | AI 문제 생성 관련 API 진입점 | `question_generator.py`, `document_service.py`, `question_generation_graph.py` |
| `routers/ai_documents.py` | RAG 문서 관리 및 검색 API 진입점 | `document_loader.py`, `text_splitter.py`, `document_service.py` |
| `routers/questions.py` | 수동 문제 관리 (CRUD) | `models.py` |
| `routers/applicants.py` | 응시자 관리 | `models.py` |
| `routers/exam.py` | 시험 응시 흐름 제어 | `models.py` |
| `routers/diagnoses.py` | 시험지(진단) 구성 및 관리 | `models.py` |
| `routers/dashboard.py` | 통계 데이터 조회 | `models.py` |

---

## 4. AI Core Files

| 파일 경로 | 역할 | 호출되는 곳 | 리팩토링 후 추천 위치 |
| :--- | :--- | :--- | :--- |
| `ai/client.py` | OpenAI API Client 초기화 | Services, Embedding | `ai/core/openai_client.py` |
| `ai/embedding_service.py` | 텍스트 벡터화 (Embedding) | `document_service.py` | `ai/rag/embedding_service.py` |
| `ai/vector_store.py` | ChromaDB CRUD 및 유사도 검색 | `document_service.py` | `ai/rag/vector_store.py` |

---

## 5. AI LangGraph Files (Workflow Control)

| 파일 경로 | 역할 | 주요 호출 서비스 | 추천 위치 |
| :--- | :--- | :--- | :--- |
| `ai/graph/question_generation_state.py` | 그래프 상태 데이터 구조 정의 | - | `ai/questions/graph_state.py` |
| `ai/graph/question_generation_nodes.py` | 각 단계별 실행 로직 (Node) | `question_planner.py`, `question_generator.py`, `question_validator.py` | `ai/questions/graph_nodes.py` |
| `ai/graph/question_generation_graph.py` | 그래프 구조 및 엣지 정의 | `question_generation_nodes.py` | `ai/questions/graph_runner.py` |

---

## 6. AI RAG Files (Retrieval)

| 파일 경로 | 역할 | 상세 설명 |
| :--- | :--- | :--- |
| `ai/rag/document_loader.py` | 파일 텍스트 추출 | PDF, Docx, TXT 로더 포함 |
| `ai/rag/text_cleaner.py` | 텍스트 정제 | 노이즈 제거 및 포맷팅 |
| `ai/rag/text_splitter.py` | 텍스트 분할 (Chunking) | 의미 단위 분할 로직 |
| `ai/rag/document_service.py` | **RAG 통합 서비스** | **Hybrid Search**(Vector + FULLTEXT), RRF Merge, Context Builder |

---

## 7. AI Question Service Files (Generation)

| 파일 경로 | 역할 | 호출 관계 | 추천 위치 |
| :--- | :--- | :--- | :--- |
| `ai/services/question_generator.py` | 실제 문제 생성 (LLM 호출) | `ai_questions.py`, Graph Nodes | `ai/questions/generator.py` |
| `ai/services/question_planner.py` | 문제 설계서(Plan) 생성 | Graph Nodes | `ai/questions/planner.py` |
| `ai/services/question_validator.py` | 생성 결과 형식 및 정답 검증 | Graph Nodes, `ai_questions.py` | `ai/questions/validator.py` |
| `ai/services/question_templates.py` | 기술별 고급 문제 구조 정의 | Graph Nodes | `ai/questions/templates.py` |
| `ai/services/question_choice_generator.py` | 템플릿용 선택지/해설 생성 | Graph Nodes | `ai/questions/choice_generator.py` |
| `ai/services/competency_config.py` | 역량 유형별 키워드 및 설정 | 대부분의 AI 모듈 | `ai/core/config.py` |

---

## 8. Frontend App & Pages

| 파일 경로 | 역할 | 주요 연결 Backend |
| :--- | :--- | :--- |
| `src/lib/api.ts` | API 통신 추상화 | Backend Routers |
| `src/app/pages/AIQuestionGeneration.tsx` | 문제 생성 요청 화면 | `POST /api/ai/generate-questions` |
| `src/app/pages/AIQuestionReview.tsx` | 생성 문제 검수 화면 | `GET /api/questions`, `PUT /api/questions/{id}` |
| `src/app/pages/DocumentRAGManagement.tsx` | RAG 문서 관리 화면 | `POST /api/ai/documents/upload` |
| `src/app/pages/QuestionManagement.tsx` | 승인된 문제 관리 화면 | `GET /api/questions` |

---

## 9. 주요 흐름별 파일 연결 요약

### A. 일반 문제 생성
`AIQuestionGeneration.tsx` → `api.ts` → `routers/ai_questions.py` → `ai/services/question_generator.py` → `models.py` (Save)

### B. Template 기반 고급 문제 생성 (LangGraph)
`AIQuestionGeneration.tsx` → `api.ts` → `routers/ai_questions.py` → `ai/graph/question_generation_graph.py` → `ai/graph/question_generation_nodes.py` → (`question_templates.py`, `question_choice_generator.py`, `question_validator.py`) → `models.py` (Save)

### C. 문서 업로드 및 임베딩
`DocumentRAGManagement.tsx` → `api.ts` → `routers/ai_documents.py` → (`document_loader.py`, `text_splitter.py`) → `ai/embedding_service.py` → `ai/vector_store.py` → ChromaDB & MariaDB

### D. Hybrid RAG 검색 및 문서 기반 생성
`AIQuestionGeneration.tsx` → `api.ts` → `routers/ai_questions.py` → `ai/rag/document_service.py` → (`vector_store.py`, MariaDB FULLTEXT) → `ai/services/question_generator.py` (Context 기반 생성)

---

## 10. 리팩토링 후보 및 테스트 체크리스트

### 주요 리팩토링 대상
1.  **AI Core 분리**: `client.py` 등을 `ai/core`로 이동.
2.  **RAG 모듈화**: `embedding`, `vector_store`를 `ai/rag` 내부로 이동.
3.  **문제 생성 모듈화**: `services`와 `graph`를 `ai/questions`로 통합.

### 리팩토링 후 필수 테스트 항목
*   [ ] 일반 문제 생성 기능 (1개 생성 테스트)
*   [ ] 고급 템플릿 문제 생성 기능 (AI, SQL 등 역량별)
*   [ ] 문서 업로드 및 chunk 분리 정상 여부
*   [ ] 문서 검색 (Hybrid 모드) 결과 노출 여부
*   [ ] 문서 기반 RAG 문제 생성 및 근거 포함 여부
*   [ ] AI 검수 화면에서 생성된 문제의 데이터 정합성 확인
