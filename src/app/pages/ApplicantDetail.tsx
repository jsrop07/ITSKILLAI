import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { useNavigate, useParams } from "react-router";
import { ArrowLeft, Sparkles, Loader2, Save, Send } from "lucide-react";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "../components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "../components/ui/dialog";
import { Switch } from "../components/ui/switch";
import { applicantsApi, recordsApi, diagnosesApi } from "../../lib/api";
import type { Applicant, ExamRecord, AnswerDetail, Diagnosis } from "../../lib/types";
import AIReportCard from "../components/result/AIReportCard";

export default function ApplicantDetail() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();

  const [applicant, setApplicant] = useState<Applicant | null>(null);
  const [record, setRecord] = useState<ExamRecord | null>(null);
  const [answers, setAnswers] = useState<AnswerDetail[]>([]);
  const [gradedDiagnosis, setGradedDiagnosis] = useState<Diagnosis | null>(null);
  const [diagnoses, setDiagnoses] = useState<Diagnosis[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedAnswer, setSelectedAnswer] = useState<AnswerDetail | null>(null);
  const [aiReportLoading, setAiReportLoading] = useState(false);
  const [aiReportOpen, setAiReportOpen] = useState(false);
  const [form, setForm] = useState({
    name: "", email: "", phone: "", target_role: "", experience_level: "", tech_stack: "",
  });

  const [selectedDiagnosisId, setSelectedDiagnosisId] = useState<string>("");
  const [deadlineAt, setDeadlineAt] = useState<string>("");

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

  const loadData = async () => {
    if (!id) return;
    try {
      const app = await applicantsApi.get(Number(id));
      setApplicant(app);
      setForm({
        name: app.name || "",
        email: app.email || "",
        phone: app.phone || "",
        target_role: app.target_role || "",
        experience_level: app.experience_level || "",
        tech_stack: app.tech_stack || "",
      });

      const records = await recordsApi.list({ applicant_id: Number(id) });
      if (records.length > 0) {
        const latest = records[0];
        setRecord(latest);

        if (latest.status === "graded" || latest.status === "submitted") {
          const ans = await recordsApi.getAnswers(latest.record_id);
          setAnswers(ans);
          try {
            const d = await diagnosesApi.get(latest.diagnosis_id);
            setGradedDiagnosis(d);
          } catch (e) { }
        }
      }

      // 항상 시험 목록 로드 (상태 표시용)
      const diags = await diagnosesApi.list({ status: "active" });
      setDiagnoses(diags);
      // 배정된 기록이 있으면 기록의 정보를, 없으면 응시자의 임시 정보를 우선 표시
      if (records.length > 0) {
        const latest = records[0];
        setSelectedDiagnosisId(String(latest.diagnosis_id));
        if (latest.deadline_at) setDeadlineAt(latest.deadline_at.substring(0, 10));
      } else {
        if (app.target_diagnosis_id) setSelectedDiagnosisId(String(app.target_diagnosis_id));
        if (app.target_deadline_at) setDeadlineAt(app.target_deadline_at.substring(0, 10));
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [id]);

  const handleGenerateAIReport = async (recordId: number) => {
    try {
      setAiReportLoading(true);

      const res = await recordsApi.generateAIReport(recordId);

      setRecord((prev) =>
        prev
          ? {
            ...prev,
            summary_comment: res.summary_comment,
          }
          : prev
      );
      setAiReportOpen(true);
    } catch (error) {
      console.error(error);
      alert("AI 결과 리포트 생성에 실패했습니다.");
    } finally {
      setAiReportLoading(false);
    }
  };

  const handleSave = async () => {
    if (!applicant) return;
    setSaving(true);
    try {
      await applicantsApi.update(applicant.applicant_id, {
        ...form,
        status: "temp_saved",
        target_diagnosis_id: selectedDiagnosisId ? Number(selectedDiagnosisId) : undefined,
        target_deadline_at: deadlineAt ? new Date(deadlineAt + "T23:59:59").toISOString() : undefined,
      });
      alert("임시 저장되었습니다.");
      loadData();
    } catch (err) {
      alert("저장 실패");
    } finally {
      setSaving(false);
    }
  };

  const handleAssignEmail = async () => {
    if (!applicant) return;
    if (!selectedDiagnosisId) return alert("배정할 시험을 선택해주세요.");
    if (!deadlineAt) return alert("만료일을 설정해주세요.");
    setSaving(true);
    try {
      await recordsApi.create({
        applicant_id: applicant.applicant_id,
        diagnosis_id: Number(selectedDiagnosisId),
        deadline_at: new Date(deadlineAt + "T23:59:59").toISOString(),
      });
      alert("시험이 배정되었고 응시자에게 이메일이 발송되었습니다.");
      loadData();
    } catch (err) {
      alert("배정 실패");
    } finally {
      setSaving(false);
    }
  };

  const handlePublishResult = async () => {
    if (!record) return;

    if (!window.confirm("응시자에게 결과를 공개하고 이메일을 발송하시겠습니까?")) {
      return;
    }

    try {
      setSaving(true);
      const updated = await recordsApi.publishResult(record.record_id);
      setRecord(updated);
      alert("결과가 공개되었고 응시자에게 이메일이 발송되었습니다.");
    } catch (err: any) {
      alert(err.response?.data?.detail || "결과 공개 실패");
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateAssignment = async () => {
    if (!record) return;
    if (!selectedDiagnosisId) return alert("시험지를 선택해주세요.");
    if (!deadlineAt) return alert("마감일을 선택해주세요.");
    setSaving(true);
    try {
      await recordsApi.update(record.record_id, {
        diagnosis_id: Number(selectedDiagnosisId),
        deadline_at: new Date(deadlineAt + "T23:59:59").toISOString(),
      } as any);
      alert("배정 정보가 수정되었습니다.");
      loadData();
    } catch (err) {
      alert("수정 실패");
    } finally {
      setSaving(false);
    }
  };

  const getViolationReasonLabel = (reason?: string) => {
    switch (reason) {
      case "window_blur":
        return "시험 창 포커스 이탈";
      case "visibility_hidden":
        return "다른 탭 또는 화면으로 이동";
      case "page_hidden":
        return "시험 화면 숨김";
      case "fullscreen_exit":
        return "전체화면 해제";
      case "page_closed":
        return "시험 창 닫기 또는 새로고침";
      default:
        return reason || "알 수 없는 화면 이탈";
    }
  };

  const parseViolationLogs = (value: any) => {
    if (!value) return [];

    if (Array.isArray(value)) return value;

    if (typeof value === "string") {
      try {
        const parsed = JSON.parse(value);
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        return [];
      }
    }

    return [];
  };

  const violationLogs = parseViolationLogs(record?.violation_log_json);

  const violationReasonText = (() => {
    if (violationLogs.length === 0) return "-";

    const counts = violationLogs.reduce((acc: Record<string, number>, log: any) => {
      const label = getViolationReasonLabel(log.reason);
      acc[label] = (acc[label] || 0) + 1;
      return acc;
    }, {});

    return Object.entries(counts)
      .map(([label, count]) => `${label} ${count}회`)
      .join(", ");
  })();
  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-96">
        <Loader2 className="size-8 animate-spin text-sky-500" />
      </div>
    );
  }

  if (!applicant) {
    return <div className="p-8 text-slate-500">응시자를 찾을 수 없습니다.</div>;
  }

  const isPending = applicant.status === "pending" || applicant.status === "temp_saved";
  const isAssigned = !isPending; // ready / in_progress / completed
  const isReady = record?.status === "ready";
  const competencies: Record<string, number> = record?.competency_breakdown_json || {};

  const assignedDiagnosisName =
    diagnoses.find((d) => String(d.diagnosis_id) === String(record?.diagnosis_id))?.title ||
    gradedDiagnosis?.title ||
    (record ? `시험 #${record.diagnosis_id}` : "-");

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/applicants")}>
          <ArrowLeft className="size-5" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-semibold text-slate-800">응시자 상세 정보</h1>
          <p className="text-sm text-slate-500 mt-1">시험 결과 및 응시자 관리</p>
        </div>
        {(isPending || isReady) && (
          <div className="flex gap-2">
            <Button variant="outline" onClick={isPending ? handleSave : handleUpdateAssignment} disabled={saving}>
              {saving ? <Loader2 className="size-4 animate-spin mr-2" /> : <Save className="size-4 mr-2" />}
              {isPending ? "임시 저장" : "배정 정보 수정"}
            </Button>
            {isPending && (
              <Button className="bg-sky-600 hover:bg-sky-700" onClick={handleAssignEmail} disabled={saving}>
                <Send className="size-4 mr-2" />
                이메일 보내기(시험 배정)
              </Button>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
        {/* 좌: 기본 정보 */}
        <div className="space-y-4 self-start">
          <Card className="border-slate-200 bg-white shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">응시자 기본 정보</CardTitle>
              <CardDescription>시험 배정 후에는 일부 정보만 확인 가능합니다.</CardDescription>
            </CardHeader>

            <CardContent className="p-4">
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="text-xs text-slate-500">이름</p>
                  <p className="mt-1 text-sm font-medium text-slate-900">{applicant?.name || "-"}</p>
                </div>

                <div className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="text-xs text-slate-500">이메일</p>
                  <p className="mt-1 font-medium text-slate-900 break-all">{applicant?.email || "-"}</p>
                </div>

                <div className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="text-xs text-slate-500">전화번호</p>
                  <p className="mt-1 text-sm font-medium text-slate-900">{applicant?.phone || "-"}</p>
                </div>

                <div className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="text-xs text-slate-500">지원 직무</p>
                  <p className="mt-1 text-sm font-medium text-slate-900">{applicant?.target_role || "-"}</p>
                </div>

                <div className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="text-xs text-slate-500">경력 수준</p>
                  <p className="mt-1 text-sm font-medium text-slate-900">{applicant?.experience_level || "-"}</p>
                </div>

                <div className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="text-xs text-slate-500">기술 스택</p>
                  <p className="mt-1 text-sm font-medium text-slate-900">{applicant?.tech_stack || "-"}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          {/* 역량 세부 분석 */}
          {record?.competency_breakdown_json && (
            <Card className="border-slate-200 bg-white shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">역량 세부 분석</CardTitle>
                <CardDescription>각 역량 영역별 평가 결과 (%)</CardDescription>
              </CardHeader>
              <CardContent className="p-4 pt-0">
                <div className="space-y-4">
                  {Object.entries(record.competency_breakdown_json).map(([key, value]) => {
                    const score = Number(value || 0);

                    return (
                      <div key={key}>
                        <div className="mb-1 flex items-center justify-between text-sm">
                          <span className="font-medium text-slate-700">{key}</span>
                          <span className="font-semibold text-slate-900">{score}%</span>
                        </div>
                        <div className="h-2 rounded-full bg-slate-100">
                          <div
                            className="h-2 rounded-full bg-sky-500"
                            style={{ width: `${Math.min(score, 100)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* 우: 시험 배정 / 결과 대시보드 */}
        <div className="space-y-4">
          {/* ── 배정 전 또는 배정 후 시작 전(ready) 상태: 시험 선택 수정 가능 ── */}
          {(isPending || isReady) && (
            <Card className="border-sky-200 bg-sky-50">
              <CardHeader>
                <CardTitle className="text-sky-800">{isPending ? "시험 배정 설정" : "배정된 시험 수정"}</CardTitle>
                <CardDescription className="text-sky-600">
                  {isPending ? "응시자에게 제공할 시험과 마감일을 선택합니다." : "시험을 시작하기 전까지 시험지와 마감일을 변경할 수 있습니다."}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label className="text-sky-800">배정할 시험</Label>
                    {selectedDiagnosisId && (
                      <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => navigate(`/exams/${selectedDiagnosisId}`)}>
                        선택한 시험 문제수정
                      </Button>
                    )}
                  </div>
                  <Select value={selectedDiagnosisId} onValueChange={setSelectedDiagnosisId}>
                    <SelectTrigger className="bg-white"><SelectValue placeholder="진행할 시험 선택" /></SelectTrigger>
                    <SelectContent>
                      {diagnoses.map((d) => (
                        <SelectItem key={d.diagnosis_id} value={String(d.diagnosis_id)}>
                          {d.title} ({d.duration_minutes}분)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label className="text-sky-800">응시 만료일 (해당 일 23:59:59 실격 처리)</Label>
                  <Input type="date" className="bg-white" value={deadlineAt} onChange={(e) => setDeadlineAt(e.target.value)} />
                </div>
                {!isPending && record && (
                  <div className="pt-2 border-t border-sky-100 flex items-center justify-between">
                    <span className="text-xs text-sky-700">현재 응시 토큰: <code className="font-mono font-bold">{record.login_token}</code></span>
                    <Button variant="link" size="sm" className="h-auto p-0 text-xs text-sky-600" onClick={() => navigate("/test-login")}>응시 페이지 이동</Button>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* ── 배정 후 (Ready 상태가 아닐 때만 정보 카드 표시, Ready일 때는 위에서 수정 가능하므로 설명만) ── */}
          {isAssigned && !isReady && record && (
            <Card className="border-sky-100 bg-sky-50/60 shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">배정된 시험 정보</CardTitle>
              </CardHeader>

              <CardContent className="grid grid-cols-1 gap-3 md:grid-cols-2 p-4">
                <div className="rounded-lg bg-white/80 px-4 py-3">
                  <p className="text-xs text-slate-500">시험지</p>
                  <p className="mt-1 text-sm font-medium text-slate-900">{gradedDiagnosis?.title || "-"}</p>
                </div>

                <div className="rounded-lg bg-white/80 px-4 py-3">
                  <p className="text-xs text-slate-500">응시 토큰</p>
                  <p className="mt-1 font-mono text-xs text-slate-700 break-all">
                    {record?.login_token || "-"}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* ── 결과 대시보드 (배정 후 항상 표시) ── */}
          {isAssigned && (
            <Card className="border-slate-200">
              <CardHeader>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <CardTitle>시험 결과 대시보드</CardTitle>
                    <CardDescription>
                      제출 결과와 공개 상태를 관리합니다.
                    </CardDescription>
                  </div>

                  {record?.status === "graded" && (
                    <Button
                      type="button"
                      size="sm"
                      variant={record.summary_comment ? "outline" : "default"}
                      onClick={() => {
                        if (record.summary_comment) {
                          setAiReportOpen(true);
                        } else {
                          handleGenerateAIReport(record.record_id);
                        }
                      }}
                      disabled={aiReportLoading}
                      className="shrink-0 gap-2"
                    >
                      {aiReportLoading ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          생성 중...
                        </>
                      ) : (
                        <>
                          <Sparkles className="h-4 w-4" />
                          {record.summary_comment ? "AI 분석 보기" : "AI 리포트 생성"}
                        </>
                      )}
                    </Button>
                  )}
                </div>
              </CardHeader>

              <CardContent className="p-4 pt-0">
                <div className="grid grid-cols-1 gap-4 md:grid-cols-[1.1fr_0.9fr]">
                  <div className="rounded-xl bg-slate-50 p-4">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <p className="text-sm font-medium text-slate-700">
                          응시자에게 결과 공개
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                          공개 후 응시자 결과 화면에서 확인할 수 있습니다.
                        </p>
                      </div>

                      {record?.result_visible ? (
                        <Badge className="bg-emerald-100 text-emerald-700">
                          결과 공개 완료
                        </Badge>
                      ) : (
                        <Button
                          size="sm"
                          className="bg-sky-600 hover:bg-sky-700"
                          onClick={handlePublishResult}
                          disabled={!record || saving || record.status !== "graded"}
                        >
                          {saving ? (
                            <Loader2 className="size-4 mr-2 animate-spin" />
                          ) : (
                            <Send className="size-4 mr-2" />
                          )}
                          결과 공개 및 메일 발송
                        </Button>
                      )}
                    </div>

                    <div className="mt-4 grid grid-cols-2 gap-3">
                      <div className="rounded-lg bg-white px-3 py-2">
                        <p className="text-[11px] text-slate-500">제출일시</p>
                        <p className="mt-1 text-xs font-medium text-slate-900">
                          {formatKST(record?.submitted_at)}
                        </p>
                      </div>

                      <div className="rounded-lg bg-white px-3 py-2">
                        <p className="text-[11px] text-slate-500">응시 상태</p>
                        <p className="mt-1 text-xs font-medium text-slate-900">
                          {record?.status || "-"}
                        </p>
                      </div>

                      <div className="col-span-2 rounded-lg bg-white px-3 py-2">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-[11px] text-slate-500">화면 이탈 기록</p>
                          {(record?.violation_count ?? 0) >= 3 ? (
                            <Badge className="bg-rose-100 text-rose-700">
                              부정행위 불합격
                            </Badge>
                          ) : (record?.violation_count ?? 0) > 0 ? (
                            <Badge className="bg-amber-100 text-amber-700">
                              주의
                            </Badge>
                          ) : (
                            <Badge className="bg-slate-100 text-slate-600">
                              없음
                            </Badge>
                          )}
                        </div>

                        <p className="mt-1 text-xs font-medium text-slate-900">
                          위반 횟수: {record?.violation_count ?? 0}회
                          <span className="mx-2 text-slate-300">|</span>
                          사유: {violationReasonText}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-xl bg-slate-50 p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-medium text-slate-700">점수 요약</p>

                        {record?.total_score != null ? (
                          <>
                            <p className="mt-3 text-3xl font-bold text-slate-900">
                              {record.total_score}
                              <span className="ml-1 text-base font-normal text-slate-500">
                                점
                              </span>
                            </p>
                            <p className="mt-1 text-xs text-slate-500">
                              합격 기준 {gradedDiagnosis?.pass_score ?? 70}점
                            </p>
                          </>
                        ) : (
                          <p className="mt-3 text-sm text-slate-500">
                            아직 채점 결과가 없습니다.
                          </p>
                        )}
                      </div>

                      {record?.total_score != null && (
                        <Badge
                          className={
                            record.pass_yn
                              ? "bg-emerald-100 text-emerald-700"
                              : "bg-rose-100 text-rose-700"
                          }
                        >
                          {record.pass_yn ? "합격" : "불합격"}
                        </Badge>
                      )}
                    </div>

                    {record?.total_score != null && (
                      <div className="mt-4 h-2 rounded-full bg-slate-200">
                        <div
                          className={`h-2 rounded-full ${record.pass_yn ? "bg-emerald-500" : "bg-amber-500"
                            }`}
                          style={{
                            width: `${Math.min(Number(record.total_score || 0), 100)}%`,
                          }}
                        />
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* 문제별 상세 결과 */}
      {
        answers.length > 0 && (
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="text-lg">문제별 상세 결과</CardTitle>
              <CardDescription>문제를 클릭하면 정답과 상세 내용을 확인할 수 있습니다.</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>#</TableHead>
                    <TableHead>문제</TableHead>
                    <TableHead>역량</TableHead>
                    <TableHead>난이도</TableHead>
                    <TableHead>응답</TableHead>
                    <TableHead>정답 여부</TableHead>
                    <TableHead>점수</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {answers.map((ans, idx) => (
                    <TableRow
                      key={ans.answer_id}
                      className="cursor-pointer hover:bg-slate-50 transition-colors"
                      onClick={() => setSelectedAnswer(ans)}
                    >
                      <TableCell className="font-medium">{idx + 1}</TableCell>
                      <TableCell className="max-w-sm text-slate-700 text-sm">{ans.question_title}</TableCell>
                      <TableCell>
                        {ans.competency_type && (
                          <Badge variant="secondary" className="bg-sky-100 text-sky-700">{ans.competency_type}</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {ans.difficulty && (
                          <Badge
                            variant="secondary"
                            className={
                              ans.difficulty === "고급"
                                ? "bg-red-100 text-red-700"
                                : ans.difficulty === "중급"
                                  ? "bg-amber-100 text-amber-700"
                                  : "bg-green-100 text-green-700"
                            }
                          >
                            {ans.difficulty}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-slate-600 max-w-xs truncate" title={ans.answer_text || ""}>
                        {ans.answer_text || "-"}
                      </TableCell>
                      <TableCell>
                        {ans.is_correct != null ? (
                          <Badge
                            variant="secondary"
                            className={ans.is_correct ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}
                          >
                            {ans.is_correct ? "정답" : "오답"}
                          </Badge>
                        ) : (
                          <span className="text-slate-400 text-sm">-</span>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-slate-700">{ans.earned_score}점</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )
      }
      {/* AI 리포트 모달 */}
      <Dialog open={aiReportOpen} onOpenChange={setAiReportOpen}>
        <DialogContent className="w-[92vw] !max-w-5xl sm:!max-w-5xl">
          <DialogHeader>
            <div className="flex items-start justify-between gap-4">
              <div>
                <DialogTitle>AI 종합 진단 리포트</DialogTitle>
                <p className="mt-1 text-sm text-slate-500">
                  응시자의 정오답 패턴과 문제 내용을 기반으로 생성된 관리자용 AI 분석입니다.
                </p>
              </div>

              {record?.status === "graded" && (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => handleGenerateAIReport(record.record_id)}
                  disabled={aiReportLoading}
                  className="mr-8 shrink-0 gap-2"
                >
                  {aiReportLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      재생성 중...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4" />
                      리포트 재생성
                    </>
                  )}
                </Button>
              )}
            </div>
          </DialogHeader>

          {record?.summary_comment ? (
            <AIReportCard
              report={record.summary_comment}
              description="응시자의 정오답 패턴과 문제 내용을 기반으로 생성된 관리자용 AI 분석입니다."
            />
          ) : (
            <div className="rounded-lg bg-slate-50 p-4 text-sm text-slate-500">
              아직 생성된 AI 리포트가 없습니다.
            </div>
          )}
        </DialogContent>
      </Dialog>
      {/* 문제 상세 클릭 모달 */}
      <Dialog open={!!selectedAnswer} onOpenChange={(open) => !open && setSelectedAnswer(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>문제 상세 확인</DialogTitle>
          </DialogHeader>
          {selectedAnswer && (
            <div className="space-y-6 pt-4">
              <div className="flex items-start gap-3">
                <span className="flex-shrink-0 size-8 flex items-center justify-center rounded-full bg-sky-600 text-white text-sm font-bold">
                  {selectedAnswer.answer_id}
                </span>
                <div className="space-y-1">
                  <h3 className="text-base font-medium text-slate-800 leading-relaxed">{selectedAnswer.question_title}</h3>
                  <div className="flex items-center gap-2 mt-2">
                    {selectedAnswer.competency_type && (
                      <Badge variant="secondary" className="bg-sky-100 text-sky-700">{selectedAnswer.competency_type}</Badge>
                    )}
                    {selectedAnswer.difficulty && (
                      <Badge variant="secondary" className="bg-slate-100 text-slate-600">{selectedAnswer.difficulty}</Badge>
                    )}
                  </div>
                </div>
              </div>
              {selectedAnswer.question_type === "multiple_choice" && Array.isArray(selectedAnswer.choices_json) ? (
                <div className="space-y-2 border-t border-b border-slate-100 py-4">
                  <Label className="text-slate-500 mb-2 block">객관식 선택지 (단일 정답)</Label>
                  {selectedAnswer.choices_json.map((choice: string, i: number) => {
                    const isCorrect = String(selectedAnswer.correct_answer_json).startsWith(String(i + 1) + "번");
                    const isSelected = String(selectedAnswer.answer_text).startsWith(String(i + 1) + "번");

                    return (
                      <div key={i} className="flex items-center gap-2 bg-slate-50 p-2 rounded-lg">
                        <span className="size-7 flex-shrink-0 flex items-center justify-center rounded-full bg-slate-200 text-slate-600 text-sm font-medium">
                          {i + 1}
                        </span>
                        <span className="flex-1 text-sm text-slate-700">{choice}</span>
                        <div className="flex gap-2 text-xs font-bold">
                          {isCorrect && <span className="text-sky-600 bg-sky-100 px-2 py-1 rounded">정답체크</span>}
                          {isSelected && (
                            <span className={isCorrect ? "text-green-600 bg-green-100 px-2 py-1 rounded" : "text-red-600 bg-red-100 px-2 py-1 rounded"}>
                              응답체크
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4 border-t border-b border-slate-100 py-4">
                  <div className="space-y-2 p-4 bg-slate-50 rounded-lg">
                    <Label className="text-slate-500">응시자 답변</Label>
                    <p className="text-sm font-medium text-slate-800 break-words">{selectedAnswer.answer_text || "-"}</p>
                  </div>
                  <div className="space-y-2 p-4 bg-sky-50 rounded-lg">
                    <Label className="text-sky-700">모범 답안 (정답)</Label>
                    <p className="text-sm font-medium text-sky-900 break-words">{selectedAnswer.correct_answer_json ?? "-"}</p>
                  </div>
                </div>
              )}
              <div className="flex items-center justify-between bg-slate-50 p-4 rounded-lg">
                <span className="text-sm font-medium text-slate-700">채점 결과</span>
                <div className="flex items-center gap-3">
                  <Badge
                    variant="secondary"
                    className={selectedAnswer.is_correct ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}
                  >
                    {selectedAnswer.is_correct ? "정답" : "오답"}
                  </Badge>
                  <span className="text-sm font-bold text-slate-800">{selectedAnswer.earned_score}점 획득</span>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div >
  );
}
