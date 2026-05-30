import { useEffect, useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Progress } from "../../components/ui/progress";
import { Clock, ChevronLeft, ChevronRight, Send, Loader2, AlertTriangle } from "lucide-react";
import { examApi } from "../../../lib/api";
import type { QuestionForExam, AnswerSubmit, ExamLoginResponse } from "../../../lib/types";

export default function TestRoom() {
  const navigate = useNavigate();
  const [session, setSession] = useState<ExamLoginResponse | null>(null);
  const [questions, setQuestions] = useState<QuestionForExam[]>([]);
  const [answers, setAnswers] = useState<Record<number, AnswerSubmit>>({});
  const [currentIdx, setCurrentIdx] = useState(0);
  const [timeLeft, setTimeLeft] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const answersRef = useRef<Record<number, AnswerSubmit>>({});
  const submittingRef = useRef(false);
  const endTimeRef = useRef<number | null>(null);
  const lastViolationAtRef = useRef(0);
  const [violationCount, setViolationCount] = useState(0);
  const [showViolationWarning, setShowViolationWarning] = useState(false);
  // Load session & questions
  useEffect(() => {
    const raw = sessionStorage.getItem("exam_session");
    if (!raw) { navigate("/test-login"); return; }
    const s: ExamLoginResponse = JSON.parse(raw);
    setSession(s);
    setViolationCount(s.violation_count ?? 0);

    examApi.getQuestions(s.record_id, s.exam_token)
      .then(async (qs) => {
        const status = await examApi.getStatus(s.record_id, s.exam_token);

        if (status.status === "graded" || status.remaining_seconds <= 0) {
          sessionStorage.setItem("submitted_record_id", String(s.record_id));
          navigate("/test-submit");
          return;
        }

        setQuestions(qs);
        setViolationCount(status.violation_count ?? 0);

        endTimeRef.current = Date.now() + status.remaining_seconds * 1000;
        setTimeLeft(status.remaining_seconds);

        const restoredAnswers: Record<number, AnswerSubmit> = {};

        qs.forEach((q) => {
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

        const saved = localStorage.getItem(`exam_answers_${s.record_id}`);
        if (Object.keys(restoredAnswers).length > 0) {
          setAnswers(restoredAnswers);
          answersRef.current = restoredAnswers;
          localStorage.setItem(`exam_answers_${s.record_id}`, JSON.stringify(restoredAnswers));
        } else if (saved) {
          const parsed = JSON.parse(saved);
          setAnswers(parsed);
          answersRef.current = parsed;
        }
      })
      .catch(() => navigate("/test-login"))
      .finally(() => setLoading(false));
  }, []);

  // Save answers to localStorage on change
  useEffect(() => {
    if (!session) return;
    localStorage.setItem(`exam_answers_${session.record_id}`, JSON.stringify(answers));
  }, [answers, session]);

  useEffect(() => {
    answersRef.current = answers;
  }, [answers]);

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60).toString().padStart(2, "0");
    const s = (secs % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  const isUrgent = timeLeft < 300; // less than 5 min

  const setAnswer = (questionId: number, value: any, isJson: boolean) => {
    if (!session) return;

    const nextAnswers = {
      ...answersRef.current,
      [questionId]: {
        question_id: questionId,
        ...(isJson ? { answer_json: value } : { answer_text: String(value) }),
      },
    };

    answersRef.current = nextAnswers;
    setAnswers(nextAnswers);
    localStorage.setItem(`exam_answers_${session.record_id}`, JSON.stringify(nextAnswers));

    examApi
      .saveProgress(session.record_id, Object.values(nextAnswers), session.exam_token)
      .then((res) => {
        if (res?.expired) {
          sessionStorage.setItem("submitted_record_id", String(session.record_id));
          navigate("/test-submit");
        }
      })
      .catch((err) => {
        console.error("답안 임시저장 실패:", err);
      });
  };

  const handleSubmit = useCallback(async (auto = false) => {
    if (!session) return;
    if (submittingRef.current) return;

    if (!auto && !showConfirm) {
      setShowConfirm(true);
      return;
    }

    submittingRef.current = true;
    setSubmitting(true);

    if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    try {
      const answerList = Object.values(answersRef.current);

      await examApi.saveProgress(session.record_id, answerList, session.exam_token);
      await examApi.submit(session.record_id, answerList, session.exam_token);

      localStorage.removeItem(`exam_answers_${session.record_id}`);
      sessionStorage.setItem("submitted_record_id", String(session.record_id));
      navigate("/test-submit");
    } catch (err) {
      console.error(err);
      alert("제출 중 오류가 발생했습니다. 다시 시도해 주세요.");
      submittingRef.current = false;
      setSubmitting(false);
      setShowConfirm(false);
    }
  }, [session, showConfirm, navigate]);

  useEffect(() => {
    if (!session || loading) return;

    const reportViolation = async (reason: string) => {
      if (submittingRef.current) return;

      const now = Date.now();

      // blur + visibilitychange가 동시에 발생하는 경우 중복 카운트 방지
      if (now - lastViolationAtRef.current < 1500) return;
      lastViolationAtRef.current = now;

      console.log("화면 이탈 감지:", reason);

      try {
        const res = await examApi.reportViolation(
          session.record_id,
          reason,
          session.exam_token
        );

        const nextCount = res.violation_count ?? violationCount + 1;
        setViolationCount(nextCount);

        if (res.disqualified) {
          alert("화면 이탈 3회 이상으로 불합격 처리되었습니다.");
          localStorage.removeItem(`exam_answers_${session.record_id}`);
          sessionStorage.setItem("submitted_record_id", String(session.record_id));
          navigate("/test-submit");
          return;
        }

        if (nextCount >= 3) {
          alert("화면 이탈 3회 이상으로 불합격 처리되었습니다.");
          localStorage.removeItem(`exam_answers_${session.record_id}`);
          sessionStorage.setItem("submitted_record_id", String(session.record_id));
          navigate("/test-submit");
          return;
        }

        setShowViolationWarning(true);
      } catch (err) {
        console.error("화면 이탈 기록 실패:", err);
      }
    };

    const handleVisibilityChange = () => {
      console.log("visibilitychange:", document.hidden);
      if (document.hidden) {
        reportViolation("visibility_hidden");
      }
    };

    const handleBlur = () => {
      console.log("window blur");
      reportViolation("window_blur");
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("blur", handleBlur);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("blur", handleBlur);
    };
  }, [session, loading, violationCount, handleSubmit]);

  // timer
  useEffect(() => {
    if (!session || loading || !endTimeRef.current) return;

    timerRef.current = setInterval(() => {
      if (!endTimeRef.current) return;

      const next = Math.max(
        0,
        Math.ceil((endTimeRef.current - Date.now()) / 1000)
      );

      setTimeLeft(next);

      if (next <= 0) {
        if (timerRef.current) {
          clearInterval(timerRef.current);
        }
        handleSubmit(true);
      }
    }, 1000);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [session, loading, handleSubmit]);
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center space-y-3">
          <Loader2 className="size-10 animate-spin text-sky-500 mx-auto" />
          <p className="text-slate-500">시험 문제를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (questions.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center space-y-3">
          <p className="text-slate-500">문제가 없습니다. 관리자에게 문의해 주세요.</p>
          <Button variant="outline" onClick={() => navigate("/test-login")}>돌아가기</Button>
        </div>
      </div>
    );
  }

  const current = questions[currentIdx];
  const answeredCount = Object.keys(answers).length;
  const progress = Math.round((answeredCount / questions.length) * 100);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top Bar */}
      <div className={`sticky top-0 z-50 px-6 py-3 flex items-center justify-between shadow-sm transition-colors ${isUrgent ? "bg-red-600" : "bg-slate-800"}`}>
        <div className="text-white">
          <p className="text-sm font-medium opacity-80">{session?.diagnosis_title}</p>
          <p className="text-xs opacity-60">{session?.applicant_name}님</p>
        </div>
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-2 font-mono text-xl font-bold ${isUrgent ? "text-white animate-pulse" : "text-white"}`}>
            <Clock className="size-5" />
            {formatTime(timeLeft)}
          </div>
          <Button
            size="sm"
            className={`${isUrgent ? "bg-white text-red-600 hover:bg-red-50" : "bg-sky-600 hover:bg-sky-500"}`}
            onClick={() => handleSubmit(false)}
            disabled={submitting}
          >
            <Send className="size-4 mr-1" />
            제출
          </Button>
        </div>
      </div>

      <div className="flex flex-1 max-w-6xl mx-auto w-full gap-6 p-6">
        {/* Question Panel */}
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
              {/* Multiple Choice */}
              {current.question_type === "multiple_choice" && current.choices_json && (
                <div className="space-y-2">
                  {current.choices_json.map((choice, i) => {
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
                        {choice}
                      </button>
                    );
                  })}
                </div>
              )}


              {/* Essay */}
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

          {/* Navigation */}
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

        {/* Question Map Sidebar */}
        <div className="w-48 flex-shrink-0">
          <Card className="border-slate-200 sticky top-24">
            <CardHeader className="pb-3 pt-4">
              <CardTitle className="text-sm text-slate-700">문제 목록</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-4 gap-1.5">
                {questions.map((q, i) => {
                  const answered = !!answers[q.question_id];
                  const isCurrent = i === currentIdx;
                  return (
                    <button
                      key={i}
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
      {showViolationWarning && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-sm shadow-2xl">
            <CardContent className="pt-6 space-y-4">
              <div className="text-center space-y-2">
                <AlertTriangle className="size-10 text-red-500 mx-auto" />
                <h3 className="text-lg font-semibold text-slate-800">
                  시험 화면 이탈 감지
                </h3>
                <p className="text-sm text-slate-500">
                  시험 중 다른 창, 탭, 프로그램으로 이동하면 부정행위로 처리될 수 있습니다.
                </p>
                <p className="text-sm text-red-600 bg-red-50 rounded-lg p-2">
                  현재 이탈 횟수: {violationCount}회 / 3회
                </p>
              </div>
              <Button
                className="w-full bg-red-600 hover:bg-red-700"
                onClick={() => setShowViolationWarning(false)}
              >
                시험 계속하기
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
      {/* Submit Confirm Overlay */}
      {showConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-sm shadow-2xl">
            <CardContent className="pt-6 space-y-4">
              <div className="text-center space-y-2">
                <AlertTriangle className="size-10 text-amber-500 mx-auto" />
                <h3 className="text-lg font-semibold text-slate-800">시험을 제출하시겠습니까?</h3>
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
