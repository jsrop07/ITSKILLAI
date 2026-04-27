import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Label } from "../components/ui/label";
import { useNavigate } from "react-router";
import { Search, Filter, Eye, Plus, Loader2, X } from "lucide-react";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "../components/ui/table";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "../components/ui/select";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter,
} from "../components/ui/dialog";
import { applicantsApi, recordsApi, diagnosesApi } from "../../lib/api";
import type { Applicant, ApplicantCreate, Diagnosis } from "../../lib/types";
import { APPLICANT_STATUS_LABELS } from "../../lib/types";
type ApplicantWithResult = Applicant & {
  latest_score?: number | null;
  latest_pass_yn?: boolean | number | string | null;
};

export default function ApplicantManagement() {
  const navigate = useNavigate();
  const [applicants, setApplicants] = useState<ApplicantWithResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [showAdd, setShowAdd] = useState(false);
  const [diagnoses, setDiagnoses] = useState<Diagnosis[]>([]);

  // 응시자 추가 폼
  const [form, setForm] = useState<ApplicantCreate>({
    name: "", email: "", phone: "", target_role: "", experience_level: "", tech_stack: "",
  });
  const [assignDiagnosisId, setAssignDiagnosisId] = useState<string>("");
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (searchTerm) params.search = searchTerm;
      if (statusFilter !== "all") params.status = statusFilter;
      if (roleFilter !== "all") params.target_role = roleFilter;
      const data = await applicantsApi.list(params);
      setApplicants(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [searchTerm, roleFilter, statusFilter]);

  useEffect(() => {
    diagnosesApi.list({ status: "active" }).then(setDiagnoses).catch(console.error);
  }, []);

  const handleAdd = async () => {
    if (!form.name || !form.email) return alert("이름과 이메일은 필수입니다.");
    setSaving(true);
    try {
      const created = await applicantsApi.create(form);
      // 시험 배정 선택 시 Record 생성
      if (assignDiagnosisId) {
        await recordsApi.create({
          applicant_id: created.applicant_id,
          diagnosis_id: Number(assignDiagnosisId),
        });
      }
      setShowAdd(false);
      setForm({ name: "", email: "", phone: "", target_role: "", experience_level: "", tech_stack: "" });
      setAssignDiagnosisId("");
      load();
    } catch (err: any) {
      alert(err.response?.data?.detail || "추가 실패");
    } finally {
      setSaving(false);
    }
  };

  const statusColor: Record<string, string> = {
    completed: "bg-green-100 text-green-700",
    in_progress: "bg-blue-100 text-blue-700",
    ready: "bg-sky-100 text-sky-700",
    pending: "bg-slate-100 text-slate-700",
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">응시자 관리</h1>
          <p className="text-sm text-slate-500 mt-1">시험 응시자 조회 및 관리</p>
        </div>
        <Button className="bg-sky-600 hover:bg-sky-700" onClick={() => setShowAdd(true)}>
          <Plus className="size-4 mr-2" />
          응시자 추가
        </Button>
      </div>

      <Card className="border-slate-200">
        <CardHeader className="border-b border-slate-200">
          <div className="flex items-center gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-slate-400" />
              <Input
                placeholder="이름 또는 이메일로 검색..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={roleFilter} onValueChange={setRoleFilter}>
              <SelectTrigger className="w-48">
                <Filter className="size-4 mr-2" />
                <SelectValue placeholder="직무 필터" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">전체 직무</SelectItem>
                <SelectItem value="백엔드 개발자">백엔드 개발자</SelectItem>
                <SelectItem value="프론트엔드 개발자">프론트엔드 개발자</SelectItem>
                <SelectItem value="풀스택 개발자">풀스택 개발자</SelectItem>
                <SelectItem value="데이터 엔지니어">데이터 엔지니어</SelectItem>
                <SelectItem value="DevOps 엔지니어">DevOps 엔지니어</SelectItem>
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="상태 필터" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">전체 상태</SelectItem>
                <SelectItem value="pending">신청 완료</SelectItem>
                <SelectItem value="ready">시험 준비</SelectItem>
                <SelectItem value="in_progress">진행중</SelectItem>
                <SelectItem value="completed">완료</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex justify-center py-16">
              <Loader2 className="size-6 animate-spin text-sky-500" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>이름</TableHead>
                  <TableHead>이메일</TableHead>
                  <TableHead>목표 직무</TableHead>
                  <TableHead>경력</TableHead>
                  <TableHead>점수</TableHead>
                  <TableHead>결과</TableHead>
                  <TableHead>상태</TableHead>
                  <TableHead>신청일</TableHead>
                  <TableHead className="text-right">작업</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {applicants.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-slate-400 py-12">
                      응시자가 없습니다.
                    </TableCell>
                  </TableRow>
                ) : (
                  applicants.map((applicant) => (
                    <TableRow key={applicant.applicant_id} className="cursor-pointer hover:bg-slate-50 transition-colors" onClick={() => navigate(`/applicants/${applicant.applicant_id}`)}>
                      <TableCell className="font-medium">{applicant.name}</TableCell>
                      <TableCell className="text-slate-600">{applicant.email}</TableCell>
                      <TableCell>
                        {applicant.target_role && (
                          <Badge variant="secondary" className="bg-sky-100 text-sky-700">
                            {applicant.target_role}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-slate-600">{applicant.experience_level || "-"}</TableCell>
                      <TableCell>
                        {applicant.latest_score != null ? (
                          <span className="font-semibold text-slate-700">{applicant.latest_score}점</span>
                        ) : (
                          <span className="text-slate-400">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {applicant.latest_pass_yn != null ? (
                          <Badge
                            variant="secondary"
                            className={applicant.latest_pass_yn ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}
                          >
                            {applicant.latest_pass_yn ? "합격" : "불합격"}
                          </Badge>
                        ) : (
                          <span className="text-slate-400">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className={statusColor[applicant.status] || "bg-slate-100 text-slate-700"}
                        >
                          {APPLICANT_STATUS_LABELS[applicant.status]}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-slate-500 text-sm">
                        {applicant.created_at?.slice(0, 10)}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate(`/applicants/${applicant.applicant_id}`)}
                        >
                          <Eye className="size-4 mr-2" />
                          상세보기
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* 응시자 추가 Dialog */}
      <Dialog open={showAdd} onOpenChange={setShowAdd}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>응시자 추가</DialogTitle>
            <DialogDescription>새 응시자 정보를 입력하고 선택적으로 시험을 배정합니다.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>이름 *</Label>
                <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="홍길동" />
              </div>
              <div className="space-y-2">
                <Label>이메일 *</Label>
                <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="example@email.com" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>연락처</Label>
                <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="010-0000-0000" />
              </div>
              <div className="space-y-2">
                <Label>경력</Label>
                <Input value={form.experience_level} onChange={(e) => setForm({ ...form, experience_level: e.target.value })} placeholder="3년" />
              </div>
            </div>
            <div className="space-y-2">
              <Label>목표 직무</Label>
              <Select value={form.target_role} onValueChange={(v) => setForm({ ...form, target_role: v })}>
                <SelectTrigger>
                  <SelectValue placeholder="직무 선택" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="백엔드 개발자">백엔드 개발자</SelectItem>
                  <SelectItem value="프론트엔드 개발자">프론트엔드 개발자</SelectItem>
                  <SelectItem value="풀스택 개발자">풀스택 개발자</SelectItem>
                  <SelectItem value="데이터 엔지니어">데이터 엔지니어</SelectItem>
                  <SelectItem value="DevOps 엔지니어">DevOps 엔지니어</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>기술 스택</Label>
              <Input value={form.tech_stack} onChange={(e) => setForm({ ...form, tech_stack: e.target.value })} placeholder="Java, Spring Boot, MySQL" />
            </div>
            <div className="space-y-2 border-t pt-4">
              <Label>시험 배정 (선택)</Label>
              <Select value={assignDiagnosisId} onValueChange={setAssignDiagnosisId}>
                <SelectTrigger>
                  <SelectValue placeholder="배정할 시험 선택 (선택사항)" />
                </SelectTrigger>
                <SelectContent>
                  {diagnoses.map((d) => (
                    <SelectItem key={d.diagnosis_id} value={String(d.diagnosis_id)}>
                      {d.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAdd(false)}>취소</Button>
            <Button className="bg-sky-600 hover:bg-sky-700" onClick={handleAdd} disabled={saving}>
              {saving ? <Loader2 className="size-4 animate-spin mr-2" /> : null}
              추가
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
