import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { CheckCircle, XCircle, TrendingUp, Award, Loader2, Lock, ChevronDown, ChevronUp, } from "lucide-react";
import { examApi } from "../../../lib/api";
import type { ExamResultResponse, ResultStatItem, WrongAnswerItem, } from "../../../lib/types";
import AIReportCard from "../../components/result/AIReportCard";

export default function TestResult() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const recordId = searchParams.get("record_id");

  const [result, setResult] = useState<ExamResultResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [notVisible, setNotVisible] = useState(false);
  const [openWrongIds, setOpenWrongIds] = useState<number[]>([]);

  useEffect(() => {
    if (!recordId) { navigate("/test-login"); return; }
    examApi.getResult(Number(recordId))
      .then(setResult)
      .catch((err) => {
        console.error("결과 조회 실패:", err);
        console.error("status:", err.response?.status);
        console.error("data:", err.response?.data);

        if (err.response?.status === 403) {
          setNotVisible(true);
        } else {
          alert(
            `결과 조회 실패: ${err.response?.status || "unknown"}\n` +
            `${JSON.stringify(err.response?.data || err.message)}`
          );
        }
      })
      .finally(() => setLoading(false));
  }, [recordId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader2 className="size-8 animate-spin text-sky-500" />
      </div>
    );
  }

  if (notVisible) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-sky-50 flex items-center justify-center p-4">
        <Card className="w-full max-w-md shadow-lg text-center">
          <CardContent className="pt-10 pb-8 space-y-4">
            <div className="mx-auto size-16 rounded-full bg-slate-100 flex items-center justify-center">
              <Lock className="size-8 text-slate-500" />
            </div>
            <h2 className="text-xl font-semibold text-slate-800">결과 미공개</h2>
            <p className="text-slate-500 text-sm leading-relaxed">
              담당자가 결과를 아직 공개하지 않았습니다.<br />
              공개 후 다시 확인해 주세요.
            </p>
            <Button variant="outline" onClick={() => navigate("/test-submit")}>
              돌아가기
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!result) return null;

  const analysis = result.analysis_report;
  const summary = analysis?.summary;
  const wrongAnswers = analysis?.wrong_answers ?? [];
  const recommendations = analysis?.recommendations ?? [];
  const competencyStats = analysis?.competency_stats ?? [];
  const difficultyStats = analysis?.difficulty_stats ?? [];
  const weakCompetencies = analysis?.weak_competencies ?? [];

  const formatKST = (value?: string | null) => {
    if (!value) return "-";

    const hasTimezone =
      value.endsWith("Z") || /[+-]\d{2}:\d{2}$/.test(value);

    const utcValue = hasTimezone ? value : `${value}Z`;

    return new Date(utcValue).toLocaleString("ko-KR", {
      timeZone: "Asia/Seoul",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
  };

  const toggleWrongAnswer = (questionId: number) => {
    setOpenWrongIds((prev) =>
      prev.includes(questionId)
        ? prev.filter((id) => id !== questionId)
        : [...prev, questionId]
    );
  };

  const competencies = result.competency_breakdown || {};

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6">
      <div className="mx-auto max-w-4xl space-y-5">
        {/* Compact Score Card */}
        <Card
          className={`border shadow-sm ${result.pass_yn
            ? "border-emerald-200 bg-emerald-50/70"
            : "border-rose-200 bg-rose-50/70"
            }`}
        >
          <CardContent className="p-4">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div className="flex items-center gap-4">
                <div
                  className={`flex h-14 w-14 items-center justify-center rounded-full ${result.pass_yn ? "bg-emerald-100" : "bg-rose-100"
                    }`}
                >
                  {result.pass_yn ? (
                    <CheckCircle className="h-7 w-7 text-emerald-600" />
                  ) : (
                    <XCircle className="h-7 w-7 text-rose-600" />
                  )}
                </div>

                <div>
                  <p className="text-xs text-slate-500">
                    {result.applicant_name}님의 시험 결과
                  </p>
                  <h1 className="text-xl font-bold text-slate-900">
                    {result.diagnosis_title}
                  </h1>
                  <p className="mt-1 text-xs text-slate-500">
                    제출일시{" "}
                    {formatKST(result.submitted_at)}
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-between gap-5 md:justify-end">
                <div className="text-right">
                  <p className="text-3xl font-bold text-slate-900">
                    {result.total_score}
                    <span className="ml-1 text-base font-normal text-slate-500">
                      점
                    </span>
                  </p>
                  <p className="text-xs text-slate-500">
                    합격 기준 {result.pass_score}점
                  </p>
                </div>

                <Badge
                  className={
                    result.pass_yn
                      ? "bg-emerald-100 text-emerald-700"
                      : "bg-rose-100 text-rose-700"
                  }
                >
                  {result.pass_yn ? "합격" : "불합격"}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Competency Breakdown */}
        {!analysis && Object.keys(competencies).length > 0 && (
          <Card className="border-slate-200 shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <TrendingUp className="size-5 text-sky-600" />
                역량별 결과
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {Object.entries(competencies).map(([name, score], idx) => (
                  <div key={idx} className="space-y-1.5">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium text-slate-700">{name}</span>
                      <span className={`font-semibold ${score >= 70 ? "text-green-600" : score >= 50 ? "text-amber-600" : "text-red-500"}`}>
                        {score}%
                      </span>
                    </div>
                    <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${score >= 70 ? "bg-green-500" : score >= 50 ? "bg-amber-500" : "bg-red-500"}`}
                        style={{ width: `${score}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
        {analysis && summary && (
          <div className="space-y-6">
            {/* 결과 분석 요약 */}
            <Card className="border-slate-200 bg-white shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">결과 분석 요약</CardTitle>
              </CardHeader>
              <CardContent className="p-4 pt-0">
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  <div className="rounded-lg bg-slate-50 p-4">
                    <p className="text-sm text-slate-500">전체 문항</p>
                    <p className="mt-1 text-2xl font-bold text-slate-900">
                      {summary.total_questions}
                      <span className="ml-1 text-sm font-normal text-slate-500">문항</span>
                    </p>
                  </div>

                  <div className="rounded-lg bg-emerald-50 p-4">
                    <p className="text-sm text-emerald-600">정답</p>
                    <p className="mt-1 text-2xl font-bold text-emerald-700">
                      {summary.correct_count}
                      <span className="ml-1 text-sm font-normal text-emerald-600">문항</span>
                    </p>
                  </div>

                  <div className="rounded-lg bg-rose-50 p-4">
                    <p className="text-sm text-rose-600">오답</p>
                    <p className="mt-1 text-2xl font-bold text-rose-700">
                      {summary.wrong_count}
                      <span className="ml-1 text-sm font-normal text-rose-600">문항</span>
                    </p>
                  </div>

                  <div className="rounded-lg bg-blue-50 p-4">
                    <p className="text-sm text-blue-600">정답률</p>
                    <p className="mt-1 text-2xl font-bold text-blue-700">
                      {summary.accuracy_rate}
                      <span className="ml-1 text-sm font-normal text-blue-600">%</span>
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
            {result.summary_comment && (
              <AIReportCard report={result.summary_comment} />
            )}

            {/* 역량/난이도 분석 */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Card className="border-slate-200 shadow-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">
                    {competencyStats.length > 1 ? "역량별 정답률" : "역량 결과"}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {competencyStats.map((item: ResultStatItem) => (
                      <div key={item.key}>
                        <div className="mb-1 flex items-center justify-between text-sm">
                          <span className="font-medium text-slate-700">{item.label}</span>
                          <span className="text-slate-500">
                            {item.correct_count}/{item.total_count} · {item.accuracy_rate}%
                          </span>
                        </div>
                        <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
                          <div
                            className={`h-full rounded-full ${item.accuracy_rate >= 70
                              ? "bg-green-500"
                              : item.accuracy_rate >= 50
                                ? "bg-amber-500"
                                : "bg-red-500"
                              }`}
                            style={{ width: `${item.accuracy_rate}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card className="border-slate-200 shadow-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">난이도별 정답률</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {difficultyStats.map((item: ResultStatItem) => (
                      <div key={item.key}>
                        <div className="mb-1 flex items-center justify-between text-sm">
                          <span className="font-medium text-slate-700">{item.label}</span>
                          <span className="text-slate-500">
                            {item.correct_count}/{item.total_count} · {item.accuracy_rate}%
                          </span>
                        </div>
                        <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
                          <div
                            className={`h-full rounded-full ${item.accuracy_rate >= 70
                              ? "bg-green-500"
                              : item.accuracy_rate >= 50
                                ? "bg-amber-500"
                                : "bg-red-500"
                              }`}
                            style={{ width: `${item.accuracy_rate}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            {!result.summary_comment && recommendations.length > 0 && (
              <Card className="border-slate-200 bg-white shadow-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">추천 학습 방향</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {recommendations.map((text: string, index: number) => (
                      <li
                        key={index}
                        className="rounded-lg bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900"
                      >
                        {text}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

            {/* 오답 문제 목록 */}
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between gap-3">
                  <CardTitle className="text-lg">오답 문제 목록</CardTitle>
                  <span className="text-sm text-slate-500">
                    총 {wrongAnswers.length}문항
                  </span>
                </div>
              </CardHeader>

              <CardContent>
                {wrongAnswers.length > 0 ? (
                  <div className="overflow-hidden rounded-lg border border-slate-200">
                    <div className="hidden grid-cols-[72px_1fr_90px_90px_90px] gap-3 bg-slate-50 px-4 py-3 text-xs font-semibold text-slate-500 md:grid">
                      <div>역량</div>
                      <div>문제</div>
                      <div>난이도</div>
                      <div>내 답안</div>
                      <div>정답</div>
                    </div>

                    <div className="divide-y divide-slate-200">
                      {wrongAnswers.map((item: WrongAnswerItem) => {
                        const isOpen = openWrongIds.includes(item.question_id);

                        return (
                          <div key={item.question_id} className="bg-white">
                            <button
                              type="button"
                              onClick={() => toggleWrongAnswer(item.question_id)}
                              className="grid w-full grid-cols-1 gap-2 px-4 py-4 text-left hover:bg-slate-50 md:grid-cols-[72px_1fr_90px_90px_90px]"
                            >
                              <div>
                                <Badge variant="secondary" className="bg-sky-50 text-sky-700">
                                  {item.competency_label || item.competency_type || "-"}
                                </Badge>
                              </div>

                              <div className="min-w-0">
                                <p className="line-clamp-1 font-medium text-slate-900">
                                  {item.question_title}
                                </p>
                                <p className="mt-1 text-xs text-slate-500 md:hidden">
                                  난이도 {item.difficulty} · 내 답안 {String(item.submitted_answer ?? "-")} · 정답 {String(item.correct_answer ?? "-")}
                                </p>
                              </div>

                              <div className="hidden md:block">
                                <Badge variant="outline" className="bg-orange-50 text-orange-700">
                                  {item.difficulty || "-"}
                                </Badge>
                              </div>

                              <div className="hidden truncate text-sm text-slate-600 md:block">
                                {String(item.submitted_answer ?? "-")}
                              </div>

                              <div className="hidden items-center justify-between gap-2 text-sm text-slate-600 md:flex">
                                <span className="truncate">{String(item.correct_answer ?? "-")}</span>
                                {isOpen ? (
                                  <ChevronUp className="size-4 shrink-0 text-slate-400" />
                                ) : (
                                  <ChevronDown className="size-4 shrink-0 text-slate-400" />
                                )}
                              </div>
                            </button>
                            {isOpen && (
                              <div className="border-t border-slate-100 bg-slate-50 px-4 py-4">
                                {item.question_body && (
                                  <div className="mb-3 rounded-md bg-white p-3 text-sm leading-6 text-slate-700">
                                    <p className="mb-1 text-xs font-semibold text-slate-500">
                                      문제 본문
                                    </p>
                                    <div className="whitespace-pre-wrap">
                                      {item.question_body}
                                    </div>
                                  </div>
                                )}

                                {Array.isArray(item.choices_json) && item.choices_json.length > 0 && (
                                  <div className="mb-3 rounded-md bg-white p-3 text-sm leading-6 text-slate-700">
                                    <p className="mb-2 text-xs font-semibold text-slate-500">
                                      선택지
                                    </p>
                                    <ol className="list-decimal space-y-1 pl-5">
                                      {item.choices_json.map((choice, index) => (
                                        <li key={`${item.question_id}-choice-${index}`} className="whitespace-pre-wrap">
                                          {String(choice)}
                                        </li>
                                      ))}
                                    </ol>
                                  </div>
                                )}

                                <div className="grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
                                  <div className="rounded-md bg-white p-3">
                                    <p className="mb-1 text-xs font-semibold text-slate-500">
                                      내 답안
                                    </p>
                                    <p className="text-slate-700">
                                      {String(item.submitted_answer ?? "-")}
                                    </p>
                                  </div>

                                  <div className="rounded-md bg-white p-3">
                                    <p className="mb-1 text-xs font-semibold text-slate-500">
                                      정답
                                    </p>
                                    <p className="text-slate-700">
                                      {String(item.correct_answer ?? "-")}
                                    </p>
                                  </div>
                                </div>

                                {item.explanation && (
                                  <div className="mt-3 rounded-md bg-white p-3 text-sm leading-6 text-slate-700">
                                    <p className="mb-1 text-xs font-semibold text-slate-500">
                                      해설
                                    </p>
                                    <div className="whitespace-pre-wrap">
                                      {item.explanation}
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  <p className="rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                    오답 문제가 없습니다. 모든 문제를 맞혔습니다.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        <div className="flex flex-col gap-3">
          <Button variant="outline" className="w-full" onClick={() => navigate("/apply")}>
            메인으로 돌아가기
          </Button>
        </div>
      </div>
    </div>
  );
}
