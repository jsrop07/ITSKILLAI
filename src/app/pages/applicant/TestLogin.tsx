import { useState } from "react";
import { useNavigate } from "react-router";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Lock, AlertCircle, Loader2 } from "lucide-react";
import { examApi } from "../../../lib/api";

export default function TestLogin() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !token) return setError("이름과 토큰을 모두 입력해 주세요.");
    setError("");
    setLoading(true);
    try {
      const res = await examApi.login(email, token);
      sessionStorage.setItem("exam_session", JSON.stringify(res));

      // 이미 제출/채점 완료된 경우 → 결과 화면으로 바로 이동
      if (res.status === "graded" || res.status === "submitted") {
        sessionStorage.setItem("submitted_record_id", String(res.record_id));
        navigate(`/test-result?record_id=${res.record_id}`);
      } else {
        navigate("/test-intro");
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "로그인에 실패했습니다. 이름과 토큰을 확인해 주세요.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-blue-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <div className="mx-auto size-16 rounded-full bg-sky-100 flex items-center justify-center mb-4">
            <Lock className="size-8 text-sky-600" />
          </div>
          <h1 className="text-2xl font-bold text-slate-800">응시자 로그인</h1>
          <p className="text-slate-500 mt-2">이름과 발급받은 로그인 토큰을 입력해 주세요.</p>
        </div>

        <Card className="shadow-lg border-slate-200">
          <CardContent className="pt-6">
            <form onSubmit={handleLogin} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="login-name">이메일</Label>
                <Input
                  id="login-name"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="홍길동"
                  required
                  className="h-11"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="login-token">로그인 토큰</Label>
                <Input
                  id="login-token"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="관리자로부터 받은 토큰을 입력하세요"
                  required
                  className="h-11 font-mono text-sm"
                />
                <p className="text-xs text-slate-400">
                  토큰은 시험 배정 후 이메일로 발송됩니다.
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
                로그인
              </Button>
            </form>
          </CardContent>
        </Card>

        <p className="text-center text-sm text-slate-400">
          아직 신청하지 않으셨나요?{" "}
          <button
            className="text-sky-600 hover:underline font-medium"
            onClick={() => navigate("/apply")}
          >
            시험 신청하기
          </button>
        </p>
      </div>
    </div>
  );
}
