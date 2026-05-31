import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import requests


GENERAL_ENDPOINT = "/api/ai/generate-questions"
RAG_ENDPOINT = "/api/ai/generate-questions-from-document"


def load_jobs(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"jobs 파일을 찾을 수 없습니다: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def post_job(base_url: str, job: dict, timeout: int) -> dict:
    job_type = job.get("type")
    payload = job.get("payload", {})

    if job_type == "general":
        endpoint = GENERAL_ENDPOINT
    elif job_type == "rag":
        endpoint = RAG_ENDPOINT
    else:
        raise ValueError(f"지원하지 않는 job type입니다: {job_type}")

    url = base_url.rstrip("/") + endpoint

    started_at = datetime.now().isoformat(timespec="seconds")

    try:
        response = requests.post(url, json=payload, timeout=timeout)

        result = {
            "name": job.get("name"),
            "type": job_type,
            "endpoint": endpoint,
            "payload": payload,
            "status_code": response.status_code,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "success": response.ok,
        }

        try:
            body = response.json()
        except Exception:
            body = response.text

        result["response"] = body

        if response.ok and isinstance(body, dict):
            result["created_count"] = body.get("count") or len(body.get("questions", []))
        else:
            result["created_count"] = 0

        return result

    except Exception as e:
        return {
            "name": job.get("name"),
            "type": job_type,
            "endpoint": endpoint,
            "payload": payload,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "success": False,
            "created_count": 0,
            "error": str(e),
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--jobs",
        default="scripts/ai_generation_jobs.json",
        help="batch jobs json path",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="API base URL. jobs 파일의 base_url보다 우선합니다.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=2.0,
        help="각 요청 사이 대기 시간. OpenAI rate limit 방지용입니다.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="요청 timeout 초",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 호출하지 않고 실행 계획만 출력합니다.",
    )

    args = parser.parse_args()

    jobs_path = Path(args.jobs)
    data = load_jobs(jobs_path)

    base_url = args.base_url or data.get("base_url") or "http://localhost:8000"
    jobs = data.get("jobs", [])

    if not jobs:
        raise ValueError("실행할 jobs가 없습니다.")

    print(f"Base URL: {base_url}")
    print(f"Jobs: {len(jobs)}개")

    results = []

    for index, job in enumerate(jobs, start=1):
        name = job.get("name", f"job-{index}")
        job_type = job.get("type")
        payload = job.get("payload", {})
        count = payload.get("count")

        print(f"\n[{index}/{len(jobs)}] {name}")
        print(f"- type: {job_type}")
        print(f"- count: {count}")
        print(f"- topic: {payload.get('topic')}")

        if args.dry_run:
            results.append({
                "name": name,
                "type": job_type,
                "payload": payload,
                "success": None,
                "created_count": 0,
                "dry_run": True,
            })
            continue

        result = post_job(base_url=base_url, job=job, timeout=args.timeout)
        results.append(result)

        if result["success"]:
            print(f"성공: created_count={result.get('created_count')}")
        else:
            print("실패")
            if "error" in result:
                print(result["error"])
            else:
                print(result.get("response"))

        time.sleep(args.sleep)

    total_created = sum(item.get("created_count") or 0 for item in results)
    success_count = sum(1 for item in results if item.get("success") is True)
    fail_count = sum(1 for item in results if item.get("success") is False)

    summary = {
        "base_url": base_url,
        "job_count": len(jobs),
        "success_count": success_count,
        "fail_count": fail_count,
        "total_created": total_created,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "results": results,
    }

    output_dir = Path("exports")
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"ai_generation_batch_result_{timestamp}.json"

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n=== Batch 완료 ===")
    print(f"성공 jobs: {success_count}")
    print(f"실패 jobs: {fail_count}")
    print(f"생성된 문제 수: {total_created}")
    print(f"결과 파일: {output_path}")


if __name__ == "__main__":
    main()