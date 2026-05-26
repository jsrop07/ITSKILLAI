from __future__ import annotations

import os

from openai import OpenAI

from ai.reports.prompts import REPORT_SYSTEM_PROMPT, build_report_user_prompt


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def render_result_report(
    current_evidence: dict,
    history_comparison: dict,
) -> str:
    user_prompt = build_report_user_prompt(
        current_evidence=current_evidence,
        history_comparison=history_comparison,
    )

    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": REPORT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    content = response.choices[0].message.content
    return content.strip() if content else ""