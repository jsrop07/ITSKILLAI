import { useEffect, useMemo, useState } from "react";
import {
  FileCheck,
  CheckCircle2,
  XCircle,
  Loader2,
  Sparkles,
  Database,
} from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Textarea } from "../components/ui/textarea";

import { questionsApi } from "../../lib/api";
import type { Question } from "../../lib/types";
import { getCompetencyLabel, AI_GENERATION_TYPE_LABELS } from "../../lib/types";

const formatDate = (dateStr?: string) => {
  if (!dateStr) return "-";
  try {
    const d = new Date(dateStr);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  } catch {
    return "-";
  }
};

const getGenerationBadgeClass = (type?: string | null) => {
  switch (type) {
    case "rag":
      return "bg-indigo-100 text-indigo-700 border-indigo-200";
    case "general_graph":
      return "bg-cyan-100 text-cyan-700 border-cyan-200";
    case "manual":
      return "bg-slate-100 text-slate-700 border-slate-200";
    default:
      return "bg-amber-100 text-amber-700 border-amber-200";
  }
};

const getGenerationLabel = (q: Question) => {
  if (q.ai_generation_type && AI_GENERATION_TYPE_LABELS[q.ai_generation_type]) {
    return AI_GENERATION_TYPE_LABELS[q.ai_generation_type];
  }
  if (q.source_type === "ai") return "AI 생성";
  return AI_GENERATION_TYPE_LABELS.manual;
};

const QUESTION_TYPE_LABELS: Record<string, string> = {
  multiple_choice: "객관식",
  essay: "서술형",
  coding: "코드작성형",
};

const typeColor: Record<string, string> = {
  multiple_choice: "bg-blue-100 text-blue-700 border-blue-200",
  essay: "bg-emerald-100 text-emerald-700 border-emerald-200",
  coding: "bg-orange-100 text-orange-700 border-orange-200",
};

const difficultyColor: Record<string, string> = {
  초급: "bg-green-100 text-green-700 border-green-200",
  중급: "bg-amber-100 text-amber-700 border-amber-200",
  고급: "bg-red-100 text-red-700 border-red-200",
};

function parseChoices(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map((item) => String(item));
  }

  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      if (Array.isArray(parsed)) {
        return parsed.map((item) => String(item));
      }
    } catch {
      return [];
    }
  }

  return [];
}

function parseAnswer(value: unknown): number | string {
  if (typeof value === "number") return value;

  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      if (typeof parsed === "number") return parsed;
      if (typeof parsed === "string") return parsed;
    } catch {
      const numberValue = Number(value);
      if (!Number.isNaN(numberValue)) return numberValue;
      return value;
    }
  }

  return "";
}

