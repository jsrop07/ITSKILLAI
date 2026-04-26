import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { Button } from "../../components/ui/button";
import { Card, CardContent } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Clock, FileText, AlertTriangle, ChevronRight, Loader2 } from "lucide-react";
import type { ExamLoginResponse } from "../../../lib/types";

export default function TestIntro() {
  const navigate = useNavigate();
  const [session, setSession] = useState<ExamLoginResponse | null>(null);

  useEffect(() => {
    const raw = sessionStorage.getItem("exam_session");
    if (!raw) {
      navigate("/test-login");
      return;
    }
    try {
      setSession(JSON.parse(raw));
    } catch {
      navigate("/test-login");
    }
  }, []);

  if (!session) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="size-8 animate-spin text-sky-500" />
      </div>
    );
  }

  const notices = [
    "시험 중 브라우저를 닫거나 새로고침하면 답안이 초기화될 수 있습니다.",
    "제한 시간이 종료되면 자동으로 제출됩니다.",
    "모든 문제를 꼼꼼히 읽고 답변해 주세요.",
    "시험 중 외부 자료 참고는 금지입니다.",
    "객관식 문제는 하나의 답을 선택하세요.",
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-sky-50 py-12 px-4">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <p className="text-sm text-sky-600 font-medium">환영합니다, {session.applicant_name}님</p>
          <h1 className="text-3xl font-bold text-slate-800">{session.diagnosis_title}</h1>
          <p className="text-slate-500">시험을 시작하기 전 아래 내용을 확인해 주세요.</p>
        </div>

        {/* Exam Info Cards */}
        <div className="grid grid-cols-3 gap-4">
          <Card className="border-sky-200 bg-sky-50">
            <CardContent className="pt-4 pb-4 text-center space-y-1">
              <Clock className="size-6 text-sky-600 mx-auto" />
              <p className="text-2xl font-bold text-sky-700">{session.duration_minutes}분</p>
              <p className="text-xs text-sky-600">제한 시간</p>
            </CardContent>
          </Card>
          <Card className="border-slate-200 bg-slate-50">
            <CardContent className="pt-4 pb-4 text-center space-y-1">
              <FileText className="size-6 text-slate-600 mx-auto" />
              <p className="text-2xl font-bold text-slate-700">{session.question_count}문제</p>
              <p className="text-xs text-slate-500">총 문제 수</p>
            </CardContent>
          </Card>
          <Card className="border-amber-200 bg-amber-50">
            <CardContent className="pt-4 pb-4 text-center space-y-1">
              <Badge className="bg-amber-500 text-white text-lg px-3 py-1 rounded-lg font-bold border-0">
                {session.pass_score}점
              </Badge>
              <p className="text-xs text-amber-600 mt-1">합격 기준</p>
            </CardContent>
          </Card>
        </div>

        {/* Notice */}
        <Card className="border-slate-200">
          <CardContent className="pt-5 pb-5">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="size-5 text-amber-500" />
              <h2 className="font-semibold text-slate-800">시험 주의사항</h2>
            </div>
            <ul className="space-y-3">
              {notices.map((notice, i) => (
                <li key={i} className="flex items-start gap-3 text-sm text-slate-600">
                  <span className="size-5 flex-shrink-0 flex items-center justify-center rounded-full bg-amber-100 text-amber-700 font-medium text-xs">
                    {i + 1}
                  </span>
                  {notice}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        {/* CTA */}
        <div className="flex flex-col gap-3">
          <Button
            className="w-full h-14 text-base font-semibold bg-sky-600 hover:bg-sky-700"
            onClick={() => navigate("/test-room")}
          >
            시험 시작하기
            <ChevronRight className="size-5 ml-2" />
          </Button>
          <p className="text-center text-xs text-slate-400">
            시작 버튼을 누르면 제한 시간이 카운트다운됩니다.
          </p>
        </div>
      </div>
    </div>
  );
}
