import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Label } from "../components/ui/label";
import { Search, Plus, Edit, Trash2, Loader2 } from "lucide-react";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "../components/ui/table";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter,
} from "../components/ui/dialog";
import { Checkbox } from "../components/ui/checkbox";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "../components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { diagnosesApi } from "../../lib/api";
import type { Diagnosis, DiagnosisCreate } from "../../lib/types";
import { LEVEL_LABELS, STATUS_LABELS } from "../../lib/types";
import { useNavigate } from "react-router";

export default function ExamManagement() {
  const navigate = useNavigate();
  const [exams, setExams] = useState<Diagnosis[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [checkedIds, setCheckedIds] = useState<Set<number>>(new Set());
  const [activeTab, setActiveTab] = useState("active");
  const [page, setPage] = useState(1);
  const limit = 20;

  useEffect(() => {
    load();
  }, []);

  const load = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (searchTerm) params.search = searchTerm;
      const data = await diagnosesApi.list(params);
      setExams(data);
      setPage(1);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("정말 이 시험을 삭제하시겠습니까?")) return;
    try {
      await diagnosesApi.delete(id);
      load();
    } catch (err) {
      console.error(err);
      alert("삭제 불가 (할당된 기록이 있을 수 있습니다.)");
    }
  };

  const handleBulkDelete = async () => {
    if (checkedIds.size === 0) return alert("선택된 시험이 없습니다.");
    if (!window.confirm(`선택한 ${checkedIds.size}개 시험을 삭제하시겠습니까?`)) return;
    try {
      await Promise.all(Array.from(checkedIds).map(id => diagnosesApi.delete(id)));
      setCheckedIds(new Set());
      load();
    } catch (err) {
      alert("일부 시험 삭제 실패 (할당된 기록이 있을 수 있습니다.)");
      load();
    }
  };

  const handleBulkInactive = async () => {
    if (checkedIds.size === 0) return alert("선택된 시험이 없습니다.");
    if (!window.confirm(`선택한 ${checkedIds.size}개 시험을 비활성화하시겠습니까?`)) return;
    try {
      await Promise.all(Array.from(checkedIds).map(id => diagnosesApi.update(id, { status: "inactive" } as any)));
      setCheckedIds(new Set());
      load();
    } catch (err) {
      alert("일부 시험 비활성화 실패");
    }
  };

  const filteredExams = exams.filter((e) => {
    if (activeTab === "active") return e.status !== "inactive";
    if (activeTab === "inactive") return e.status === "inactive";
    return true;
  });

  const paginatedExams = filteredExams.slice((page - 1) * limit, page * limit);
  const totalPages = Math.ceil(filteredExams.length / limit) || 1;

  const allFilteredChecked = paginatedExams.length > 0 && paginatedExams.every(e => checkedIds.has(e.diagnosis_id));

  const toggleCheckAll = () => {
    const newKeys = new Set(checkedIds);
    if (allFilteredChecked) {
      paginatedExams.forEach(e => newKeys.delete(e.diagnosis_id));
    } else {
      paginatedExams.forEach(e => newKeys.add(e.diagnosis_id));
    }
    setCheckedIds(newKeys);
  };

  const toggleCheck = (id: number) => {
    const newKeys = new Set(checkedIds);
    if (newKeys.has(id)) newKeys.delete(id);
    else newKeys.add(id);
    setCheckedIds(newKeys);
  };

  const levelColor: Record<string, string> = {
    advanced: "bg-red-100 text-red-700",
    intermediate: "bg-amber-100 text-amber-700",
    beginner: "bg-green-100 text-green-700",
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">시험 관리</h1>
          <p className="text-sm text-slate-500 mt-1">시험 목록 조회 및 설정 관리</p>
        </div>
        <Button className="bg-sky-600 hover:bg-sky-700" onClick={() => navigate("/exams/new")}>
          <Plus className="size-4 mr-2" />
          시험 생성
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => { setActiveTab(v); setPage(1); setCheckedIds(new Set()); }}>
        <div className="flex items-center justify-between mb-4">
          <TabsList>
            <TabsTrigger value="active">활성 / 준비 중</TabsTrigger>
            <TabsTrigger value="inactive">비활성 (삭제 대기)</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="active" className="mt-0 space-y-4">
        </TabsContent>
        <TabsContent value="inactive" className="mt-0 space-y-4">
        </TabsContent>

        <Card className="border-slate-200">
          <CardHeader className="border-b border-slate-200">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-slate-400" />
              <Input
                placeholder="시험명 검색"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            {checkedIds.size > 0 && (
              <div className="flex items-center gap-2 mt-4 pt-4 border-t border-slate-100">
                <span className="text-sm font-medium text-sky-700">{checkedIds.size}개 선택됨</span>
                {activeTab === "active" && (
                  <Button variant="outline" size="sm" className="h-8 text-amber-600 hover:text-amber-700" onClick={handleBulkInactive}>
                    선택 비활성화
                  </Button>
                )}
                <Button variant="outline" size="sm" className="h-8 text-red-600 hover:text-red-700" onClick={handleBulkDelete}>
                  선택 영구 삭제
                </Button>
              </div>
            )}
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
                    <TableHead className="w-12">
                      <Checkbox checked={allFilteredChecked} onCheckedChange={toggleCheckAll} />
                    </TableHead>
                    <TableHead>시험명</TableHead>
                    {/* <TableHead>대상 직무</TableHead> */}
                    <TableHead>난이도</TableHead>
                    <TableHead>문제 수</TableHead>
                    <TableHead>제한 시간</TableHead>
                    <TableHead>합격 점수</TableHead>
                    <TableHead>상태</TableHead>
                    <TableHead>생성일</TableHead>
                    <TableHead className="text-right">작업</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedExams.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={10} className="text-center text-slate-400 py-12">
                        시험이 없습니다.
                      </TableCell>
                    </TableRow>
                  ) : (
                    paginatedExams.map((exam) => (
                      <TableRow
                        key={exam.diagnosis_id}
                        className="cursor-pointer hover:bg-slate-50 transition-colors"
                        onClick={() => navigate(`/exams/${exam.diagnosis_id}`)}
                      >
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          <Checkbox checked={checkedIds.has(exam.diagnosis_id)} onCheckedChange={() => toggleCheck(exam.diagnosis_id)} />
                        </TableCell>
                        <TableCell className="font-medium">{exam.title}</TableCell>
                        <TableCell>
                          <Badge variant="secondary" className={levelColor[exam.level]}>
                            {LEVEL_LABELS[exam.level]}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-slate-600">
                          {exam.question_idxs
                            ? exam.question_idxs.split(',').filter(x => x.trim() !== '').length
                            : exam.question_count}개
                        </TableCell>
                        <TableCell className="text-slate-600">{exam.duration_minutes}분</TableCell>
                        <TableCell className="text-slate-600">{exam.pass_score}점</TableCell>
                        <TableCell>
                          <Badge
                            variant="secondary"
                            className={
                              exam.status === "active"
                                ? "bg-green-100 text-green-700"
                                : exam.status === "draft"
                                  ? "bg-slate-100 text-slate-700"
                                  : "bg-red-100 text-red-700"
                            }
                          >
                            {STATUS_LABELS[exam.status]}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-slate-500 text-sm">
                          {exam.created_at?.slice(0, 10)}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="sm" className="text-sky-600 hover:text-sky-700 mr-1" onClick={(e) => { e.stopPropagation(); navigate(`/exams/${exam.diagnosis_id}`); }}>
                            <Edit className="size-4" />
                          </Button>
                          <Button variant="ghost" size="sm" className="text-red-600 hover:text-red-700" onClick={(e) => { e.stopPropagation(); handleDelete(exam.diagnosis_id); }}>
                            <Trash2 className="size-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            )}
            {!loading && filteredExams.length > 0 && (
              <div className="flex items-center justify-center gap-4 p-4 border-t border-slate-200">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                >
                  이전
                </Button>
                <span className="text-sm text-slate-600">
                  {page} / {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(Math.min(totalPages, page + 1))}
                  disabled={page === totalPages}
                >
                  다음
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </Tabs>
    </div>
  );
}
