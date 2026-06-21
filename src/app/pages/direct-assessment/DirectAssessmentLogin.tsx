import { useState } from "react";
import { useNavigate } from "react-router";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Card, CardContent } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { AlertCircle, Laptop, Loader2, ShieldCheck } from "lucide-react";
import { directCbtApi } from "../../../lib/api";

export default function DirectAssessmentLogin() {
    const navigate = useNavigate();

    const [accessCode, setAccessCode] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!accessCode.trim()) {
            setError("체험 코드를 입력해 주세요.");
            return;
        }

        setError("");
        setLoading(true);

        try {
            const result = await directCbtApi.login(accessCode.trim());

            // 이전 direct-cbt 진행 정보 제거
            // record_id와 applicant_id가 서로 꼬이는 문제 방지
            localStorage.removeItem("direct_applicant_id");
            localStorage.removeItem("direct_applicant_name");
            localStorage.removeItem("direct_applicant_email");
            localStorage.removeItem("direct_record_id");
            localStorage.removeItem("direct_exam_token");
            localStorage.removeItem("direct_ai_report_generated");
            localStorage.removeItem("direct_ai_report_limit_exceeded");
            localStorage.removeItem("direct_ai_report_remaining_today");

            // 백엔드에서 자동 생성한 체험 응시자 정보 저장
            localStorage.setItem("direct_applicant_id", String(result.applicant_id));
            localStorage.setItem("direct_applicant_name", result.name);
            localStorage.setItem("direct_applicant_email", result.email);

            navigate("/direct-assessment/exams");
        } catch (err: any) {
            setError(err.response?.data?.detail || "체험 코드 확인 중 오류가 발생했습니다.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-blue-50 flex items-center justify-center p-4">
            <div className="w-full max-w-md space-y-6">
                <div className="text-center">
                    <div className="mx-auto size-16 rounded-full bg-sky-100 flex items-center justify-center mb-4">
                        <Laptop className="size-8 text-sky-600" />
                    </div>

                    <Badge className="mb-3 bg-sky-100 text-sky-700 hover:bg-sky-100">
                        Direct CBT
                    </Badge>

                    <h1 className="text-2xl font-bold text-slate-800">
                        직접 CBT 진단
                    </h1>

                    <p className="text-slate-500 mt-2 leading-relaxed">
                        체험 코드를 입력하면 관리자 배정 없이<br />
                        공개된 시험지를 선택해 바로 응시할 수 있습니다.
                    </p>
                </div>

                <div className="rounded-xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-700">
                    <div className="flex gap-3">
                        <ShieldCheck className="size-5 flex-shrink-0 text-sky-600" />
                        <div className="space-y-1">
                            <p className="font-medium">이용 안내</p>
                            <p>• 체험 코드를 입력하면 관리자 승인 없이 진단을 진행할 수 있습니다.</p>
                            <p>• 체험형 결과는 이전 기록과 비교하지 않고 현재 결과 기준으로 분석됩니다.</p>
                        </div>
                    </div>
                </div>

                <Card className="shadow-lg border-slate-200">
                    <CardContent className="pt-6">
                        <form onSubmit={handleLogin} className="space-y-5">
                            <div className="space-y-2">
                                <Label htmlFor="direct-access-code">체험 코드</Label>
                                <Input
                                    id="direct-access-code"
                                    type="password"
                                    value={accessCode}
                                    onChange={(e) => setAccessCode(e.target.value)}
                                    placeholder="체험 코드를 입력해 주세요"
                                    required
                                    className="h-11"
                                />
                                <p className="text-xs text-slate-400">
                                    포트폴리오 검토용 체험 코드를 입력하면 바로 진단을 시작할 수 있습니다.
                                </p>
                            </div>

                            {error && (
                                <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 p-3 rounded-lg">
                                    <AlertCircle className="size-4 flex-shrink-0" />
                                    <span>{error}</span>
                                </div>
                            )}

                            <Button
                                type="submit"
                                className="w-full h-11 bg-sky-600 hover:bg-sky-700"
                                disabled={loading}
                            >
                                {loading ? <Loader2 className="size-4 animate-spin mr-2" /> : null}
                                시험지 선택하기
                            </Button>
                        </form>
                    </CardContent>
                </Card>

                <p className="text-center text-xs text-slate-400">
                    기존 이메일 토큰 방식 응시는 기존 응시자 로그인 페이지를 이용해 주세요.
                </p>
            </div>
        </div>
    );
}