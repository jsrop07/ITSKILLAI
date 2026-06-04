import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { AlertCircle, ArrowRight, Clock, FileText, Loader2, RefreshCcw, UserRound } from "lucide-react";
import { directCbtApi } from "../../../lib/api";
import type { DirectCbtDiagnosisItem } from "../../../lib/types";

export default function DirectAssessmentExamList() {
    const navigate = useNavigate();

    const [diagnoses, setDiagnoses] = useState<DirectCbtDiagnosisItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [startingId, setStartingId] = useState<number | null>(null);
    const [error, setError] = useState("");

    const applicantId = Number(localStorage.getItem("direct_applicant_id") || 0);
    const applicantName = localStorage.getItem("direct_applicant_name") || "";
    const applicantEmail = localStorage.getItem("direct_applicant_email") || "";

    const loadDiagnoses = async () => {
        try {
            setLoading(true);
            setError("");
            const data = await directCbtApi.listDiagnoses();
            setDiagnoses(data);
        } catch (err: any) {
            setError(err.response?.data?.detail || "시험지 목록을 불러오지 못했습니다.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (!applicantId) {
            navigate("/direct-assessment/login");
            return;
        }

        loadDiagnoses();
    }, [applicantId, navigate]);

    const handleStart = async (diagnosisId: number) => {
        try {
            setStartingId(diagnosisId);
            setError("");

            const result = await directCbtApi.startRecord(diagnosisId, applicantId);

            localStorage.setItem("direct_record_id", String(result.record_id));
            localStorage.setItem("direct_exam_token", result.exam_token);

            navigate(`/direct-assessment/take/${result.record_id}`);
        } catch (err: any) {
            setError(err.response?.data?.detail || "시험 시작 중 오류가 발생했습니다.");
        } finally {
            setStartingId(null);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50">
                <Loader2 className="size-8 animate-spin text-sky-500" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-sky-50 px-4 py-10">
            <div className="mx-auto max-w-4xl space-y-6">
                <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                    <div>
                        <Badge className="mb-3 bg-sky-100 text-sky-700 hover:bg-sky-100">
                            Direct CBT
                        </Badge>
                        <h1 className="text-3xl font-bold text-slate-900">시험지 선택</h1>
                        <p className="mt-2 text-slate-500">
                            공개된 시험지를 선택하면 바로 응시가 시작됩니다.
                        </p>
                    </div>

                    <Card className="border-slate-200 shadow-sm">
                        <CardContent className="flex items-center gap-3 p-4">
                            <div className="size-10 rounded-full bg-sky-100 flex items-center justify-center">
                                <UserRound className="size-5 text-sky-600" />
                            </div>
                            <div>
                                <p className="text-sm font-medium text-slate-800">
                                    {applicantName || "응시자"}
                                </p>
                                <p className="text-xs text-slate-500">{applicantEmail}</p>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                    <p className="font-medium">AI 진단 이용 제한</p>
                    <p className="mt-1">
                        같은 이메일 기준 하루 3회까지 AI 종합 진단 리포트가 생성됩니다.
                        4회차부터는 점수와 기본 분석만 제공됩니다.
                    </p>
                </div>

                {error && (
                    <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-600">
                        <AlertCircle className="size-4" />
                        <span>{error}</span>
                    </div>
                )}

                {diagnoses.length === 0 ? (
                    <Card className="border-slate-200 shadow-sm">
                        <CardContent className="py-14 text-center">
                            <div className="mx-auto size-14 rounded-full bg-slate-100 flex items-center justify-center mb-4">
                                <FileText className="size-7 text-slate-400" />
                            </div>
                            <h2 className="text-lg font-semibold text-slate-800">
                                직접 응시 가능한 시험지가 없습니다.
                            </h2>
                            <p className="mt-2 text-sm text-slate-500">
                                관리자가 직접 CBT 공개로 설정한 시험지만 표시됩니다.
                            </p>
                            <Button
                                variant="outline"
                                className="mt-5"
                                onClick={loadDiagnoses}
                            >
                                <RefreshCcw className="size-4 mr-2" />
                                다시 불러오기
                            </Button>
                        </CardContent>
                    </Card>
                ) : (
                    <div className="grid gap-4">
                        {diagnoses.map((diagnosis) => (
                            <Card
                                key={diagnosis.diagnosis_id}
                                className="border-slate-200 shadow-sm hover:shadow-md transition-shadow"
                            >
                                <CardHeader className="pb-3">
                                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <Badge variant="secondary" className="bg-sky-100 text-sky-700">
                                                    {diagnosis.level || "intermediate"}
                                                </Badge>
                                                <Badge variant="outline">즉시 응시</Badge>
                                            </div>

                                            <CardTitle className="mt-3 text-xl text-slate-900">
                                                {diagnosis.title}
                                            </CardTitle>

                                            <p className="mt-2 text-sm text-slate-500 leading-relaxed">
                                                {diagnosis.description || "시험 설명이 등록되지 않았습니다."}
                                            </p>
                                        </div>

                                        <Button
                                            className="bg-sky-600 hover:bg-sky-700"
                                            onClick={() => handleStart(diagnosis.diagnosis_id)}
                                            disabled={startingId === diagnosis.diagnosis_id}
                                        >
                                            {startingId === diagnosis.diagnosis_id ? (
                                                <Loader2 className="size-4 animate-spin mr-2" />
                                            ) : (
                                                <ArrowRight className="size-4 mr-2" />
                                            )}
                                            응시하기
                                        </Button>
                                    </div>
                                </CardHeader>

                                <CardContent>
                                    <div className="grid grid-cols-3 gap-3">
                                        <div className="rounded-lg bg-slate-50 p-3">
                                            <p className="text-xs text-slate-500">문항 수</p>
                                            <p className="mt-1 font-semibold text-slate-800">
                                                {diagnosis.question_count}문항
                                            </p>
                                        </div>

                                        <div className="rounded-lg bg-slate-50 p-3">
                                            <p className="text-xs text-slate-500">제한 시간</p>
                                            <p className="mt-1 flex items-center gap-1 font-semibold text-slate-800">
                                                <Clock className="size-4 text-sky-600" />
                                                {diagnosis.duration_minutes}분
                                            </p>
                                        </div>

                                        <div className="rounded-lg bg-slate-50 p-3">
                                            <p className="text-xs text-slate-500">합격 기준</p>
                                            <p className="mt-1 font-semibold text-slate-800">
                                                {diagnosis.pass_score}점
                                            </p>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                )}

                <div className="text-center">
                    <Button
                        variant="ghost"
                        className="text-slate-500"
                        onClick={() => {
                            localStorage.removeItem("direct_applicant_id");
                            localStorage.removeItem("direct_applicant_name");
                            localStorage.removeItem("direct_applicant_email");
                            navigate("/direct-assessment/login");
                        }}
                    >
                        다른 이메일로 로그인
                    </Button>
                </div>
            </div>
        </div>
    );
}