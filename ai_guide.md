# IT 역량진단 시스템 — AI 기능 구축 가이드

> **목적**: GPT와 함께 AI 기능을 직접 구현할 수 있도록,  
> 현재 시스템 구조, 추가해야 할 AI 기능, 폴더 구조, API 연결 방식을 상세히 기술합니다.

---

## 1. 현재 시스템 구조 (GPT에게 설명용)

```
c:\itskillAI\
├── backend\                   # FastAPI 백엔드 (Python)
│   ├── main.py                # 앱 진입점 (라우터 등록)
│   ├── database.py            # MariaDB 연결 (SQLAlchemy)
│   ├── models.py              # DB 테이블 모델
│   ├── schemas.py             # Pydantic 요청/응답 스키마
│   └── routers\
│       ├── auth.py            # 관리자 JWT 인증
│       ├── applicants.py      # 응시자 CRUD
│       ├── diagnoses.py       # 시험지(문제집) CRUD
│       ├── questions.py       # 문제 CRUD
│       ├── records.py         # 응시 기록 + 답변 조회
│       ├── exam.py            # 응시자 시험 흐름 (로그인→풀기→제출→결과)
│       └── dashboard.py       # 대시보드 통계
└── src\                       # React + Vite 프론트엔드 (TypeScript)
    ├── lib\
    │   ├── api.ts             # axios API 호출 함수들
    │   └── types.ts           # TypeScript 타입 정의
    └── app\
        └── pages\             # 관리자 화면들
```

### 핵심 DB 테이블

| 테이블 | 설명 |
|--------|------|
| `questions` | 문제 (title, choices_json, answer_json, competency_type, difficulty, score) |
| `diagnoses` | 시험지 (title, question_idxs="1,2,5", question_count, duration_minutes) |
| `applicants` | 응시자 (name, email, status, target_diagnosis_id) |
| `records` | 응시 결과 (answer_data="1,2,0,1", total_score, pass_yn, competency_breakdown_json, summary_comment) |

---

## 2. 추가해야 할 AI 기능 목록

### ① 자동 문제 생성 (AI Question Generation)
- **역할**: 관리자가 주제/난이도/역량 키워드를 입력하면 GPT가 문제+선택지+정답+해설을 자동 생성
- **사용 API**: `OpenAI GPT-4o` (또는 `GPT-4-turbo`)
- **입력**: 주제(예: "Spring Boot 트랜잭션"), 난이도(초급/중급/고급), 문제 수(N)
- **출력**: `Question` 형식의 JSON 배열
- **라우터 파일**: `backend/routers/ai_questions.py` (신규 생성)

### ② AI 채점 및 결과 요약 (AI Grading & Summary)
- **역할**: 객관식 외 주관식/서술형 문제 자동 채점 + 응시 결과 종합 코멘트 생성
- **사용 API**: `OpenAI GPT-4o`
- **입력**: 응시자의 answer_data, 각 문제 내용, 역량 분류
- **출력**: 문제별 채점 결과 + `summary_comment` (한국어 총평 텍스트)
- **연결 위치**: `backend/routers/exam.py`의 `submit_exam()` 함수 내부에서 호출
- **저장 위치**: `records.summary_comment` 컬럼

### ③ 문서 기반 문제 생성 RAG (Document RAG)
- **역할**: 관리자가 PDF/Word 문서를 업로드하면 해당 내용을 기반으로 문제 생성
- **사용 API**: `OpenAI Embeddings` + `LangChain` 또는 `LlamaIndex`
- **벡터 DB**: `FAISS` (로컬) 또는 `Chroma`
- **라우터 파일**: `backend/routers/ai_rag.py`

### ④ 역량 약점 분석 리포트 (AI Analytics)
- **역할**: 전체 응시자의 역량별 점수를 분석하여 "이 조직의 취약 역량" 자동 리포트 생성
- **사용 API**: `OpenAI GPT-4o`
- **입력**: 대시보드의 `competency_breakdown_json` 집계 데이터
- **출력**: 한국어 분석 코멘트
- **라우터 파일**: `backend/routers/ai_analytics.py`

---

## 3. AI 폴더 구조 (신규 생성)

```
backend\
├── ai\                            ← 신규 폴더
│   ├── __init__.py
│   ├── client.py                  ← OpenAI 클라이언트 초기화 (공통)
│   ├── question_generator.py      ← 문제 자동 생성 로직
│   ├── grader.py                  ← 주관식 채점 + 결과 요약 로직
│   ├── rag_pipeline.py            ← 문서 → 임베딩 → 문제 생성
│   └── analytics.py               ← 역량 분석 리포트 생성
```

---

## 4. 각 파일 역할 상세