export default function AIQuestionReview() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [reviewNote, setReviewNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const loadQuestions = async () => {
    setLoading(true);

    try {
      const data = await questionsApi.list({
        source_type: "ai",
        review_status: "pending",
      });

      const list = Array.isArray(data) ? data : [];
      setQuestions(list);

      if (list.length > 0) {
        setSelectedId((prev) => prev ?? list[0].question_id);
      } else {
        setSelectedId(null);
      }
    } catch (error) {
      console.error("AI 검토 목록 조회 실패:", error);
      alert("AI 검토 목록을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQuestions();
  }, []);

  const selectedQuestion = useMemo(() => {
    return questions.find((q) => q.question_id === selectedId) ?? null;
  }, [questions, selectedId]);

  const ragEvidence = selectedQuestion?.rag_evidence;
  const ragDocuments = ragEvidence?.documents ?? [];
  const shouldShowRagEvidence =
    selectedQuestion?.ai_generation_type === "ai_question_v2_rag" &&
    !!ragEvidence &&
    ragDocuments.length > 0;

  const choices = useMemo(() => {
    return parseChoices(selectedQuestion?.choices_json);
  }, [selectedQuestion]);

  const answer = useMemo(() => {
    return parseAnswer(selectedQuestion?.answer_json);
  }, [selectedQuestion]);

  const handleApprove = async () => {
    if (!selectedQuestion) return;

    setSaving(true);

    try {
      await questionsApi.update(selectedQuestion.question_id, {
        review_status: "approved",
      } as any);

      setReviewNote("");
      await loadQuestions();
    } catch (error) {
      console.error("문제 승인 실패:", error);
      alert("문제 승인에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  };

  const handleReject = async () => {
    if (!selectedQuestion) return;

    setSaving(true);

    try {
      await questionsApi.update(selectedQuestion.question_id, {
        review_status: "rejected",
      } as any);

      alert("문제가 반려되었습니다.");
      setReviewNote("");
      await loadQuestions();
    } catch (error) {
      console.error("문제 반려 실패:", error);
      alert("문제 반려에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-800 flex items-center gap-2">
          <FileCheck className="size-7 text-amber-600" />
          AI 문제 검토
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          AI 생성 문제의 품질을 확인하고 승인 또는 반려 처리합니다.
        </p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <Card className="col-span-1 border-slate-200">
          <CardHeader className="border-b border-slate-200">
            <CardTitle className="text-lg">검토 대기 목록</CardTitle>
            <CardDescription>{questions.length}개 문제 대기 중</CardDescription>
          </CardHeader>

          <CardContent className="p-0">
            {loading ? (
              <div className="flex justify-center py-16">
                <Loader2 className="size-6 animate-spin text-sky-500" />
              </div>
            ) : questions.length === 0 ? (
              <div className="py-16 text-center text-sm text-slate-400">
                검토 대기 중인 AI 문제가 없습니다.
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {questions.map((q) => (
                  <div
                    key={q.question_id}
                    className={`p-4 cursor-pointer transition-colors ${selectedId === q.question_id
                      ? "bg-sky-50 border-l-4 border-l-sky-500"
                      : "hover:bg-slate-50"
                      }`}
                    onClick={() => setSelectedId(q.question_id)}
                  >
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <Badge variant="secondary" className="bg-sky-100 text-sky-700 text-[10px] h-5">
                        {getCompetencyLabel(q.competency_type) || "미분류"}
                      </Badge>
                      <Badge
                        variant="secondary"
                        className={`${difficultyColor[q.difficulty ?? ""] || "bg-slate-100 text-slate-700"} text-[10px] h-5`}
                      >
                        {q.difficulty}
                      </Badge>
                    </div>

                    <p className="text-sm font-medium text-slate-800 mb-2 line-clamp-2">
                      {q.title || q.body}
                    </p>

                    <div className="flex items-center justify-between mt-auto">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className={`${getGenerationBadgeClass(q.ai_generation_type)} text-[10px] h-5 border`}>
                          <Sparkles className="size-3 mr-1" />
                          {getGenerationLabel(q)}
                        </Badge>
                        <Badge variant="outline" className={`${typeColor[q.question_type] || "bg-slate-100"} text-[10px] h-5`}>
                          {QUESTION_TYPE_LABELS[q.question_type] || q.question_type}
                        </Badge>
                      </div>
                      <span className="text-xs font-bold text-slate-600">
                        {q.score}점
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="col-span-2 space-y-6">
          {!selectedQuestion ? (
            <Card className="border-slate-200">
              <CardContent className="py-20 text-center text-slate-400">
                검토할 문제를 선택하세요.
              </CardContent>
            </Card>
          ) : (
            <>
              <Card className="border-slate-200">
                <CardHeader className="border-b border-slate-200">
                  <div className="w-full">
                    <div className="flex items-center justify-between gap-4">
                      <CardTitle className="text-lg flex-1 min-w-0">
                        {selectedQuestion.title}
                      </CardTitle>

                      <div className="flex items-center gap-2 shrink-0">
                        <Button
                          className="bg-green-600 hover:bg-green-700"
                          onClick={handleApprove}
                          disabled={saving}
                        >
                          {saving ? (
                            <Loader2 className="size-4 mr-2 animate-spin" />
                          ) : (
                            <CheckCircle2 className="size-4 mr-2" />
                          )}
                          승인
                        </Button>

                        <Button
                          variant="outline"
                          className="text-red-600 border-red-200 hover:bg-red-50"
                          onClick={handleReject}
                          disabled={saving}
                        >
                          <XCircle className="size-4 mr-2" />
                          반려
                        </Button>
                      </div>
                    </div>

                    <div className="flex items-center justify-between mt-2 flex-wrap gap-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge
                          variant="secondary"
                          className={
                            typeColor[selectedQuestion.question_type ?? ""] ||
                            "bg-slate-100 text-slate-700"
                          }
                        >
                          {QUESTION_TYPE_LABELS[selectedQuestion.question_type ?? ""] ||
                            selectedQuestion.question_type}
                        </Badge>

                        <Badge
                          variant="secondary"
                          className={
                            difficultyColor[selectedQuestion.difficulty ?? ""] ||
                            "bg-slate-100 text-slate-700"
                          }
                        >
                          {selectedQuestion.difficulty}
                        </Badge>

                        <Badge variant="secondary" className="bg-sky-100 text-sky-700">
                          {getCompetencyLabel(selectedQuestion.competency_type) || "미분류"}
                        </Badge>

                        <Badge variant="secondary" className="bg-slate-100 text-slate-700">
                          {selectedQuestion.score}점
                        </Badge>

                        <Badge
                          variant="outline"
                          className={`${getGenerationBadgeClass(
                            selectedQuestion.ai_generation_type
                          )} font-medium border`}
                        >
                          {getGenerationLabel(selectedQuestion)}
                        </Badge>
                      </div>

                      <span className="text-sm text-slate-600 font-medium shrink-0">
                        {formatDate(selectedQuestion.created_at)}
                      </span>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="pt-6 space-y-5">
                  <div>
                    <p className="text-sm font-medium text-slate-700 mb-2">문제 본문</p>
                    <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 text-sm text-slate-800 whitespace-pre-wrap">
                      {selectedQuestion.body}
                    </div>
                  </div>

                  {selectedQuestion.question_type === "multiple_choice" && (
                    <div>
                      <p className="text-sm font-medium text-slate-700 mb-3">선택지</p>

                      <div className="space-y-2">
                        {choices.map((choice, idx) => {
                          const isCorrect = idx + 1 === Number(answer);

                          return (
                            <div
                              key={idx}
                              className={`p-3 rounded-lg border text-sm ${isCorrect
                                ? "bg-green-50 border-green-200"
                                : "bg-slate-50 border-slate-200"
                                }`}
                            >
                              <div className="flex items-start gap-3">
                                <span className="font-medium text-slate-600">
                                  {idx + 1}
                                </span>

                                <span className="flex-1 text-slate-700">
                                  {choice}
                                </span>

                                {isCorrect && (
                                  <Badge
                                    variant="secondary"
                                    className="bg-green-100 text-green-700"
                                  >
                                    정답
                                  </Badge>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {selectedQuestion.question_type !== "multiple_choice" && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                      <p className="text-sm font-medium text-green-900 mb-2">
                        모범답안
                      </p>
                      <p className="text-sm text-green-800 leading-relaxed whitespace-pre-wrap">
                        {String(answer || "-")}
                      </p>
                    </div>
                  )}

                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <p className="text-sm font-medium text-blue-900 mb-2">해설</p>
                    <p className="text-sm text-blue-800 leading-relaxed whitespace-pre-wrap">
                      {selectedQuestion.explanation || "-"}
                    </p>
                  </div>

                  {shouldShowRagEvidence && (
                    <div className="border border-indigo-200 bg-indigo-50/40 rounded-lg p-4 space-y-4">
                      <div className="flex items-center gap-2">
                        <Database className="size-4 text-indigo-700" />
                        <p className="text-sm font-semibold text-indigo-900">
                          RAG 생성 근거
                        </p>
                      </div>

                      <div className="grid grid-cols-2 gap-3 text-sm">
                        <div>
                          <p className="text-xs text-slate-500 mb-1">검색어</p>
                          <p className="font-medium text-slate-800">
                            {ragEvidence?.search_query || "-"}
                          </p>
                        </div>

                        <div>
                          <p className="text-xs text-slate-500 mb-1">검색 방식</p>
                          <p className="font-medium text-slate-800">
                            {ragEvidence?.search_mode || "-"}
                          </p>
                        </div>

                        <div>
                          <p className="text-xs text-slate-500 mb-1">top_k</p>
                          <p className="font-medium text-slate-800">
                            {ragEvidence?.top_k ?? "-"}
                          </p>
                        </div>

                        <div>
                          <p className="text-xs text-slate-500 mb-1">category</p>
                          <p className="font-medium text-slate-800">
                            {ragEvidence?.category || "-"}
                          </p>
                        </div>
                      </div>

                      <div className="space-y-3">
                        {ragDocuments.map((doc, index) => (
                          <div
                            key={`${doc.file_name}-${doc.chunk_index}-${index}`}
                            className="rounded-lg border border-indigo-100 bg-white p-4"
                          >
                            <div className="flex items-start justify-between gap-3 mb-2">
                              <div>
                                <p className="text-sm font-semibold text-slate-800">
                                  {doc.title || "문서명 없음"}
                                </p>
                                <p className="text-xs text-slate-500">
                                  {doc.file_name || "-"} · chunk {doc.chunk_index ?? "-"}
                                </p>
                              </div>

                              <Badge
                                variant="secondary"
                                className="bg-indigo-100 text-indigo-700"
                              >
                                {doc.search_source || "unknown"}
                              </Badge>
                            </div>

                            <div className="grid grid-cols-3 gap-2 text-xs text-slate-600 mb-3">
                              <div>vector: {doc.vector_score ?? "-"}</div>
                              <div>keyword: {doc.keyword_score ?? "-"}</div>
                              <div>hybrid: {doc.hybrid_score ?? "-"}</div>
                            </div>

                            <div className="rounded-md bg-slate-50 border border-slate-100 p-3 text-xs text-slate-700 whitespace-pre-wrap">
                              {doc.content_preview || "-"}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}