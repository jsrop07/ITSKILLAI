# AI 문제 생성 파이프라인 고도화 WBS

## 현재 단계

현재 프로젝트는 ChromaDB 기반 Vector RAG + category metadata filter를 적용한 상태이며,
일반 AI 문제 생성에는 question_planner.py를 추가하여
문제 설계서 기반 생성 구조를 적용하고 있다.

아직 Hybrid RAG, reranker, LangGraph, fine-tuning, QLoRA, vLLM 자체 서빙은 적용하지 않았다.

## 현재 AI 생성 흐름

1. 사용자 문제 생성 요청
2. question_planner.py에서 문제 설계서 생성
3. question_generator.py에서 설계서 기반 문제 생성
4. 기존 검증 로직으로 JSON/정답/해설 검증
5. 정답 위치 재배치
6. 해설 재생성
7. pending 상태로 DB 저장

## 다음 목표

1. question_reviewer.py 추가
2. quality_score / reject_reasons 산출
3. RAG 생성에도 planner 적용
4. Hybrid RAG 구현
5. LangGraph 기반 워크플로우 전환
6. approved 문제 export