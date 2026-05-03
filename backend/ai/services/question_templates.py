# backend/ai/services/question_templates.py

from __future__ import annotations

import random


def build_ai_rag_advanced_template(topic: str) -> dict:
    """
    AI/RAG 고급 문제는 LLM 자유 생성에 맡기지 않고,
    검색 로그/파이프라인 조건이 포함된 body를 코드에서 직접 만든다.
    """

    templates = [
        {
            "title": "RAG 검색 결과 품질 진단",
            "body": (
                "사내 RAG 시스템에서 query=\"요구사항 변경 영향 분석\"으로 검색했을 때 "
                "top_k=5 결과 중 상위 3개 chunk가 실제 질문 의도와 다른 문서였다. "
                "검색 결과는 chunk #1 category=sql similarity=0.42, "
                "chunk #2 category=database similarity=0.39, "
                "chunk #3 category=software_engineering similarity=0.36으로 나타났다. "
                "metadata_filter는 적용되지 않았고 reranker도 미적용 상태다. "
                "사용자는 소프트웨어공학 문서의 요구사항 변경 영향 근거를 기대하고 있다. "
                "이 상황에서 RAG 검색 품질을 개선하기 위해 가장 우선적으로 점검해야 할 사항은 무엇인가?"
            ),
            "choices": [
                "metadata_filter로 category를 먼저 제한하고, reranker로 후보 chunk의 순서를 재평가한다.",
                "first-stage retrieval의 top_k를 늘려 후보를 더 확보하지만, category가 다른 chunk가 섞이는 문제는 별도로 해결하지 않는다.",
                "reranker를 적용해 상위 chunk 순서만 조정하지만, 관련 문서가 후보군에 충분히 포함되는지는 확인하지 않는다.",
                "embedding 모델 교체를 우선 검토하지만, 현재 검색 결과의 category 불일치와 filter 미적용 문제는 직접 해결하지 못한다.",
                "query rewrite로 질의를 확장하지만, metadata 조건과 chunk category 불일치 문제는 후속 단계로 미룬다.",
            ],
            "answer": 1,
            "explanation": (
                "정답은 1번입니다. 현재 문제의 핵심은 검색 후보에 질문 의도와 다른 category의 chunk가 상위에 섞이고 있다는 점입니다. "
                "따라서 metadata_filter로 검색 범위를 먼저 제한하고, reranker로 후보 chunk의 순서를 재평가하는 판단이 가장 타당합니다. "
                "top_k만 늘리는 방식은 후보 수를 늘릴 수 있지만 관련 없는 chunk도 함께 늘어날 수 있습니다. "
                "reranker만 적용하는 방식은 후보군 자체에 관련 문서가 충분히 포함되지 않으면 효과가 제한됩니다. "
                "embedding 모델 교체나 query rewrite는 일부 개선 가능성이 있지만, 현재 로그에서 드러난 category 불일치와 filter 미적용 문제를 우선 해결하지 못합니다."
            ),
            "competency_tags": ["RAG", "검색 품질", "metadata filter", "reranker"],
            "answer_intent": "metadata_filter_and_reranker",
            "distractor_intents": [
                "increase_top_k_only",
                "reranker_only",
                "embedding_model_only",
                "query_rewrite_only",
            ],
        },
        {
            "title": "Reranker 적용 범위 판단",
            "body": (
                "사내 RAG 시스템에서 query=\"개인정보 접근 권한 정책\"으로 검색했을 때 "
                "first-stage retrieval의 top_k=20 후보 중 실제 정답 근거 문서는 12위에 위치했다. "
                "현재 검색 결과는 chunk #1 similarity=0.47, chunk #2 similarity=0.45처럼 유사도는 높지만 "
                "일반 보안 정책 설명에 치우쳐 있고, reranker를 적용하면 정답 근거 문서가 상위 3개 안으로 올라온다. "
                "다만 reranker 적용 시 latency p95가 0.8초에서 1.7초로 증가한다. "
                "이 상황에서 검색 정확도와 응답 지연 시간의 트레이드오프를 고려했을 때 가장 적절한 판단은 무엇인가?"
            ),
            "choices": [
                "reranker를 전체 후보에 무조건 적용하기보다 candidate 수와 적용 구간을 조정해 accuracy 개선 폭과 latency 증가를 함께 측정한다.",
                "reranker를 제거해 p95 latency를 낮추고, 검색 정확도 저하는 query rewrite만으로 보완한다.",
                "top_k를 크게 늘려 정답 문서가 포함될 가능성을 높이지만, reranker 비용과 응답 시간 증가는 별도로 고려하지 않는다.",
                "embedding 모델을 교체해 first-stage retrieval의 유사도를 높이는 데 집중하고, 재정렬 단계의 비용은 이후에 검토한다.",
                "keyword search 비중을 높여 정확 키워드 매칭을 강화하지만, 의미 기반 검색 결과와의 결합 순위는 조정하지 않는다.",
            ],
            "answer": 1,
            "explanation": (
                "정답은 1번입니다. 현재 로그에서는 reranker가 정답 근거 문서의 순위를 개선하지만 p95 latency를 크게 증가시키는 상황입니다. "
                "따라서 전체 후보에 일괄 적용하기보다 candidate 수와 reranker 적용 구간을 조정하면서 accuracy와 latency를 함께 측정해야 합니다. "
                "reranker를 제거하면 응답 시간은 줄 수 있지만 정답 근거 문서가 하위에 머무르는 문제가 남습니다. "
                "top_k 확대나 embedding 모델 교체는 후보 품질 개선에 도움이 될 수 있으나, 재정렬 비용과 응답 시간 문제를 직접 다루지 못합니다."
            ),
            "competency_tags": ["RAG", "reranker", "latency", "accuracy"],
            "answer_intent": "tune_reranker_scope_with_latency_measurement",
            "distractor_intents": [
                "remove_reranker_for_latency_only",
                "increase_top_k_without_latency_check",
                "replace_embedding_model_only",
                "increase_keyword_search_weight_only",
            ],
        },
        {
            "title": "Hybrid Search 도입 판단",
            "body": (
                "사내 문서 RAG 시스템에서 query=\"NCS 요구사항 확인 비기능 요구사항\"으로 검색했을 때 "
                "vector search top_k=5 결과가 의미적으로 비슷한 일반 소프트웨어공학 문서에 집중되었다. "
                "검색 결과는 chunk #1 similarity=0.43, chunk #2 similarity=0.41, chunk #3 similarity=0.40 수준이며, "
                "정확히 일치해야 하는 키워드인 \"비기능 요구사항\"과 문서 category metadata가 충분히 반영되지 않았다. "
                "현재 keyword search는 사용하지 않고 metadata_filter도 미적용 상태다. "
                "이 상황에서 검색 품질을 개선하기 위해 가장 우선적으로 검토해야 할 판단은 무엇인가?"
            ),
            "choices": [
                "vector search에 keyword search와 metadata_filter를 결합해 정확 키워드와 문서 범위를 함께 반영한다.",
                "vector search의 top_k만 늘려 더 많은 후보를 가져오고, 키워드 일치 여부는 후속 LLM 응답 단계에서 보완한다.",
                "embedding 모델을 교체해 전체 similarity를 높이는 방향을 우선 검토하지만, 정확 키워드 누락 문제는 별도로 다루지 않는다.",
                "reranker만 추가해 현재 검색 후보의 순서를 조정하지만, 후보군에 정확 키워드 문서가 포함되는지는 확인하지 않는다.",
                "query를 더 짧게 단순화해 벡터 검색의 응답 속도를 개선하지만, 비기능 요구사항이라는 핵심 용어 반영은 약해질 수 있다.",
            ],
            "answer": 1,
            "explanation": (
                "정답은 1번입니다. 현재 문제는 의미적으로 유사한 문서는 검색되지만, 정확히 일치해야 하는 키워드와 문서 category 조건이 충분히 반영되지 않는 상황입니다. "
                "따라서 vector search만 사용하는 방식보다 keyword search와 metadata_filter를 결합해 검색 범위를 보정하는 판단이 적절합니다. "
                "top_k만 늘리면 관련 없는 후보도 함께 늘어날 수 있습니다. "
                "embedding 모델 교체나 reranker 추가는 일부 개선 가능성이 있지만, 정확 키워드 누락과 metadata 미적용 문제를 직접 해결하지 못합니다."
            ),
            "competency_tags": ["RAG", "hybrid search", "vector search", "keyword search"],
            "answer_intent": "combine_vector_keyword_and_metadata_filter",
            "distractor_intents": [
                "increase_vector_top_k_only",
                "replace_embedding_model_only",
                "reranker_only_without_candidate_fix",
                "simplify_query_for_latency_only",
            ],
        },
    ]

    selected = random.choice(templates)

    return {
        "title": selected["title"],
        "body": selected["body"],
        "choices": selected["choices"],
        "answer": selected["answer"],
        "explanation": selected["explanation"],
        "difficulty": "고급",
        "competency_type": "ai",
        "competency_tags": selected["competency_tags"],
        "score": 5,
        
        # LLM이 choices/explanation만 생성할 때 사용할 의도 정보
        "answer_intent": selected["answer_intent"],
        "distractor_intents": selected["distractor_intents"],
    }

