import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Progress } from "../../components/ui/progress";
import { AlertTriangle, ChevronLeft, ChevronRight, Clock, Loader2, Send } from "lucide-react";
import { directCbtApi, examApi } from "../../../lib/api";
import type { AnswerSubmit, QuestionForExam } from "../../../lib/types";

export default function DirectAssessmentTake() {
    const navigate = useNavigate();
    const { recordId } = useParams();

    const parsedRecordId = Number(recordId);
    const applicantId = Number(localStorage.getItem("direct_applicant_id") || 0);
    const applicantName = localStorage.getItem("direct_applicant_name") || "";
    const examToken = localStorage.getItem("direct_exam_token") || "";

    const [questions, setQuestions] = useState<QuestionForExam[]>([]);
    const [answers, setAnswers] = useState<Record<number, AnswerSubmit>>({});
    const [currentIdx, setCurrentIdx] = useState(0);
    const [timeLeft, setTimeLeft] = useState(0);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);
    const [error, setError] = useState("");

    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const answersRef = useRef<Record<number, AnswerSubmit>>({});
    const endTimeRef = useRef<number | null>(null);

    useEffect(() => {
        if (!applicantId || !examToken || !parsedRecordId) {
            navigate("/direct-assessment/login");
            return;
        }

        const load = async () => {
            try {
                setLoading(true);
                setError("");

                const status = await examApi.getStatus(parsedRecordId, examToken);

                if (status.status === "graded" || status.remaining_seconds <= 0) {
                    navigate(`/direct-assessment/result/${parsedRecordId}`);
                    return;
                }

                const qs = await examApi.getQuestions(parsedRecordId, examToken);
                setQuestions(qs);
                setTimeLeft(status.remaining_seconds);
                endTimeRef.current = Date.now() + status.remaining_seconds * 1000;

                const restoredAnswers: Record<number, AnswerSubmit> = {};

                qs.forEach((q: QuestionForExam) => {
                    if (q.saved_answer_json !== null && q.saved_answer_json !== undefined) {
                        restoredAnswers[q.question_id] = {
                            question_id: q.question_id,
                            answer_json: q.saved_answer_json,
                        };
                    } else if (q.saved_answer_text) {
                        restoredAnswers[q.question_id] = {
                            question_id: q.question_id,
                            answer_text: q.saved_answer_text,
                        };
                    }
                });

                const saved = localStorage.getItem(`direct_answers_${parsedRecordId}`);

                if (Object.keys(restoredAnswers).length > 0) {
                    setAnswers(restoredAnswers);
                    answersRef.current = restoredAnswers;
                } else if (saved) {
                    const parsed = JSON.parse(saved);
                    setAnswers(parsed);
                    answersRef.current = parsed;
                }
            } catch (err: any) {
                setError(err.response?.data?.detail || "문제를 불러오지 못했습니다.");
            } finally {
                setLoading(false);
            }
        };

        load();
    }, [applicantId, examToken, parsedRecordId, navigate]);

    useEffect(() => {
        if (!parsedRecordId) return;
        localStorage.setItem(`direct_answers_${parsedRecordId}`, JSON.stringify(answers));
        answersRef.current = answers;
    }, [answers, parsedRecordId]);

    useEffect(() => {
        if (loading || !endTimeRef.current) return;

        timerRef.current = setInterval(() => {
            const remain = Math.max(0, Math.floor((endTimeRef.current! - Date.now()) / 1000));
            setTimeLeft(remain);

            if (remain <= 0) {
                if (timerRef.current) clearInterval(timerRef.current);
                handleSubmit(true);
            }
        }, 1000);

        return () => {
            if (timerRef.current) clearInterval(timerRef.current);
        };
    }, [loading]);

    const formatTime = (secs: number) => {
        const m = Math.floor(secs / 60).toString().padStart(2, "0");
        const s = (secs % 60).toString().padStart(2, "0");
        return `${m}:${s}`;
    };

    const setAnswer = (questionId: number, value: any, isJson: boolean) => {
        const nextAnswers = {
            ...answersRef.current,
            [questionId]: {
                question_id: questionId,
                ...(isJson ? { answer_json: value } : { answer_text: String(value) }),
            },
        };

        answersRef.current = nextAnswers;
        setAnswers(nextAnswers);
        localStorage.setItem(`direct_answers_${parsedRecordId}`, JSON.stringify(nextAnswers));

        examApi
            .saveProgress(parsedRecordId, Object.values(nextAnswers), examToken)
            .catch((err) => {
                console.error("직접 CBT 답안 임시저장 실패:", err);
            });
    };

    const handleSubmit = async (auto = false) => {
        if (!auto && !showConfirm) {
            setShowConfirm(true);
            return;
        }

        if (submitting) return;

        setSubmitting(true);

        if (timerRef.current) {
            clearInterval(timerRef.current);
        }

        try {
            const answerList = Object.values(answersRef.current);

            const result = await directCbtApi.submit(
                parsedRecordId,
                answerList,
                applicantId
            );

            localStorage.removeItem(`direct_answers_${parsedRecordId}`);
            localStorage.setItem("direct_ai_report_generated", String(result.ai_report_generated));
            localStorage.setItem("direct_ai_report_limit_exceeded", String(result.ai_report_limit_exceeded));
            localStorage.setItem("direct_ai_report_remaining_today", String(result.ai_report_remaining_today));

            navigate(`/direct-assessment/result/${parsedRecordId}`);
        } catch (err: any) {
            alert(err.response?.data?.detail || "제출 중 오류가 발생했습니다.");
            setSubmitting(false);
            setShowConfirm(false);
        }
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
            <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
                <Card className="w-full max-w-md">
                    <CardContent className="pt-6 text-center space-y-4">
                        <AlertTriangle className="size-10 text-red-500 mx-auto" />
                        <p className="text-sm text-red-600">{error}</p>
                        <Button onClick={() => navigate("/direct-assessment/exams")}>
                            시험지 목록으로
                        </Button>
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (questions.length === 0) {
        return (
            <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
                <Card className="w-full max-w-md">
                    <CardContent className="pt-6 text-center space-y-4">
                        <p className="text-slate-600">표시할 문제가 없습니다.</p>
                        <Button onClick={() => navigate("/direct-assessment/exams")}>
                            시험지 목록으로
                        </Button>
                    </CardContent>
                </Card>
            </div>
        );
    }

    const current = questions[currentIdx];
    const answeredCount = Object.keys(answers).length;
    const progress = Math.round((answeredCount / questions.length) * 100);
    const isUrgent = timeLeft < 300;

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col">
            <div className={`${isUrgent ? "bg-red-600" : "bg-slate-900"} text-white px-6 py-4 shadow-md sticky top-0 z-40`}>
                <div className="max-w-6xl mx-auto flex items-center justify-between">
                    <div>
                        <p className="text-sm opacity-70">직접 CBT 진단</p>
                        <h1 className="font-semibold">문제 풀이</h1>
                        <p className="text-xs opacity-60">{applicantName || "응시자"}님</p>
                    </div>

                    <div className="flex items-center gap-3">
                        <div className={`flex items-center gap-2 font-mono text-xl font-bold ${isUrgent ? "animate-pulse" : ""}`}>
                            <Clock className="size-5" />
                            {formatTime(timeLeft)}
                        </div>

                        <Button
                            size="sm"
                            className={isUrgent ? "bg-white text-red-600 hover:bg-red-50" : "bg-sky-600 hover:bg-sky-500"}
                            onClick={() => handleSubmit(false)}
                            disabled={submitting}
                        >
                            <Send className="size-4 mr-1" />
                            제출
                        </Button>
                    </div>
                </div>
            </div>

            <div className="flex flex-1 max-w-6xl mx-auto w-full gap-6 p-6">
                <div className="flex-1 space-y-4">
                    <div className="flex items-center justify-between">
                        <Badge variant="secondary" className="bg-sky-100 text-sky-700 text-sm px-3 py-1">
                            {currentIdx + 1} / {questions.length}
                        </Badge>

                        <div className="flex items-center gap-2 text-sm text-slate-500">
                            <span>답변 완료: {answeredCount}/{questions.length}</span>
                            <Progress value={progress} className="w-24 h-2" />
                        </div>
                    </div>

                    <Card className="border-slate-200 shadow-sm">
                        <CardHeader className="pb-4">
                            <div className="flex items-start gap-3">
                                <span className="flex-shrink-0 size-8 flex items-center justify-center rounded-full bg-sky-600 text-white text-sm font-bold">
                                    {currentIdx + 1}
                                </span>

                                <CardTitle className="text-base font-medium text-slate-800 leading-relaxed">
                                    {current.title}
                                </CardTitle>
                            </div>

                            {current.body && (
                                <div className="mt-3 ml-11 p-3 bg-slate-50 rounded-lg text-sm text-slate-600 whitespace-pre-wrap">
                                    {current.body}
                                </div>
                            )}
                        </CardHeader>

                        <CardContent className="ml-11">
                            {current.question_type === "multiple_choice" && current.choices_json && (
                                <div className="space-y-2">
                                    {current.choices_json.map((choice: any, i: number) => {
                                        const isSelected = answers[current.question_id]?.answer_json === i + 1;

                                        return (
                                            <button
                                                key={i}
                                                onClick={() => setAnswer(current.question_id, i + 1, true)}
                                                className={`w-full text-left px-4 py-3 rounded-lg border text-sm transition-all ${isSelected
                                                        ? "border-sky-500 bg-sky-50 text-sky-700 font-medium"
                                                        : "border-slate-200 bg-white text-slate-700 hover:border-sky-300 hover:bg-sky-50"
                                                    }`}
                                            >
                                                <span className={`inline-flex items-center justify-center size-6 rounded-full mr-3 text-xs font-bold ${isSelected ? "bg-sky-600 text-white" : "bg-slate-100 text-slate-600"
                                                    }`}>
                                                    {i + 1}
                                                </span>
                                                {String(choice)}
                                            </button>
                                        );
                                    })}
                                </div>
                            )}

                            {current.question_type === "essay" && (
                                <textarea
                                    className="w-full border border-slate-200 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 resize-none"
                                    placeholder="서술형 답변을 입력해 주세요..."
                                    rows={6}
                                    value={answers[current.question_id]?.answer_text || ""}
                                    onChange={(e) => setAnswer(current.question_id, e.target.value, false)}
                                />
                            )}
                        </CardContent>
                    </Card>

                    <div className="flex items-center justify-between">
                        <Button
                            variant="outline"
                            onClick={() => setCurrentIdx((i) => Math.max(0, i - 1))}
                            disabled={currentIdx === 0}
                        >
                            <ChevronLeft className="size-4 mr-1" />
                            이전
                        </Button>

                        {currentIdx < questions.length - 1 ? (
                            <Button
                                className="bg-sky-600 hover:bg-sky-700"
                                onClick={() => setCurrentIdx((i) => Math.min(questions.length - 1, i + 1))}
                            >
                                다음
                                <ChevronRight className="size-4 ml-1" />
                            </Button>
                        ) : (
                            <Button
                                className="bg-green-600 hover:bg-green-700"
                                onClick={() => handleSubmit(false)}
                                disabled={submitting}
                            >
                                <Send className="size-4 mr-2" />
                                최종 제출
                            </Button>
                        )}
                    </div>
                </div>

                <div className="w-48 flex-shrink-0 hidden md:block">
                    <Card className="border-slate-200 sticky top-24">
                        <CardHeader className="pb-3 pt-4">
                            <CardTitle className="text-sm text-slate-700">문제 목록</CardTitle>
                        </CardHeader>

                        <CardContent>
                            <div className="grid grid-cols-4 gap-1.5">
                                {questions.map((q: QuestionForExam, i: number) => {
                                    const answered = !!answers[q.question_id];
                                    const isCurrent = i === currentIdx;

                                    return (
                                        <button
                                            key={q.question_id}
                                            onClick={() => setCurrentIdx(i)}
                                            className={`size-9 rounded text-xs font-medium transition-all ${isCurrent
                                                    ? "bg-sky-600 text-white ring-2 ring-sky-300"
                                                    : answered
                                                        ? "bg-green-100 text-green-700"
                                                        : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                                                }`}
                                        >
                                            {i + 1}
                                        </button>
                                    );
                                })}
                            </div>

                            <div className="mt-4 space-y-1.5 text-xs text-slate-500">
                                <div className="flex items-center gap-2">
                                    <div className="size-3 rounded bg-green-100 border border-green-300" />
                                    <span>답변 완료</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="size-3 rounded bg-slate-100 border border-slate-300" />
                                    <span>미답변</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="size-3 rounded bg-sky-600" />
                                    <span>현재 문제</span>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>

            {showConfirm && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <Card className="w-full max-w-sm shadow-2xl">
                        <CardContent className="pt-6 space-y-4">
                            <div className="text-center space-y-2">
                                <AlertTriangle className="size-10 text-amber-500 mx-auto" />
                                <h3 className="text-lg font-semibold text-slate-800">
                                    시험을 제출하시겠습니까?
                                </h3>
                                <p className="text-sm text-slate-500">
                                    답변 완료: <strong>{answeredCount}</strong> / {questions.length}문제
                                </p>

                                {answeredCount < questions.length && (
                                    <p className="text-sm text-amber-600 bg-amber-50 rounded-lg p-2">
                                        미답변 문제가 {questions.length - answeredCount}개 있습니다.
                                    </p>
                                )}
                            </div>

                            <div className="flex gap-3">
                                <Button
                                    variant="outline"
                                    className="flex-1"
                                    onClick={() => setShowConfirm(false)}
                                    disabled={submitting}
                                >
                                    계속 풀기
                                </Button>

                                <Button
                                    className="flex-1 bg-sky-600 hover:bg-sky-700"
                                    onClick={() => handleSubmit(false)}
                                    disabled={submitting}
                                >
                                    {submitting ? <Loader2 className="size-4 animate-spin mr-2" /> : null}
                                    제출하기
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            )}
        </div>
    );
}