import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Award, CheckCircle, ChevronDown, ChevronUp, Loader2, Sparkles, TrendingUp, XCircle } from "lucide-react";
import { directCbtApi } from "../../../lib/api";
import type { ExamResultResponse, ResultStatItem, WrongAnswerItem } from "../../../lib/types";
import AIReportCard from "../../components/result/AIReportCard";

export default function DirectAssessmentResult() {
  const navigate = useNavigate();
  const { recordId } = useParams();

  const parsedRecordId = Number(recordId);
  const applicantId = Number(localStorage.getItem("direct_applicant_id") || 0);

  const [result, setResult] = useState<ExamResultResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [openWrongIds, setOpenWrongIds] = useState<number[]>([]);
  const [error, setError] = useState("");

  const aiReportGenerated =
    localStorage.getItem("direct_ai_report_generated") === "true";
  const aiReportLimitExceeded =
    localStorage.getItem("direct_ai_report_limit_exceeded") === "true";

  useEffect(() => {
    if (!applicantId || !parsedRecordId) {
      navigate("/direct-assessment/login");
      return;
    }

    directCbtApi
      .getResult(parsedRecordId, applicantId)
      .then(setResult)
      .catch((err: any) => {
        setError(err.response?.data?.detail || "결과를 불러오지 못했습니다.");
      })
      .finally(() => setLoading(false));
  }, [applicantId, parsedRecordId, navigate]);

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

  const formatAnswerLabel = (value: unknown) => {
    if (value === null || value === undefined || value === "") return "-";

    const text = String(value);

    // 이미 "1번" 형태면 그대로 사용
    if (text.endsWith("번")) return text;

    // 숫자면 "1번" 형태로 표시
    if (/^\d+$/.test(text)) return `${text}번`;

    return text;
  };

  const normalizeChoices = (choices?: unknown): string[] => {
    if (!choices) return [];

    if (Array.isArray(choices)) {
      return choices.map((choice) => String(choice));
    }

    if (typeof choices === "string") {
      try {
        const parsed = JSON.parse(choices);
        if (Array.isArray(parsed)) {
          return parsed.map((choice) => String(choice));
        }
      } catch {
        return [];
      }
    }

    return [];
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader2 className="size-8 animate-spin text-sky-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-sky-50 flex items-center justify-center p-4">
        <Card className="w-full max-w-md shadow-lg text-center">
          <CardContent className="pt-10 pb-8 space-y-4">
            <XCircle className="size-12 text-red-500 mx-auto" />
            <h2 className="text-xl font-semibold text-slate-800">결과 조회 실패</h2>
            <p className="text-sm text-red-600">{error}</p>
            <Button onClick={() => navigate("/direct-assessment/exams")}>
              시험지 목록으로
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!result) return null;

  const analysis = result.analysis_report;
  const summary = analysis?.summary;
  const recommendations = analysis?.recommendations ?? [];
  const competencyStats = analysis?.competency_stats ?? [];
  const difficultyStats = analysis?.difficulty_stats ?? [];
  const weakCompetencies = analysis?.weak_competencies ?? [];
  const wrongAnswers = analysis?.wrong_answers ?? [];
  const competencies = result.competency_breakdown || {};

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6">
      <div className="mx-auto max-w-4xl space-y-5">
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
                    체험형 CBT 결과
                  </p>
                  <h1 className="text-xl font-bold text-slate-900">
                    {result.diagnosis_title}
                  </h1>
                  <p className="mt-1 text-xs text-slate-500">
                    제출일시 {formatKST(result.submitted_at)}
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

        {aiReportGenerated && (
          <Card className="border-sky-200 bg-sky-50 shadow-sm">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <Sparkles className="size-5 text-sky-600 mt-0.5" />
                <div>
                  <p className="font-medium text-sky-800">
                    AI 종합 진단이 생성되었습니다.
                  </p>
                  <p className="mt-1 text-sm text-sky-700">
                    체험형 진단은 이전 기록과 비교하지 않고 현재 결과 기준으로 분석됩니다.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {aiReportLimitExceeded && (
          <Card className="border-amber-200 bg-amber-50 shadow-sm">
            <CardContent className="p-4">
              <p className="font-medium text-amber-800">
                현재 AI 진단 리포트를 생성할 수 없습니다.
              </p>
              <p className="mt-1 text-sm text-amber-700">
                기본 채점 결과와 정량 분석은 확인할 수 있습니다.
              </p>
            </CardContent>
          </Card>
        )}

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
                {Object.entries(competencies as Record<string, number>).map(
                  ([name, score]: [string, number], idx: number) => (
                    <div key={idx} className="space-y-1.5">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium text-slate-700">{name}</span>
                        <span
                          className={`font-semibold ${score >= 70
                            ? "text-green-600"
                            : score >= 50
                              ? "text-amber-600"
                              : "text-red-500"
                            }`}
                        >
                          {score}%
                        </span>
                      </div>
                      <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${score >= 70
                            ? "bg-green-500"
                            : score >= 50
                              ? "bg-amber-500"
                              : "bg-red-500"
                            }`}
                          style={{ width: `${score}%` }}
                        />
                      </div>
                    </div>
                  )
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {analysis && summary && (
          <div className="space-y-6">
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

            {weakCompetencies.length > 0 && (
              <Card className="border-amber-200 bg-amber-50 shadow-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2 text-amber-900">
                    <Award className="size-5" />
                    우선 보완 영역
                  </CardTitle>
                </CardHeader>

                <CardContent>
                  <div className="grid gap-2 md:grid-cols-3">
                    {weakCompetencies.slice(0, 3).map((item: ResultStatItem) => (
                      <div key={item.key} className="rounded-lg bg-white/70 p-3">
                        <p className="font-medium text-amber-900">{item.label}</p>
                        <p className="mt-1 text-sm text-amber-700">
                          정답률 {item.accuracy_rate}%
                        </p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

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
                  <div className="space-y-3">
                    {wrongAnswers.map((item: WrongAnswerItem) => {
                      const opened = openWrongIds.includes(item.question_id);
                      const choices = normalizeChoices(item.choices_json);

                      return (
                        <div
                          key={item.question_id}
                          className="overflow-hidden rounded-lg border border-slate-200 bg-white"
                        >
                          <button
                            className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-slate-50"
                            onClick={() => toggleWrongAnswer(item.question_id)}
                          >
                            <div className="min-w-0">
                              <p className="text-sm font-medium text-slate-800 line-clamp-1">
                                {item.question_title}
                              </p>
                              <p className="mt-1 text-xs text-slate-500">
                                {item.competency_label || item.competency_type || "-"} ·{" "}
                                {item.difficulty || "-"}
                              </p>
                            </div>

                            {opened ? (
                              <ChevronUp className="size-4 text-slate-400" />
                            ) : (
                              <ChevronDown className="size-4 text-slate-400" />
                            )}
                          </button>

                          {opened && (
                            <div className="border-t border-slate-100 bg-slate-50 px-4 py-4 text-sm text-slate-700 space-y-3">
                              {item.question_body && (
                                <div className="rounded-lg bg-white p-3">
                                  <p className="mb-2 text-xs font-semibold text-slate-500">
                                    문제 본문
                                  </p>
                                  <div className="whitespace-pre-wrap leading-6">
                                    {item.question_body}
                                  </div>
                                </div>
                              )}

                              {choices.length > 0 && (
                                <div className="rounded-lg bg-white p-3">
                                  <p className="mb-2 text-xs font-semibold text-slate-500">
                                    선택지
                                  </p>
                                  <ol className="list-decimal space-y-1 pl-5 leading-6">
                                    {choices.map((choice, index) => (
                                      <li
                                        key={`${item.question_id}-choice-${index}`}
                                        className="whitespace-pre-wrap"
                                      >
                                        {choice}
                                      </li>
                                    ))}
                                  </ol>
                                </div>
                              )}

                              <div className="grid gap-2 md:grid-cols-2">
                                <div className="rounded-lg bg-rose-50 p-3">
                                  <p className="text-xs font-medium text-rose-600">내 답안</p>
                                  <p className="mt-1 font-semibold text-rose-900">
                                    {formatAnswerLabel(item.submitted_answer)}
                                  </p>
                                </div>

                                <div className="rounded-lg bg-emerald-50 p-3">
                                  <p className="text-xs font-medium text-emerald-600">정답</p>
                                  <p className="mt-1 font-semibold text-emerald-900">
                                    {formatAnswerLabel(item.correct_answer)}
                                  </p>
                                </div>
                              </div>

                              {item.explanation && (
                                <div className="rounded-lg bg-blue-50 p-3 text-blue-900">
                                  <p className="text-xs font-medium text-blue-600 mb-1">해설</p>
                                  <div className="whitespace-pre-wrap leading-6">
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
                ) : (
                  <div className="rounded-lg bg-emerald-50 p-5 text-center text-sm text-emerald-700">
                    오답 문제가 없습니다.
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        <div className="flex flex-col gap-3 sm:flex-row sm:justify-center pt-2">
          <Button
            className="bg-sky-600 hover:bg-sky-700"
            onClick={() => navigate("/direct-assessment/exams")}
          >
            다른 시험지 응시하기
          </Button>

          <Button
            variant="outline"
            onClick={() => navigate("/direct-assessment/login")}
          >
            처음 화면으로
          </Button>
        </div>
      </div>
    </div>
  );
}