def build_sql_advanced_template(
    topic: str,
    exclude_formats: list[str] | None = None,
) -> dict:
    """
    SQL 고급 문제는 LLM 자유 생성에 맡기지 않고,
    테이블 구조/쿼리/데이터 규모/실행 계획/운영 조건이 포함된 body를 코드에서 직접 만든다.
    """

    templates = [
        {
            "title": "대용량 주문 조회 쿼리의 인덱스 설계 판단",
            "format": "index_plan_choice",
            "body": f"""
            다음은 관리자 대시보드의 주문 조회 API에서 발생한 SQL 성능 저하 상황이다.
            주제는 '{topic}'이다.

            [테이블 구조]
            orders(
                id BIGINT PRIMARY KEY,
                user_id BIGINT,
                order_status VARCHAR(20),
                payment_status VARCHAR(20),
                created_at DATETIME,
                total_amount DECIMAL(12, 2)
            )

            [현재 인덱스]
            - PRIMARY KEY(id)
            - idx_orders_user_id(user_id)
            - idx_orders_created_at(created_at)

            [데이터 규모 및 분포]
            - orders 테이블: 약 8,500만 건
            - 최근 30일 데이터: 약 620만 건
            - order_status='PAID' 비율: 약 38%
            - payment_status='DONE' 비율: 약 41%
            - 관리자 조회 API라서 특정 user_id 조건은 없음

            [문제 쿼리]
            SELECT id, user_id, order_status, payment_status, created_at, total_amount
            FROM orders
            WHERE order_status = 'PAID'
                AND payment_status = 'DONE'
                AND created_at >= '2026-04-01 00:00:00'
            ORDER BY created_at DESC
            LIMIT 50;

            [실행 계획 요약]
            - key: idx_orders_created_at
            - type: range
            - rows: 6,200,000
            - filtered: 15.2
            - Extra: Using index condition; Using where

            [운영 조건]
            orders 테이블에는 초당 300~500건의 INSERT가 발생하므로, 인덱스 추가 시 쓰기 지연도 고려해야 한다.

            이 상황에서 가장 적절한 성능 개선 판단은 무엇인가?
            """.strip(),
            "choices": [
                "order_status, payment_status, created_at 순서의 복합 인덱스를 후보로 검토하고, 실행 계획의 rows와 filtered 감소 및 INSERT 쓰기 지연 증가를 함께 측정한다.",
                "idx_orders_created_at 단일 인덱스를 유지한 채 LIMIT 50 조건만 활용해 조회 범위를 줄이고, 상태 조건은 WHERE 필터링에 맡긴다.",
                "order_status와 payment_status 각각에 단일 인덱스를 추가한 뒤 옵티마이저가 조건별 인덱스를 선택하도록 두고, 복합 인덱스 검토는 제외한다.",
                "total_amount까지 포함한 커버링 인덱스를 먼저 구성해 SELECT 컬럼 접근을 줄이고, 조건 컬럼의 선택도와 쓰기 부하는 후순위로 검토한다.",
                "관리자 조회 API에도 user_id 조건을 추가하도록 화면 검색 조건을 변경해 기존 idx_orders_user_id 인덱스를 활용하는 방향을 우선 검토한다.",
            ],
            "answer": 1,
            "explanation": (
                "정답은 1번입니다. 현재 쿼리는 order_status, payment_status, created_at 조건을 함께 사용하고 "
                "created_at DESC 정렬과 LIMIT가 있으므로 조건 컬럼과 정렬 컬럼을 고려한 복합 인덱스를 후보로 검토하는 것이 적절합니다. "
                "다만 orders는 쓰기 부하가 큰 테이블이므로 실행 계획의 rows 감소뿐 아니라 INSERT 지연과 디스크 사용량도 함께 측정해야 합니다."
            ),
            "competency_tags": ["SQL", "인덱스", "실행 계획", "쿼리 최적화"],
            "answer_intent": "composite_index_with_execution_plan_and_write_cost",
            "distractor_intents": [
                "keep_single_created_at_index_only",
                "covering_index_without_selectivity_check",
                "single_status_index_only",
                "force_unrelated_user_id_condition",
            ],
        },
        {
            "title": "JOIN 쿼리의 실행 계획과 복합 인덱스 판단",
            "format": "join_index_choice",
            "body": f"""
            다음은 고객 CS 화면에서 회원과 주문 정보를 함께 조회하는 SQL 성능 문제다.
            주제는 '{topic}'이다.

            [테이블 구조]
            users(
                id BIGINT PRIMARY KEY,
                email VARCHAR(255),
                grade VARCHAR(20),
                created_at DATETIME
            )

            orders(
                id BIGINT PRIMARY KEY,
                user_id BIGINT,
                order_status VARCHAR(20),
                created_at DATETIME,
                total_amount DECIMAL(12, 2)
            )

            [현재 인덱스]
            users:
            - PRIMARY KEY(id)
            - idx_users_grade(grade)

            orders:
            - PRIMARY KEY(id)
            - idx_orders_user_id(user_id)
            - idx_orders_created_at(created_at)

            [데이터 규모 및 분포]
            - users 테이블: 약 1,200만 건
            - orders 테이블: 약 8,500만 건
            - VIP 회원 비율: 약 3%
            - 최근 7일 주문: 약 180만 건

            [문제 쿼리]
            SELECT u.id, u.email, u.grade, o.id AS order_id, o.created_at, o.total_amount
            FROM users u
            JOIN orders o ON o.user_id = u.id
            WHERE u.grade = 'VIP'
                AND o.order_status = 'PAID'
                AND o.created_at >= '2026-04-24 00:00:00'
            ORDER BY o.created_at DESC
            LIMIT 100;

            [실행 계획 요약]
            users:
            - key: idx_users_grade
            - rows: 360,000
            - Extra: Using where

            orders:
            - key: idx_orders_user_id
            - rows per user: 평균 14
            - Extra: Using where; Using filesort

            [운영 조건]
            CS 화면은 피크 시간대 초당 80회 이상 호출되며, orders 테이블은 쓰기 부하도 높다.

            이 상황에서 가장 적절한 성능 개선 판단은 무엇인가?
            """.strip(),
            "choices": [
                "users.grade로 후보 회원을 줄인 뒤 orders(user_id, order_status, created_at) 복합 인덱스를 검토하고, filesort 제거 여부와 INSERT 쓰기 부하를 함께 측정한다.",
                "orders.created_at 단일 인덱스를 우선 사용해 최근 주문부터 읽고, users와의 JOIN 비용은 애플리케이션 캐시로 보완하는 방향을 검토한다.",
                "users.email 컬럼에 인덱스를 추가해 SELECT 대상 컬럼 접근을 줄이고, JOIN 조건과 주문 정렬 문제는 기존 인덱스에 맡긴다.",
                "idx_orders_user_id 인덱스를 유지한 채 order_status와 created_at 조건은 WHERE 필터링으로 처리하고, filesort는 결과 건수 제한으로 완화한다.",
                "VIP 회원 비율이 낮다는 점에 집중해 idx_users_grade만 활용하고, orders 단계의 rows per user와 filesort 문제는 별도 인덱스 없이 모니터링한다.",
            ],
            "answer": 1,
            "explanation": (
                "정답은 1번입니다. 이 쿼리는 users.grade로 후보 사용자를 줄인 뒤 orders에서 user_id 조인, "
                "order_status 필터, created_at 정렬을 함께 처리해야 합니다. "
                "현재 orders 단계에서 Using filesort가 발생하므로 orders(user_id, order_status, created_at) 같은 복합 인덱스를 후보로 검토하고, "
                "filesort 제거와 rows 감소, 쓰기 비용 증가를 함께 측정하는 판단이 적절합니다."
            ),
            "competency_tags": ["SQL", "JOIN", "복합 인덱스", "실행 계획"],
            "answer_intent": "join_composite_index_with_filesort_and_write_cost",
            "distractor_intents": [
                "use_created_at_index_and_app_join",
                "index_select_column_email",
                "keep_user_id_index_only",
                "check_only_low_ratio_grade_index",
            ],
        },
        {
            "title": "쿠폰 발급 트랜잭션의 락 경합 개선 판단",
            "format": "transaction_lock_case",
            "body": f"""
            다음은 이벤트 쿠폰 발급 API에서 발생한 트랜잭션 지연 상황이다.
            주제는 '{topic}'이다.

            [테이블 구조]
            coupon_issue(
                id BIGINT PRIMARY KEY,
                coupon_id BIGINT,
                user_id BIGINT,
                issue_status VARCHAR(20),
                created_at DATETIME
            )

            [현재 인덱스]
            - PRIMARY KEY(id)
            - idx_coupon_issue_user_id(user_id)
            - idx_coupon_issue_coupon_id(coupon_id)

            [데이터 규모 및 조건]
            - coupon_issue 테이블: 약 3,200만 건
            - 특정 coupon_id에 이벤트 시간대 요청이 집중됨
            - 동일 사용자의 중복 발급은 허용되지 않음

            [현재 트랜잭션 흐름]
            BEGIN;

            SELECT id
            FROM coupon_issue
            WHERE coupon_id = 1001
                AND user_id = 50123
            FOR UPDATE;

            INSERT INTO coupon_issue(coupon_id, user_id, issue_status, created_at)
            VALUES (1001, 50123, 'ISSUED', NOW());

            COMMIT;

            [관측 로그]
            - 피크 시간대 Lock wait timeout exceeded 발생
            - SELECT FOR UPDATE 단계에서 대기 시간 급증
            - 실행 계획은 idx_coupon_issue_coupon_id 사용
            - rows: 820,000
            - filtered: 10.0

            [운영 조건]
            중복 발급 방지는 반드시 필요하므로 단순히 트랜잭션을 제거할 수는 없다.

            이 상황에서 가장 적절한 개선 판단은 무엇인가?
            """.strip(),
            "choices": [
                "coupon_id, user_id 조합의 유니크 복합 인덱스를 검토해 중복 검사 범위를 좁히고, SELECT FOR UPDATE의 락 범위와 락 경합 변화를 측정한다.",
                "SELECT FOR UPDATE를 제거하고 INSERT 이후 중복 발급 여부를 배치로 정리해 락 대기를 줄이되, 중복 발급 방지 책임을 사후 처리로 넘긴다.",
                "idx_coupon_issue_coupon_id 단일 인덱스를 유지하면서 트랜잭션 격리 수준을 높여 동시성 충돌을 제어하고, 탐색 rows 증가는 감수한다.",
                "idx_coupon_issue_user_id 인덱스를 강제로 사용하도록 힌트를 추가하고, coupon_id 조건은 WHERE 필터링으로 처리해 사용자 단위 조회를 우선한다.",
                "INSERT 전에 SELECT COUNT(*) 검사를 추가해 중복 여부를 한 번 더 확인하고, 기존 SELECT FOR UPDATE 기반 트랜잭션 구조는 유지한다.",
            ],
            "answer": 1,
            "explanation": (
                "정답은 1번입니다. 현재 SELECT FOR UPDATE가 coupon_id 단일 인덱스를 사용하면서 많은 행을 스캔하고 락 경합을 유발하고 있습니다. "
                "중복 발급 방지가 핵심 요구사항이므로 coupon_id, user_id 조합의 유니크 복합 인덱스를 검토해 탐색 범위와 락 범위를 좁히고, "
                "충돌 빈도와 쓰기 비용을 함께 확인하는 것이 적절합니다."
            ),
            "competency_tags": ["SQL", "트랜잭션", "락", "유니크 인덱스"],
            "answer_intent": "unique_composite_index_to_reduce_lock_range",
            "distractor_intents": [
                "remove_for_update_and_batch_deduplicate",
                "increase_isolation_with_single_coupon_index",
                "force_user_id_index_only",
                "add_count_query_before_insert",
            ],
        },
        {
            "title": "GROUP BY 집계 쿼리의 실행 계획 개선 판단",
            "format": "group_by_aggregation_case",
            "body": f"""
                다음은 관리자 통계 화면에서 발생한 GROUP BY 집계 쿼리 성능 저하 상황이다.
                주제는 '{topic}'이다.

                [테이블 구조]
                order_items(
                    id BIGINT PRIMARY KEY,
                    product_id BIGINT,
                    order_status VARCHAR(20),
                    category_id BIGINT,
                    created_at DATETIME,
                    quantity INT,
                    price DECIMAL(12, 2)
                )

                [현재 인덱스]
                - PRIMARY KEY(id)
                - idx_order_items_product_id(product_id)
                - idx_order_items_created_at(created_at)

                [데이터 규모 및 분포]
                - order_items 테이블: 약 1억 2천만 건
                - 최근 90일 데이터: 약 1,800만 건
                - order_status='PAID' 비율: 약 42%
                - category_id 조건은 특정 대분류 상품군에 해당하며 전체의 약 18%를 차지함

                [문제 쿼리]
                SELECT product_id, SUM(quantity) AS total_quantity, SUM(price * quantity) AS total_sales
                FROM order_items
                WHERE order_status = 'PAID'
                    AND category_id = 10
                    AND created_at >= '2026-02-01 00:00:00'
                GROUP BY product_id
                ORDER BY total_sales DESC
                LIMIT 100;

                [실행 계획 요약]
                - key: idx_order_items_created_at
                - type: range
                - rows: 18,000,000
                - filtered: 7.4
                - Extra: Using where; Using temporary; Using filesort

                [운영 조건]
                통계 화면은 하루 수십 회 호출되지만, 피크 시간대에는 관리자 여러 명이 동시에 조회한다.
                order_items 테이블에는 주문 생성 시 지속적인 INSERT가 발생한다.

                이 상황에서 가장 적절한 성능 개선 판단은 무엇인가?
                """.strip(),
            "choices": [
                "order_status, category_id, created_at, product_id 복합 인덱스를 검토하고 temporary/filesort와 INSERT 비용 변화를 측정한다.",
                "product_id 중심 인덱스를 검토한 뒤 GROUP BY 처리량과 WHERE 필터 후 rows 변화를 실행 계획에서 비교한다.",
                "created_at 인덱스를 유지한 채 최근 90일 range 스캔 rows와 filtered 변화를 확인하고 LIMIT 효과를 측정한다.",
                "price, quantity 포함 인덱스를 검토한 뒤 집계 계산의 테이블 접근 감소와 인덱스 크기 증가를 비교한다.",
                "통계 결과 캐싱을 적용한 뒤 캐시 미스 시 rows, temporary/filesort 발생 여부와 동시 조회 부하를 측정한다.",
            ],
            "answer": 1,
            "explanation": (
                "정답은 1번입니다. 현재 쿼리는 order_status, category_id, created_at 조건으로 대량 데이터를 줄인 뒤 product_id로 GROUP BY하고 total_sales 기준으로 정렬합니다. "
                "실행 계획에서 rows가 크고 Using temporary, Using filesort가 발생하므로 조건 컬럼과 그룹화 컬럼을 고려한 복합 인덱스를 후보로 검토해야 합니다. "
                "다만 order_items는 쓰기 부하가 있는 테이블이므로 INSERT 지연과 인덱스 유지 비용도 함께 측정해야 합니다."
            ),
            "competency_tags": ["SQL", "GROUP BY", "집계", "실행 계획"],
            "answer_intent": "group_by_composite_index_with_temp_filesort_and_write_cost",
            "distractor_intents": [
                "single_group_by_column_index_only",
                "keep_created_at_index_only",
                "covering_index_without_selectivity_check",
                "cache_without_execution_plan_fix",
            ],
        },
        {
            "title": "OFFSET 기반 페이징 쿼리의 성능 개선 판단",
            "format": "pagination_optimization_case",
            "body": f"""
            다음은 고객 목록 관리 화면에서 발생한 페이징 성능 저하 상황이다.
            주제는 '{topic}'이다.

            [테이블 구조]
            customers(
                id BIGINT PRIMARY KEY,
                email VARCHAR(255),
                grade VARCHAR(20),
                status VARCHAR(20),
            created_at DATETIME,
            last_login_at DATETIME
            )

            [현재 인덱스]
            - PRIMARY KEY(id)
            - idx_customers_created_at(created_at)
            - idx_customers_status(status)

            [데이터 규모 및 분포]
            - customers 테이블: 약 2,400만 건
            - status='ACTIVE' 비율: 약 64%
            - grade='VIP' 비율: 약 5%

            [문제 쿼리]
            SELECT id, email, grade, status, created_at, last_login_at
            FROM customers
                WHERE status = 'ACTIVE'
                ORDER BY created_at DESC
            LIMIT 50 OFFSET 500000;

            [실행 계획 요약]
            - key: idx_customers_created_at
            - type: index
            - rows: 500,050 이상 스캔
            - filtered: 64.0
            - Extra: Using where

            [운영 조건]
            관리자 화면에서 깊은 페이지로 이동할수록 응답 시간이 급격히 증가한다.
            검색 조건은 status와 created_at 정렬이 중심이며, 무한 스크롤 방식으로 UI 변경도 가능하다.

            이 상황에서 가장 적절한 성능 개선 판단은 무엇인가?
            """.strip(),
            "choices": [
                "OFFSET 기반 깊은 페이지 이동을 줄이고, status와 created_at 기준의 커서 기반 페이지네이션을 검토하며 실행 계획의 스캔 rows 감소를 측정한다.",
                "LIMIT 값을 50에서 100으로 늘려 한 번에 더 많은 데이터를 가져오고, OFFSET이 커질 때의 스캔 비용은 동일하게 유지한다.",
                "email 컬럼에 인덱스를 추가해 SELECT 대상 컬럼 접근을 줄이고, status 필터와 created_at 정렬은 기존 인덱스에 맡긴다.",
                "created_at 단일 인덱스가 사용되고 있으므로 OFFSET 값이 커져도 인덱스 스캔으로 충분하다고 보고 쿼리 구조는 유지한다.",
                "status 단일 인덱스를 강제로 사용해 ACTIVE 고객만 먼저 찾고, created_at 정렬 비용은 filesort로 처리한다.",
            ],
            "answer": 1,
            "explanation": (
                "정답은 1번입니다. OFFSET 500000 방식은 앞의 많은 행을 건너뛰기 위해 대량 스캔이 발생하므로 깊은 페이지에서 성능이 급격히 저하됩니다. "
                "status와 created_at 정렬 기준을 활용한 커서 기반 페이지네이션을 검토하면 불필요한 스캔 rows를 줄일 수 있습니다. "
                "LIMIT 증가나 SELECT 컬럼 인덱스 추가는 OFFSET으로 인한 근본적인 스캔 비용을 해결하지 못합니다."
            ),
            "competency_tags": ["SQL", "Pagination", "OFFSET", "쿼리 최적화"],
            "answer_intent": "cursor_pagination_with_index_scan_reduction",
            "distractor_intents": [
                "increase_limit_only",
                "index_select_column_email",
                "keep_offset_with_created_at_index",
                "force_status_index_with_filesort",
            ],
        },
        {
            "title": "커버링 인덱스 적용의 trade-off 판단",
            "format": "covering_index_tradeoff_case",
            "body": f"""
            다음은 상품 검색 API에서 커버링 인덱스 적용 여부를 검토하는 상황이다.
            주제는 '{topic}'이다.

            [테이블 구조]
            products(
                id BIGINT PRIMARY KEY,
                seller_id BIGINT,
                category_id BIGINT,
                status VARCHAR(20),
                price DECIMAL(12, 2),
                stock_count INT,
            updated_at DATETIME,
            description TEXT
            )

            [현재 인덱스]
            - PRIMARY KEY(id)
            - idx_products_category_id(category_id)
            - idx_products_updated_at(updated_at)

            [데이터 규모 및 분포]
            - products 테이블: 약 3,800만 건
            - category_id=2001 조건은 전체의 약 6%
            - status='ON_SALE' 비율은 약 55%
            - 상품 가격과 재고는 자주 변경됨

            [문제 쿼리]
            SELECT id, seller_id, price, stock_count, updated_at
            FROM products
                WHERE category_id = 2001
                AND status = 'ON_SALE'
                ORDER BY updated_at DESC
            LIMIT 100;

            [실행 계획 요약]
            - key: idx_products_updated_at
            - type: index
            - rows: 900,000
            - filtered: 3.1
            - Extra: Using where

            [인덱스 후보]
            A. idx_products_category_status_updated(category_id, status, updated_at)
            B. idx_products_covering(category_id, status, updated_at, id, seller_id, price, stock_count)

            [운영 조건]
            이 API는 읽기 호출이 많지만, price와 stock_count는 판매/재고 변경으로 자주 UPDATE된다.
            인덱스 크기가 커지면 쓰기 비용과 버퍼풀 사용량이 증가할 수 있다.

            이 상황에서 가장 적절한 인덱스 검토 판단은 무엇인가?
            """.strip(),
            "choices": [
                "조건과 정렬을 우선 만족하는 복합 인덱스 A를 기준 후보로 검토하고, 커버링 인덱스 B는 읽기 개선 폭과 UPDATE 쓰기 비용 증가를 함께 비교한다.",
                "SELECT 컬럼을 모두 포함하는 커버링 인덱스 B를 우선 적용해 테이블 접근 감소를 노리고, price와 stock_count 변경 비용 평가는 후순위로 둔다.",
                "updated_at 단일 인덱스가 정렬에 사용되므로 기존 인덱스를 유지하고, category_id와 status 조건은 where 필터링에 맡긴다.",
                "description 컬럼까지 포함한 더 넓은 커버링 인덱스를 만들어 상품 조회 API 전체를 인덱스만으로 처리하는 방향을 우선 검토한다.",
                "category_id 단일 인덱스를 추가해 상품군을 먼저 줄이고, status 필터와 updated_at 정렬은 filesort로 처리한다.",
            ],
            "answer": 1,
            "explanation": (
                "정답은 1번입니다. 현재 쿼리는 category_id와 status 조건, updated_at 정렬을 함께 사용하므로 이를 우선 만족하는 복합 인덱스 A가 기본 후보가 됩니다. "
                "커버링 인덱스 B는 테이블 접근을 줄일 수 있지만 price와 stock_count가 자주 변경되므로 UPDATE 비용과 인덱스 크기 증가를 함께 비교해야 합니다. "
                "무조건 넓은 커버링 인덱스를 적용하는 것은 쓰기 부하와 저장 공간 측면에서 위험할 수 있습니다."
            ),
            "competency_tags": ["SQL", "커버링 인덱스", "Trade-off", "쓰기 비용"],
            "answer_intent": "covering_index_tradeoff_with_update_cost",
            "distractor_intents": [
                "apply_covering_index_without_update_cost",
                "keep_updated_at_index_only",
                "include_text_column_in_covering_index",
                "single_category_index_with_filesort",
            ],
        },
    ]

    topic_text = topic or ""
    excluded = set(exclude_formats or [])

    def pick_by_format(format_name: str) -> dict:
        candidates = [
            template for template in templates
            if template.get("format") == format_name
            and template.get("format") not in excluded
        ]

        if candidates:
            return random.choice(candidates)

        # 요청 topic에 맞는 format이 이미 사용되었거나 없으면,
        # 아직 사용하지 않은 다른 SQL 템플릿 중에서 선택한다.
        fallback_candidates = [
            template for template in templates
            if template.get("format") not in excluded
        ]

        if fallback_candidates:
            return random.choice(fallback_candidates)

        return random.choice(templates)

    if any(keyword in topic_text for keyword in ["트랜잭션", "락", "동시성", "격리", "쿠폰", "lock"]):
        selected = pick_by_format("transaction_lock_case")
    elif any(keyword in topic_text for keyword in ["JOIN", "join", "조인"]):
        selected = pick_by_format("join_index_choice")
    elif any(keyword in topic_text for keyword in ["GROUP BY", "group by", "집계", "COUNT", "SUM", "통계"]):
        selected = pick_by_format("group_by_aggregation_case")
    elif any(keyword in topic_text for keyword in ["페이징", "pagination", "OFFSET", "offset", "LIMIT", "커서"]):
        selected = pick_by_format("pagination_optimization_case")
    elif any(keyword in topic_text for keyword in ["커버링", "covering", "커버링 인덱스", "SELECT 컬럼", "trade-off", "트레이드오프"]):
        selected = pick_by_format("covering_index_tradeoff_case")
    elif any(keyword in topic_text for keyword in ["인덱스", "index", "Index", "실행 계획", "실행계획", "쿼리 최적화"]):
        selected = pick_by_format("index_plan_choice")
    else:
        fallback_candidates = [
            template for template in templates
            if template.get("format") not in excluded
        ]
        selected = random.choice(fallback_candidates or templates)

    return {
        "title": selected["title"],
        "body": selected["body"],
        "choices": selected["choices"],
        "answer": selected["answer"],
        "explanation": selected["explanation"],
        "difficulty": "고급",
        "competency_type": "sql",
        "competency_tags": selected["competency_tags"],
        "score": 5,
        # count > 1 생성 시 같은 SQL 템플릿 반복을 줄이기 위한 내부 필드
        "template_format": selected.get("format"),
        # LLM이 choices/explanation만 생성할 때 사용할 의도 정보
        "answer_intent": selected["answer_intent"],
        "distractor_intents": selected["distractor_intents"],
    }