### `ai/client.py`
```python
# OpenAI 클라이언트를 싱글턴으로 관리
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

`.env` 파일에 추가:
```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
```

---

### `ai/question_generator.py`
```python
# 관리자가 요청하면 GPT가 문제 JSON 배열 반환
# 시스템 프롬프트: "당신은 IT 역량 평가 문제를 출제하는 전문가입니다."
# 사용자 프롬프트: "Spring Boot 트랜잭션 관련 중급 객관식 문제 5개를 JSON으로 생성하세요."
# 출력 형식: choices_json, answer_json, explanation 포함한 JSON 배열
```

---

### `ai/grader.py`
```python
# 시험 제출 시 호출
# 1. 객관식: 기존 로직 그대로 사용 (answer_json 비교)
# 2. 주관식/서술형: GPT에게 "모범답안 vs 응시자 답변"을 비교시켜 점수 산정
# 3. 전체 결과 기반으로 summary_comment 생성
#    예: "REST API 설계 역량은 우수하나, JPA 최적화 분야에서 보완이 필요합니다."
```

---

### `ai/rag_pipeline.py`
```python
# PDF/docx 업로드 → 텍스트 추출 → 청크 분할 → 임베딩 저장
# 문제 생성 시 관련 청크를 검색(유사도) → GPT 프롬프트에 컨텍스트로 추가
# 라이브러리: PyPDF2 or pdfminer, LangChain or llama-index, FAISS
```

---

## 5. 백엔드 라우터 연결 방법

### 신규 라우터 파일들 (`backend/routers/ai_questions.py` 등)
```python
from fastapi import APIRouter, Depends
from ai.question_generator import generate_questions  # ai 폴더에서 import

router = APIRouter(prefix="/api/ai", tags=["ai"])

@router.post("/generate-questions")
async def generate(topic: str, difficulty: str, count: int):
    result = await generate_questions(topic, difficulty, count)
    return result
```

### `main.py`에 라우터 등록
```python
from routers import ai_questions, ai_grader  # 신규 import 추가
app.include_router(ai_questions.router)
app.include_router(ai_grader.router)
```

---

## 6. 프론트엔드 연결

### `src/lib/api.ts`에 추가
```typescript
export const aiApi = {
  generateQuestions: async (topic: string, difficulty: string, count: number) => {
    const res = await api.post("/api/ai/generate-questions", { topic, difficulty, count });
    return res.data;
  },
  getSummary: async (recordId: number) => {
    const res = await api.get(`/api/ai/summary/${recordId}`);
    return res.data;
  },
};
```

### 이미 존재하는 화면들과 연결 위치
| AI 기능 | 연결할 프론트엔드 페이지 |
|---------|----------------------|
| 문제 자동 생성 | `AIQuestionGeneration.tsx` (이미 존재) |
| 문서 기반 RAG | `DocumentRAGManagement.tsx` (이미 존재) |
| AI 채점 결과 요약 | `ApplicantDetail.tsx`의 `summary_comment` 카드 |
| 역량 분석 리포트 | `ResultAnalytics.tsx` + `Dashboard.tsx` |

---

## 7. 설치해야 할 Python 패키지

```bash
# 백엔드에서 실행
pip install openai langchain faiss-cpu pymupdf python-docx tiktoken
```

`requirements.txt`에 추가:
```
openai>=1.0.0
langchain>=0.1.0
faiss-cpu>=1.7.4
pymupdf>=1.23.0
python-docx>=1.0.0
tiktoken>=0.5.0
```

---

## 8. AI Agent 활용 방법 (고급)

**AI Agent** = 단순 API 호출이 아니라, GPT가 스스로 계획을 세우고 여러 도구(tool)를 호출하는 방식

### 예시: "자동 문제 세트 구성 Agent"
1. 관리자가 "백엔드 개발자 중급 시험 30문제 세트 만들어줘" 요청
2. Agent가 스스로 판단:
   - Tool 1: DB에서 기존 문제 검색 (`questionsApi.list()`)
   - Tool 2: 부족한 역량 분야 파악 → GPT로 추가 문제 생성
   - Tool 3: 생성된 문제를 DB에 저장 + 시험지에 자동 배정
3. 결과 반환

### LangChain Agent 구조 예시
```python
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_openai import ChatOpenAI

# 도구 정의: DB 검색, 문제 생성, 저장
tools = [search_questions_tool, generate_question_tool, save_question_tool]
agent = create_openai_tools_agent(llm=ChatOpenAI(model="gpt-4o"), tools=tools, prompt=prompt)
executor = AgentExecutor(agent=agent, tools=tools)
```

---

## 9. GPT에게 물어볼 때 참고할 컨텍스트

GPT에게 요청할 때 아래를 함께 전달하면 정확한 답변을 받을 수 있습니다:

```
현재 시스템:
- FastAPI 백엔드 (Python 3.11)
- MariaDB (SQLAlchemy ORM)
- React + TypeScript 프론트엔드
- 주요 모델: Question (객관식/단답형/서술형), Diagnosis (시험지), Record (응시 결과)
- Record.answer_data = "1,0,2,1" (question_idxs 순서와 동일한 콤마 구분 답변)
- Record.summary_comment = AI가 생성할 총평 텍스트 저장 컬럼 (이미 존재)
- Record.competency_breakdown_json = {"역량명": 점수(%)} 형태 JSON

추가 목표:
- [여기에 원하는 AI 기능 설명]
```

---

## 10. 권장 구현 순서

1. ✅ `.env`에 `OPENAI_API_KEY` 추가
2. ✅ `backend/ai/client.py` 생성 (OpenAI 클라이언트)
3. ✅ `backend/ai/question_generator.py` 구현 → 기존 `AIQuestionGeneration.tsx`와 연결
4. ✅ `backend/ai/grader.py` 구현 → `exam.py`의 submit 로직에 주관식 채점 + 요약 추가
5. ✅ `backend/ai/rag_pipeline.py` 구현 → `DocumentRAGManagement.tsx`와 연결
6. ✅ `backend/ai/analytics.py` 구현 → `ResultAnalytics.tsx` 하단에 AI 분석 카드 추가
