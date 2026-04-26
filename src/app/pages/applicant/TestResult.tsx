import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { CheckCircle, XCircle, TrendingUp, Award, Loader2, Lock } from "lucide-react";
import { examApi } from "../../../lib/api";
import type { ExamResultResponse } from "../../../lib/types";

export default function TestResult() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const recordId = searchParams.get("record_id");

  const [result, setResult] = useState<ExamResultResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [notVisible, setNotVisible] = useState(false);

  useEffect(() => {
    if (!recordId) { navigate("/test-login"); return; }
    examApi.getResult(Number(recordId))
      .then(setResult)
      .catch((err) => {
        if (err.response?.status === 403) setNotVisible(true);
        else navigate("/test-login");
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

  const passScore = result.pass_score;
  const scorePercent = Math.min(Math.round((result.total_score / (passScore / 0.7)) * 100), 100);
  const competencies = result.competency_breakdown || {};

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-sky-50 py-10 px-4">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-1">
          <p className="text-sm text-slate-500">{result.applicant_name}님의 시험 결과</p>
          <h1 className="text-2xl font-bold text-slate-800">{result.diagnosis_title}</h1>
        </div>

        {/* Score Card */}
        <Card className={`border-2 shadow-lg ${result.pass_yn ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"}`}>
          <CardContent className="py-8 text-center space-y-4">
            <div className={`mx-auto size-24 rounded-full flex items-center justify-center ${result.pass_yn ? "bg-green-100" : "bg-red-100"}`}>
              {result.pass_yn
                ? <CheckCircle className="size-12 text-green-600" />
                : <XCircle className="size-12 text-red-500" />
              }
            </div>
            <div>
              <p className="text-5xl font-bold text-slate-800">{result.total_score}<span className="text-2xl font-normal text-slate-500">점</span></p>
              <p className="text-slate-500 text-sm mt-1">합격 기준: {passScore}점</p>
            </div>
            <Badge
              variant="secondary"
              className={`text-base px-5 py-1.5 ${result.pass_yn ? "bg-green-200 text-green-800" : "bg-red-200 text-red-800"}`}
            >
              {result.pass_yn ? "✅ 합격" : "❌ 불합격"}
            </Badge>
            {result.submitted_at && (
              <p className="text-xs text-slate-400">
                제출일시: {new Date(result.submitted_at).toLocaleString("ko-KR")}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Competency Breakdown */}
        {Object.keys(competencies).length > 0 && (
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

        {/* Score Gauge */}
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="py-5">
            <div className="flex items-center justify-between text-sm text-slate-500 mb-2">
              <span>0점</span>
              <span className="flex items-center gap-1">
                <Award className="size-4 text-amber-500" />
                합격 기준 {passScore}점
              </span>
              <span>100점</span>
            </div>
            <div className="h-4 bg-slate-100 rounded-full overflow-hidden relative">
              <div
                className={`h-full rounded-full transition-all ${result.pass_yn ? "bg-gradient-to-r from-sky-500 to-green-500" : "bg-gradient-to-r from-sky-500 to-amber-500"}`}
                style={{ width: `${scorePercent}%` }}
              />
              {/* Pass line indicator */}
              <div
                className="absolute top-0 h-full w-0.5 bg-amber-500 opacity-70"
                style={{ left: `${passScore}%` }}
              />
            </div>
          </CardContent>
        </Card>

        <div className="flex flex-col gap-3">
          <Button variant="outline" className="w-full" onClick={() => navigate("/apply")}>
            메인으로 돌아가기
          </Button>
        </div>
      </div>
    </div>
  );
}
