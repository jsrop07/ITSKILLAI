import { useState } from "react";
import { useNavigate } from "react-router";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, } from "../../components/ui/select";
import { ClipboardList, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { applicantsApi } from "../../../lib/api";
import type { ApplicantCreate } from "../../../lib/types";

export default function Apply() {
  const navigate = useNavigate();
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState<ApplicantCreate>({
    name: "",
    email: "",
    phone: "",
    target_role: "",
    experience_level: "",
    tech_stack: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || !form.email) return setError("이름과 이메일은 필수입니다.");
    setError("");
    setLoading(true);
    try {
      await applicantsApi.apply(form);
      setSubmitted(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || "신청 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-blue-50 flex items-center justify-center p-4">
        <Card className="w-full max-w-md shadow-lg border-slate-200 text-center">
          <CardContent className="pt-10 pb-8 space-y-4">
            <div className="mx-auto size-20 rounded-full bg-green-100 flex items-center justify-center">
              <CheckCircle className="size-10 text-green-600" />
            </div>
            <h2 className="text-2xl font-semibold text-slate-800">신청 완료!</h2>
            <p className="text-slate-600 leading-relaxed">
              시험 신청이 접수되었습니다.<br />
              담당자가 시험을 배정한 후 <strong>로그인 토큰</strong>이 이메일로 발송됩니다.
            </p>
            <p className="text-sm text-slate-400">토큰을 받으신 후 응시자 로그인 페이지에서 시험에 참여하실 수 있습니다.</p>
            <div className="pt-4 flex flex-col gap-3">
              <Button
                className="bg-sky-600 hover:bg-sky-700"
                onClick={() => navigate("/test-login")}
              >
                응시자 로그인으로 이동
              </Button>
              <Button variant="outline" onClick={() => { setSubmitted(false); setForm({ name: "", email: "", phone: "", target_role: "", experience_level: "", tech_stack: "" }); }}>
                추가 신청
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-blue-50 py-12 px-4">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center size-16 rounded-2xl bg-sky-600 mb-4">
            <ClipboardList className="size-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-slate-800">IT 역량 평가 신청</h1>
          <p className="text-slate-500">기본 정보를 입력하여 시험을 신청해 주세요.</p>
        </div>

        {/* Notice Box */}
        <div className="bg-sky-50 border border-sky-200 rounded-xl p-4 text-sm text-sky-700 space-y-1">
          <p className="font-medium">📋 시험 신청 안내</p>
          <p>• 신청 완료 후 담당자가 시험을 배정하며, 로그인 토큰이 이메일로 발송됩니다.</p>
          <p>• 시험 시작 전 안내 페이지를 반드시 확인해 주세요.</p>
        </div>

        {/* Form */}
        <Card className="shadow-lg border-slate-200">
          <CardHeader>
            <CardTitle className="text-lg">기본 정보 입력</CardTitle>
            <CardDescription>* 표시된 항목은 필수입니다.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="apply-name">이름 *</Label>
                  <Input
                    id="apply-name"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="홍길동"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="apply-email">이메일 *</Label>
                  <Input
                    id="apply-email"
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    placeholder="example@email.com"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="apply-phone">연락처</Label>
                  <Input
                    id="apply-phone"
                    value={form.phone}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
                    placeholder="010-0000-0000"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="apply-exp">경력</Label>
                  <Input
                    id="apply-exp"
                    value={form.experience_level}
                    onChange={(e) => setForm({ ...form, experience_level: e.target.value })}
                    placeholder="3년"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="apply-stack">보유 기술 스택</Label>
                <Textarea
                  id="apply-stack"
                  value={form.tech_stack}
                  onChange={(e) => setForm({ ...form, tech_stack: e.target.value })}
                  placeholder="예: Java, Spring Boot, MySQL, Redis"
                  rows={3}
                />
              </div>

              {error && (
                <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 p-3 rounded-lg">
                  <AlertCircle className="size-4 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <Button
                type="submit"
                className="w-full h-12 bg-sky-600 hover:bg-sky-700 text-base font-medium"
                disabled={loading}
              >
                {loading ? <Loader2 className="size-5 animate-spin mr-2" /> : null}
                시험 신청하기
              </Button>
            </form>
          </CardContent>
        </Card>

        <p className="text-center text-sm text-slate-400">
          이미 토큰을 받으셨나요?{" "}
          <button
            className="text-sky-600 hover:underline font-medium"
            onClick={() => navigate("/test-login")}
          >
            응시자 로그인
          </button>
        </p>
      </div>
    </div>
  );
}
