from fastapi import FastAPI
from database import engine, Base
from fastapi.middleware.cors import CORSMiddleware
# Routers
from routers import auth, dashboard, applicants, diagnoses, questions, records, exam, page_contents, ai_questions, ai_documents

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="IT 역량진단 API",
    description="IT 역량진단 문제은행 시스템 백엔드 API",
    version="1.0.0",
)

# CORS 설정 (프론트엔드 개발 서버 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(applicants.router)
app.include_router(diagnoses.router)
app.include_router(questions.router)
app.include_router(records.router)
app.include_router(exam.router)
app.include_router(page_contents.router)
app.include_router(ai_questions.router)
app.include_router(ai_documents.router)

@app.get("/")
def root():
    return {"message": "IT 역량진단 API 서버가 실행 중입니다.", "docs": "/docs"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
