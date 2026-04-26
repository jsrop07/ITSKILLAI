"""
초기 데이터 시드 스크립트
실행: python seed.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal, engine, Base
import models
from routers.auth import get_password_hash
import secrets

# 테이블 생성
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # ─────────────────────────────────────────
    # 1. 기본 관리자 계정
    # ─────────────────────────────────────────
    if not db.query(models.Admin).first():
        admin = models.Admin(
            email="admin@company.com",
            password_hash=get_password_hash("admin1234"),
            name="관리자",
            role=models.AdminRole.super_admin,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"✅ 관리자 계정 생성: {admin.email} / admin1234")
    else:
        admin = db.query(models.Admin).first()
        print(f"ℹ️  관리자 계정 이미 존재: {admin.email}")

    # ─────────────────────────────────────────
    # 2. 샘플 시험(Diagnosis) 데이터
    # ─────────────────────────────────────────
    if not db.query(models.Diagnosis).first():
        diagnoses_data = [
            {"title": "Spring Boot 심화", "description": "Spring Boot 프레임워크를 활용한 백엔드 개발 역량 평가",
             "target_role": "백엔드 개발자", "level": models.DiagnosisLevel.advanced,
             "question_count": 25, "duration_minutes": 90, "pass_score": 70,
             "status": models.DiagnosisStatus.active},
            {"title": "React 전문가", "description": "React 기반 프론트엔드 개발 역량 평가",
             "target_role": "프론트엔드 개발자", "level": models.DiagnosisLevel.advanced,
             "question_count": 30, "duration_minutes": 90, "pass_score": 70,
             "status": models.DiagnosisStatus.active},
            {"title": "웹 개발 종합", "description": "풀스택 웹 개발 종합 역량 평가",
             "target_role": "풀스택 개발자", "level": models.DiagnosisLevel.intermediate,
             "question_count": 40, "duration_minutes": 120, "pass_score": 70,
             "status": models.DiagnosisStatus.active},
            {"title": "Python 데이터 처리", "description": "Python 기반 데이터 처리 및 분석 역량 평가",
             "target_role": "데이터 엔지니어", "level": models.DiagnosisLevel.intermediate,
             "question_count": 28, "duration_minutes": 90, "pass_score": 70,
             "status": models.DiagnosisStatus.active},
            {"title": "Kubernetes 실무", "description": "Kubernetes 기반 컨테이너 오케스트레이션 실무 역량 평가",
             "target_role": "DevOps 엔지니어", "level": models.DiagnosisLevel.advanced,
             "question_count": 22, "duration_minutes": 75, "pass_score": 70,
             "status": models.DiagnosisStatus.inactive},
            {"title": "Node.js 실무", "description": "Node.js 기반 서버 개발 실무 역량 평가",
             "target_role": "백엔드 개발자", "level": models.DiagnosisLevel.intermediate,
             "question_count": 26, "duration_minutes": 90, "pass_score": 70,
             "status": models.DiagnosisStatus.active},
        ]
        for d in diagnoses_data:
            db.add(models.Diagnosis(**d, created_by=admin.admin_id))
        db.commit()
        print(f"✅ 시험 {len(diagnoses_data)}개 생성 완료")

    # ─────────────────────────────────────────
    # 3. 샘플 문제(Question) 데이터
    # ─────────────────────────────────────────
    if not db.query(models.Question).first():
        questions_data = [
            {
                "title": "Spring Boot에서 트랜잭션 관리를 위한 올바른 방법은?",
                "question_type": models.QuestionType.multiple_choice,
                "choices_json": ["@Autowired 사용", "@Transactional 애노테이션 사용", "synchronized 키워드 사용", "ThreadLocal 사용"],
                "answer_json": 1,
                "explanation": "@Transactional 애노테이션은 Spring의 선언적 트랜잭션 관리를 제공합니다.",
                "difficulty": "중급", "competency_type": "Spring Framework",
                "competency_tags_json": ["Spring", "Transaction"], "score": 4,
                "review_status": models.ReviewStatus.approved,
            },
            {
                "title": "RESTful API에서 멱등성(Idempotent)을 보장하는 HTTP 메서드를 모두 고르시오.",
                "question_type": models.QuestionType.multiple_choice,
                "choices_json": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                "answer_json": [0, 2, 3],
                "explanation": "GET, PUT, DELETE는 멱등성을 가집니다. POST, PATCH는 일반적으로 멱등성을 보장하지 않습니다.",
                "difficulty": "초급", "competency_type": "REST API 설계",
                "competency_tags_json": ["REST", "HTTP"], "score": 3,
                "review_status": models.ReviewStatus.approved,
            },
            {
                "title": "JPA N+1 문제를 해결하는 방법으로 적절하지 않은 것은?",
                "question_type": models.QuestionType.multiple_choice,
                "choices_json": ["Fetch Join 사용", "BatchSize 설정", "Eager Loading 무조건 사용", "EntityGraph 사용"],
                "answer_json": 2,
                "explanation": "Eager Loading을 무조건 사용하면 오히려 불필요한 데이터까지 로딩하여 성능이 저하됩니다.",
                "difficulty": "고급", "competency_type": "데이터베이스 최적화",
                "competency_tags_json": ["JPA", "ORM", "Performance"], "score": 5,
                "review_status": models.ReviewStatus.approved,
            },
            {
                "title": "JWT 토큰의 구조를 설명하시오.",
                "question_type": models.QuestionType.short_answer,
                "answer_json": "Header.Payload.Signature",
                "explanation": "JWT는 헤더(Header), 페이로드(Payload), 서명(Signature) 3부분으로 구성됩니다.",
                "difficulty": "중급", "competency_type": "보안 구현",
                "competency_tags_json": ["JWT", "Security"], "score": 3,
                "review_status": models.ReviewStatus.approved,
            },
            {
                "title": "마이크로서비스 아키텍처에서 서비스 간 통신 패턴으로 올바른 것은?",
                "question_type": models.QuestionType.multiple_choice,
                "choices_json": ["동기 HTTP 통신만 사용", "비동기 메시징만 사용", "동기 HTTP + 비동기 메시징 혼용", "직접 DB 공유"],
                "answer_json": 2,
                "explanation": "MSA에서는 동기(REST/gRPC)와 비동기(Message Queue) 방식을 상황에 맞게 혼용합니다.",
                "difficulty": "고급", "competency_type": "마이크로서비스",
                "competency_tags_json": ["MSA", "Architecture"], "score": 4,
                "review_status": models.ReviewStatus.approved,
            },
        ]
        q_objs = []
        for q_data in questions_data:
            q = models.Question(**q_data, source_type=models.SourceType.manual, created_by=admin.admin_id)
            db.add(q)
            q_objs.append(q)
        db.flush()

        # Spring Boot 시험에 문제 연결
        diag = db.query(models.Diagnosis).filter_by(title="Spring Boot 심화").first()
        if diag:
            diag.question_idxs = ",".join(str(q.question_id) for q in q_objs)
            diag.question_count = len(q_objs)

        db.commit()
        print(f"✅ 문제 {len(questions_data)}개 생성 및 시험 연결 완료")

    # ─────────────────────────────────────────
    # 4. 샘플 응시자 & 기록 데이터
    # ─────────────────────────────────────────
    if not db.query(models.Applicant).first():
        applicants_data = [
            {"name": "김민준", "email": "minjun.kim@example.com", "phone": "010-1234-5678",
             "target_role": "백엔드 개발자", "experience_level": "3년", "tech_stack": "Java, Spring Boot, MySQL"},
            {"name": "이서연", "email": "seoyeon.lee@example.com", "phone": "010-2345-6789",
             "target_role": "프론트엔드 개발자", "experience_level": "2년", "tech_stack": "React, TypeScript, CSS"},
            {"name": "박지호", "email": "jiho.park@example.com", "phone": "010-3456-7890",
             "target_role": "풀스택 개발자", "experience_level": "4년", "tech_stack": "Node.js, React, PostgreSQL"},
            {"name": "최수진", "email": "sujin.choi@example.com", "phone": "010-4567-8901",
             "target_role": "데이터 엔지니어", "experience_level": "2년", "tech_stack": "Python, Spark, Kafka"},
            {"name": "정현우", "email": "hyunwoo.jung@example.com", "phone": "010-5678-9012",
             "target_role": "DevOps 엔지니어", "experience_level": "3년", "tech_stack": "K8s, Docker, Terraform"},
        ]

        app_objs = []
        for a_data in applicants_data:
            a = models.Applicant(**a_data, status=models.ApplicantStatus.completed)
            db.add(a)
            app_objs.append(a)
        db.flush()

        # 응시 기록 생성
        diagnoses = db.query(models.Diagnosis).filter_by(status=models.DiagnosisStatus.active).limit(5).all()
        sample_scores = [85, 92, 78, 88, 95]
        for i, (app, diag, score) in enumerate(zip(app_objs, diagnoses, sample_scores)):
            token = secrets.token_urlsafe(16)
            record = models.Record(
                applicant_id=app.applicant_id,
                diagnosis_id=diag.diagnosis_id,
                login_token=token,
                status=models.RecordStatus.graded,
                total_score=float(score),
                pass_yn=score >= diag.pass_score,
                result_visible=True,
                competency_breakdown_json={"Spring Framework": 90, "REST API 설계": 85, "데이터베이스 최적화": 75},
            )
            db.add(record)

        db.commit()
        print(f"✅ 응시자 {len(applicants_data)}명 및 응시 기록 생성 완료")

    # ─────────────────────────────────────────
    # 5. page_contents 초기 데이터
    # ─────────────────────────────────────────
    if not db.query(models.PageContent).first():
        contents = [
            # 공통
            {"page_key": "common", "section_key": "site", "content_key": "name",
             "title": "IT 역량 평가 플랫폼", "body": None, "user_type": models.UserType.common},
            {"page_key": "common", "section_key": "site", "content_key": "subtitle",
             "title": "AI 기반 IT 역량진단 문제은행 시스템", "body": None, "user_type": models.UserType.common},

            # 관리자 로그인
            {"page_key": "admin_login", "section_key": "header", "content_key": "title",
             "title": "IT 역량 평가 플랫폼", "body": None, "user_type": models.UserType.admin},
            {"page_key": "admin_login", "section_key": "header", "content_key": "subtitle",
             "title": "관리자 로그인", "body": None, "user_type": models.UserType.admin},

            # 대시보드
            {"page_key": "admin_dashboard", "section_key": "header", "content_key": "title",
             "title": "대시보드", "body": "전체 시스템 현황 및 주요 지표", "user_type": models.UserType.admin},

            # 응시자 관리
            {"page_key": "admin_applicants", "section_key": "header", "content_key": "title",
             "title": "응시자 관리", "body": "시험 응시자 조회 및 관리", "user_type": models.UserType.admin},

            # 시험 관리
            {"page_key": "admin_exams", "section_key": "header", "content_key": "title",
             "title": "시험 관리", "body": "시험 목록 조회 및 설정 관리", "user_type": models.UserType.admin},

            # 문제 관리
            {"page_key": "admin_questions", "section_key": "header", "content_key": "title",
             "title": "문제 관리", "body": "문제 목록 조회 및 관리", "user_type": models.UserType.admin},

            # 응시자 시험 신청
            {"page_key": "applicant_apply", "section_key": "header", "content_key": "title",
             "title": "IT 역량 평가 신청", "body": None, "user_type": models.UserType.applicant},
            {"page_key": "applicant_apply", "section_key": "header", "content_key": "subtitle",
             "title": "기본 정보를 입력하여 시험을 신청해 주세요.", "body": None, "user_type": models.UserType.applicant},
            {"page_key": "applicant_apply", "section_key": "notice", "content_key": "body",
             "title": "시험 신청 안내",
             "body": "신청 완료 후 담당자가 시험을 배정하며, 로그인 토큰이 이메일로 발송됩니다.\n시험 시작 전 안내 페이지를 반드시 확인해 주세요.",
             "user_type": models.UserType.applicant},

            # 응시자 로그인
            {"page_key": "applicant_login", "section_key": "header", "content_key": "title",
             "title": "응시자 로그인", "body": None, "user_type": models.UserType.applicant},
            {"page_key": "applicant_login", "section_key": "header", "content_key": "subtitle",
             "title": "이름과 발급받은 로그인 토큰을 입력해 주세요.", "body": None, "user_type": models.UserType.applicant},

            # 시험 안내
            {"page_key": "applicant_intro", "section_key": "header", "content_key": "title",
             "title": "시험 시작 안내", "body": None, "user_type": models.UserType.applicant},
            {"page_key": "applicant_intro", "section_key": "notice", "content_key": "body",
             "title": "주의사항",
             "body": "• 시험 중 브라우저를 닫거나 새로고침하면 답안이 초기화될 수 있습니다.\n• 제한 시간이 종료되면 자동으로 제출됩니다.\n• 모든 문제를 꼼꼼히 읽고 답변해 주세요.\n• 시험 중 외부 자료 참고는 금지입니다.",
             "user_type": models.UserType.applicant},

            # 제출 완료
            {"page_key": "applicant_submit", "section_key": "header", "content_key": "title",
             "title": "제출 완료", "body": None, "user_type": models.UserType.applicant},
            {"page_key": "applicant_submit", "section_key": "header", "content_key": "subtitle",
             "title": "시험이 성공적으로 제출되었습니다.", "body": None, "user_type": models.UserType.applicant},
            {"page_key": "applicant_submit", "section_key": "notice", "content_key": "body",
             "title": "다음 단계 안내",
             "body": "채점이 완료되면 결과를 확인하실 수 있습니다.\n결과 공개 여부는 담당자가 결정하며, 공개 시 별도 안내됩니다.",
             "user_type": models.UserType.applicant},

            # 결과 확인
            {"page_key": "applicant_result", "section_key": "header", "content_key": "title",
             "title": "시험 결과 확인", "body": None, "user_type": models.UserType.applicant},
        ]
        for c in contents:
            db.add(models.PageContent(**c, is_active=True, updated_by=admin.admin_id))
        db.commit()
        print(f"✅ page_contents {len(contents)}개 생성 완료")

    print("\n🎉 시드 데이터 입력 완료!")
    print("   관리자 로그인: admin@company.com / admin1234")

except Exception as e:
    db.rollback()
    print(f"❌ 오류 발생: {e}")
    raise
finally:
    db.close()
