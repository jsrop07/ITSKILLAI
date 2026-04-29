import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { useNavigate, useParams } from "react-router";
import { ArrowLeft, Award, Sparkles, Loader2, Save, Send } from "lucide-react";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "../components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "../components/ui/dialog";
import { Switch } from "../components/ui/switch";
import { applicantsApi, recordsApi, diagnosesApi } from "../../lib/api";
import type { Applicant, Record, AnswerDetail, Diagnosis } from "../../lib/types";

export default function ApplicantDetail() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();

  const [applicant, setApplicant] = useState<Applicant | null>(null);
  const [record, setRecord] = useState<Record | null>(null);
  const [answers, setAnswers] = useState<AnswerDetail[]>([]);
  const [gradedDiagnosis, setGradedDiagnosis] = useState<Diagnosis | null>(null);
  const [diagnoses, setDiagnoses] = useState<Diagnosis[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedAnswer, setSelectedAnswer] = useState<AnswerDetail | null>(null);

  const [form, setForm] = useState({
    name: "", email: "", phone: "", target_role: "", experience_level: "", tech_stack: "",
  });

  const [selectedDiagnosisId, setSelectedDiagnosisId] = useState<string>("");
  const [deadlineAt, setDeadlineAt] = useState<string>("");

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
          } catch (e) {}
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
      alert("시험이 배정되었습니다. (실제 환경에서는 이메일을 발송합니다)");
      loadData();
    } catch (err) {
      alert("배정 실패");
    } finally {
      setSaving(false);
    }
  };

  const handleToggleVisible = async (checked: boolean) => {
    if (!record) return;
    try {
      const updated = await recordsApi.update(record.record_id, { result_visible: checked } as any);
      setRecord(updated);
    } catch (err) {
      console.error(err);
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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* 좌: 기본 정보 */}
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle>응시자 기본 정보</CardTitle>
            <CardDescription>
              {isPending ? "시험지 배정 전까지 응시자 정보를 수정할 수 있습니다." : "시험이 배정되어 정보를 수정할 수 없습니다."}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>이름 *</Label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} disabled={!isPending} />
            </div>
            <div className="space-y-2">
              <Label>이메일 *</Label>
              <Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} disabled={!isPending} />
            </div>
            <div className="space-y-2">
              <Label>전화번호</Label>
              <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} disabled={!isPending} />
            </div>
            <div className="space-y-2">
              <Label>지원 직무</Label>
              <Input value={form.target_role} onChange={(e) => setForm({ ...form, target_role: e.target.value })} disabled={!isPending} />
            </div>
            <div className="space-y-2">
              <Label>경력 수준</Label>
              <Input value={form.experience_level} onChange={(e) => setForm({ ...form, experience_level: e.target.value })} disabled={!isPending} />
            </div>
            <div className="space-y-2">
              <Label>기술 스택</Label>
              <Input value={form.tech_stack} onChange={(e) => setForm({ ...form, tech_stack: e.target.value })} disabled={!isPending} />
            </div>
          </CardContent>
        </Card>

        {/* 우: 시험 배정 / 결과 대시보드 */}
        <div className="space-y-6">
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
            <Card className="border-sky-100 bg-sky-50">
              <CardHeader>
                <CardTitle className="text-sky-800 text-base">배정된 시험 정보</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">시험지</span>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-slate-800">{assignedDiagnosisName}</span>
                  </div>
                </div>
                {record.deadline_at && (
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">응시 마감일</span>
                    <span className="font-medium text-slate-800">
                      {new Date(record.deadline_at).toLocaleDateString("ko-KR")}
                    </span>
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">응시 토큰</span>
                  <code className="text-xs bg-white border border-slate-200 rounded px-2 py-0.5 font-mono text-slate-700">{record.login_token}</code>
                </div>
              </CardContent>
            </Card>
          )}

          {/* ── 결과 대시보드 (배정 후 항상 표시) ── */}
          {isAssigned && (
            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle>시험 결과 대시보드</CardTitle>
                <CardDescription>
                  {gradedDiagnosis ? `응시한 시험: ${gradedDiagnosis.title}` : "응시 완료된 시험 내역"}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {/* 결과 공개 토글 */}
                <div className="flex items-center justify-between mb-4 pb-4 border-b border-slate-100">
                  <div className="flex items-center gap-3">
                    <Label className="text-sm font-medium text-slate-700">응시자에게 결과 공개</Label>
                    <Switch
                      checked={record?.result_visible ?? false}
                      onCheckedChange={handleToggleVisible}
                      disabled={!record}
                    />
                  </div>
                  {record?.submitted_at && (
                    <p className="text-xs text-slate-500">
                      제출일시: {new Date(record.submitted_at).toLocaleString()}
                    </p>
                  )}
                </div>

                {/* 점수 표시 */}
                <div className="flex items-center justify-center">
                  {record && record.total_score != null ? (
                    <div className="text-center w-full">
                      <div className="inline-flex items-center justify-center size-24 rounded-full bg-gradient-to-br from-sky-100 to-sky-50 border-4 border-sky-200">
                        <div>
                          <p className="text-3xl font-bold text-sky-700">{record.total_score}</p>
                          <p className="text-xs text-sky-600">점</p>
                        </div>
                      </div>
                      <div className="mt-3">
                        <Badge
                          variant="secondary"
                          className={record.pass_yn ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}
                        >
                          {record.pass_yn ? "합격" : "불합격"}
                        </Badge>
                      </div>
                    </div>
                  ) : (
                    <div className="py-8 w-full text-center text-slate-400">
                      <Award className="size-10 mx-auto mb-3 opacity-40" />
                      <p>시험이 아직 진행되지 않았거나 채점 전입니다.</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* 역량 세부 분석 */}
          {Object.keys(competencies).length > 0 && (
            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle className="text-lg">역량 세부 분석</CardTitle>
                <CardDescription>각 역량 영역별 평가 결과 (%)</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {Object.entries(competencies).map(([name, score], idx) => (
                    <div key={idx} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-slate-700">{name}</p>
                        <p className="text-lg font-semibold text-slate-800">{score}%</p>
                      </div>
                      <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-sky-500 to-sky-400 rounded-full transition-all"
                          style={{ width: `${score}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* 문제별 상세 결과 */}
      {answers.length > 0 && (
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
                    <TableCell className="text-sm text-slate-600 max-w-xs">{ans.answer_text || "-"}</TableCell>
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
      )}

      {/* AI 분석 요약 */}
      {record?.summary_comment && (
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Sparkles className="size-5 text-violet-600" />
              AI 분석 요약
            </CardTitle>
            <CardDescription>LLM 기반 종합 평가</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-slate-700 leading-relaxed">{record.summary_comment}</p>
          </CardContent>
        </Card>
      )}

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
    </div>
  );
}
