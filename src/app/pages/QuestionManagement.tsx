import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Search, Plus, Eye, Edit, Trash2, Loader2, Save } from "lucide-react";
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
import { questionsApi } from "../../lib/api";
import type { Question, QuestionCreate } from "../../lib/types";
import { REVIEW_STATUS_LABELS, COMPETENCY_OPTIONS, getCompetencyLabel, AI_GENERATION_TYPE_LABELS } from "../../lib/types";

const formatDate = (dateStr?: string) => {
  if (!dateStr) return "-";
  try {
    const d = new Date(dateStr);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  } catch {
    return "-";
  }
};

type QuestionUpdate = Partial<QuestionCreate> & {
  review_status?: "pending" | "approved" | "rejected";
};

const getGenerationBadgeClass = (type?: string | null) => {
  switch (type) {
    case "rag":
      return "bg-indigo-100 text-indigo-700 border-indigo-200";
    case "general_graph":
      return "bg-cyan-100 text-cyan-700 border-cyan-200";
    case "manual":
      return "bg-slate-100 text-slate-700 border-slate-200";
    default:
      return "bg-amber-100 text-amber-700 border-amber-200";
  }
};

const typeColor: Record<string, string> = {
  multiple_choice: "bg-blue-100 text-blue-700 border-blue-200",
  essay: "bg-emerald-100 text-emerald-700 border-emerald-200",
  coding: "bg-orange-100 text-orange-700 border-orange-200",
};

const difficultyColor: Record<string, string> = {
  초급: "bg-green-100 text-green-700 border-green-200",
  중급: "bg-amber-100 text-amber-700 border-amber-200",
  고급: "bg-red-100 text-red-700 border-red-200",
};

const QUESTION_TYPE_LABELS: Record<string, string> = {
  multiple_choice: "객관식",
  essay: "서술형",
  coding: "코드작성형",
};

const SOURCE_TYPE_LABELS: Record<string, string> = {
  manual: "수동 작성",
  ai: "AI 생성",
};

export default function QuestionManagement() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [reviewFilter, setReviewFilter] = useState("all");
  const [difficultyFilter, setDifficultyFilter] = useState("all");
  const [competencyFilter, setCompetencyFilter] = useState("");
  const [aiGenerationFilter, setAiGenerationFilter] = useState("all");
  const [page, setPage] = useState(1);
  const limit = 20;

  const [checkedIds, setCheckedIds] = useState<Set<number>>(new Set());

  const [selectedQuestion, setSelectedQuestion] = useState<Question | null>(null);
  const [editForm, setEditForm] = useState<QuestionUpdate | null>(null);
  const [isEditing, setIsEditing] = useState(false);

  const [showCreate, setShowCreate] = useState(false);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState<QuestionCreate>({
    title: "",
    body: "",
    question_type: "multiple_choice",
    source_type: "manual",
    difficulty: "중급",
    competency_type: "",
    score: 1,
    choices_json: ["", "", "", "", ""],
    answer_json: 1,
    explanation: "",
  });

  const load = async () => {
    setLoading(true);

    try {
      const params: any = {};

      if (searchTerm) params.search = searchTerm;
      if (typeFilter !== "all") params.question_type = typeFilter;
      if (sourceFilter !== "all") params.source_type = sourceFilter;
      if (reviewFilter !== "all") params.review_status = reviewFilter;
      if (difficultyFilter !== "all") params.difficulty = difficultyFilter;
      if (competencyFilter) params.competency_type = competencyFilter;
      if (aiGenerationFilter !== "all") params.ai_generation_type = aiGenerationFilter;

      console.log("문제 목록 요청 params:", params);

      const data = await questionsApi.list(params);

      console.log("문제 목록 응답:", data);

      setQuestions(Array.isArray(data) ? data : []);
      setPage(1);
    } catch (err: any) {
      console.error("문제 목록 조회 실패:", err);
      console.error("백엔드 응답:", err.response?.data);
      setQuestions([]);
      alert(err.response?.data?.detail || "문제 목록을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [searchTerm, typeFilter, sourceFilter, reviewFilter, difficultyFilter, competencyFilter, aiGenerationFilter]);

  const handleCreate = async () => {
    if (!form.title) return alert("문제 제목은 필수입니다.");
    setSaving(true);
    try {
      await questionsApi.create(form);
      setShowCreate(false);
      setForm({ title: "", body: "", question_type: "multiple_choice", source_type: "manual", difficulty: "중급", competency_type: "", score: 1, choices_json: ["", "", "", "", ""], answer_json: 1, explanation: "" });
      load();
    } catch (err: any) {
      alert(err.response?.data?.detail || "생성 실패");
    } finally {
      setSaving(false);
    }
  };

  const handleApprove = async (q: Question) => {
    try {
      await questionsApi.update(q.question_id, { review_status: "approved" } as any);
      load();
    } catch (err) { console.error(err); }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("정말 이 문제를 삭제하시겠습니까?")) return;
    try {
      await questionsApi.delete(id);
      setSelectedQuestion(null);
      load();
    } catch (err) {
      console.error(err);
      alert("삭제 불가 (시험에 포함된 문제일 수 있습니다.)");
    }
  };

  const handleBulkDelete = async () => {
    if (checkedIds.size === 0) return alert("선택된 항목이 없습니다.");
    if (!window.confirm(`선택한 ${checkedIds.size}개 항목을 삭제하시겠습니까?`)) return;
    try {
      await Promise.all(Array.from(checkedIds).map(id => questionsApi.delete(id)));
      setCheckedIds(new Set());
      load();
    } catch (err) {
      alert("일부 항목 삭제 실패");
    }
  };

  const handleBulkApprove = async () => {
    if (checkedIds.size === 0) return alert("선택된 항목이 없습니다.");
    if (!window.confirm(`선택한 ${checkedIds.size}개 항목을 승인하시겠습니까?`)) return;
    try {
      await Promise.all(Array.from(checkedIds).map(id => questionsApi.update(id, { review_status: "approved" } as any)));
      setCheckedIds(new Set());
      load();
    } catch (err) {
      alert("일부 항목 승인 실패");
    }
  };

  const openDetail = (q: Question) => {
    setSelectedQuestion(q);
    setEditForm({
      title: q.title,
      body: q.body,
      question_type: q.question_type as any,
      difficulty: q.difficulty,
      competency_type: q.competency_type,
      score: q.score,
      choices_json: Array.isArray(q.choices_json)
        ? q.choices_json
        : typeof q.choices_json === "string"
          ? JSON.parse(q.choices_json || "[]")
          : ["", "", "", "", ""],
      answer_json: Number(q.answer_json || 1),
      explanation: q.explanation,
    });
    setIsEditing(false);
  };

  const handleUpdate = async () => {
    if (!selectedQuestion || !editForm?.title) return alert("제목은 필수입니다.");
    setSaving(true);
    try {
      await questionsApi.update(selectedQuestion.question_id, editForm as any);
      alert("문제가 수정되었습니다.");
      setSelectedQuestion(null);
      load();
    } catch (err) {
      console.error(err);
      alert("수정 실패");
    } finally {
      setSaving(false);
    }
  };

  const difficultyColor: Record<string, string> = {
    고급: "bg-red-100 text-red-700",
    중급: "bg-amber-100 text-amber-700",
    초급: "bg-green-100 text-green-700",
  };

  const paginatedQuestions = questions.slice((page - 1) * limit, page * limit);
  const totalPages = Math.ceil(questions.length / limit) || 1;

  const allFilteredChecked = paginatedQuestions.length > 0 && paginatedQuestions.every(q => checkedIds.has(q.question_id));

  const toggleCheckAll = () => {
    const newKeys = new Set(checkedIds);
    if (allFilteredChecked) {
      paginatedQuestions.forEach(q => newKeys.delete(q.question_id));
    } else {
      paginatedQuestions.forEach(q => newKeys.add(q.question_id));
    }
    setCheckedIds(newKeys);
  };

  const toggleCheck = (id: number) => {
    const newKeys = new Set(checkedIds);
    if (newKeys.has(id)) newKeys.delete(id);
    else newKeys.add(id);
    setCheckedIds(newKeys);
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">문제 관리</h1>
          <p className="text-sm text-slate-500 mt-1">전체 문제 목록 조회 및 관리</p>
        </div>
        <Button className="bg-sky-600 hover:bg-sky-700" onClick={() => setShowCreate(true)}>
          <Plus className="size-4 mr-2" />
          문제 추가
        </Button>
      </div>

      <Card className="border-slate-200">
        <CardHeader className="border-b border-slate-200">
          <div className="flex items-center gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-slate-400" />
              <Input
                placeholder="문제 내용으로 검색..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select
              value={competencyFilter || "all"}
              onValueChange={(value) => setCompetencyFilter(value === "all" ? "" : value)}
            >
              <SelectTrigger className="w-40">
                <SelectValue placeholder="역량" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">전체 역량</SelectItem>
                {COMPETENCY_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-32"><SelectValue placeholder="유형" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">전체 유형</SelectItem>
                <SelectItem value="multiple_choice">객관식</SelectItem>
                <SelectItem value="essay">서술형</SelectItem>
                <SelectItem value="coding">코드작성형</SelectItem>
              </SelectContent>
            </Select>
            <Select value={difficultyFilter} onValueChange={setDifficultyFilter}>
              <SelectTrigger className="w-30"><SelectValue placeholder="난이도" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">난이도</SelectItem>
                <SelectItem value="초급">초급</SelectItem>
                <SelectItem value="중급">중급</SelectItem>
                <SelectItem value="고급">고급</SelectItem>
              </SelectContent>
            </Select>
            <Select value={sourceFilter} onValueChange={setSourceFilter}>
              <SelectTrigger className="w-32"><SelectValue placeholder="출처" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">전체 출처</SelectItem>
                <SelectItem value="ai">AI 생성</SelectItem>
                <SelectItem value="manual">수동 작성</SelectItem>
              </SelectContent>
            </Select>
            <Select value={aiGenerationFilter} onValueChange={setAiGenerationFilter}>
              <SelectTrigger className="w-40"><SelectValue placeholder="생성 방식" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">생성 방식</SelectItem>
                <SelectItem value="general_graph">설계서 기반</SelectItem>
                <SelectItem value="rag">문서 기반 RAG</SelectItem>
              </SelectContent>
            </Select>
            <Select value={reviewFilter} onValueChange={setReviewFilter}>
              <SelectTrigger className="w-32"><SelectValue placeholder="상태" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">전체 상태</SelectItem>
                <SelectItem value="pending">검토 대기</SelectItem>
                <SelectItem value="approved">승인</SelectItem>
                <SelectItem value="rejected">반려</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {checkedIds.size > 0 && (
            <div className="flex items-center gap-2 mt-4 pt-4 border-t border-slate-100">
              <span className="text-sm font-medium text-sky-700">{checkedIds.size}개 선택됨</span>
              <Button variant="outline" size="sm" className="h-8 text-green-700 hover:text-green-800" onClick={handleBulkApprove}>
                선택 승인
              </Button>
              <Button variant="outline" size="sm" className="h-8 text-red-600 hover:text-red-700" onClick={handleBulkDelete}>
                선택 삭제
              </Button>
            </div>
          )}
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex justify-center py-16"><Loader2 className="size-6 animate-spin text-sky-500" /></div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">
                    <Checkbox checked={allFilteredChecked} onCheckedChange={toggleCheckAll} />
                  </TableHead>
                  <TableHead className="w-12">#</TableHead>
                  <TableHead>문제</TableHead>
                  <TableHead>유형</TableHead>
                  <TableHead>난이도</TableHead>
                  <TableHead>역량</TableHead>
                  <TableHead>출처</TableHead>
                  <TableHead>생성 방식</TableHead>
                  <TableHead>검토 상태</TableHead>
                  <TableHead>점수</TableHead>
                  <TableHead>생성일시</TableHead>
                  <TableHead className="text-right">작업</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {questions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={12} className="text-center text-slate-400 py-12">문제가 없습니다.</TableCell>
                  </TableRow>
                ) : (
                  paginatedQuestions.map((q, idx) => (
                    <TableRow key={q.question_id}>
                      <TableCell>
                        <Checkbox checked={checkedIds.has(q.question_id)} onCheckedChange={() => toggleCheck(q.question_id)} />
                      </TableCell>
                      <TableCell className="text-slate-500 text-sm">{(page - 1) * limit + idx + 1}</TableCell>
                      <TableCell className="max-w-xs">
                        <p className="text-slate-700 text-sm truncate">{q.title}</p>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className={typeColor[q.question_type] || "bg-slate-100 text-slate-700"}>
                          {QUESTION_TYPE_LABELS[q.question_type] || q.question_type}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {q.difficulty && (
                          <Badge variant="secondary" className={difficultyColor[q.difficulty] || "bg-slate-100 text-slate-700"}>
                            {q.difficulty}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {q.competency_type && (
                          <Badge variant="secondary" className="bg-sky-100 text-sky-700">{getCompetencyLabel(q.competency_type)}</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className={q.source_type === "ai" ? "bg-violet-100 text-violet-700" : "bg-slate-100 text-slate-700"}>
                          {SOURCE_TYPE_LABELS[q.source_type]}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={`${getGenerationBadgeClass(q.ai_generation_type)} text-xs font-medium border`}>
                          {q.ai_generation_type ? AI_GENERATION_TYPE_LABELS[q.ai_generation_type] : "-"}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className={
                            q.review_status === "approved" ? "bg-green-100 text-green-700"
                              : q.review_status === "rejected" ? "bg-red-100 text-red-700"
                                : "bg-amber-100 text-amber-700"
                          }
                        >
                          {REVIEW_STATUS_LABELS[q.review_status]}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-slate-600 font-medium">{q.score}점</TableCell>
                      <TableCell className="text-sm text-slate-900 font-medium">{formatDate(q.created_at)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button variant="ghost" size="sm" onClick={() => openDetail(q)}>
                            <Edit className="size-4 mr-1" />수정/상세
                          </Button>
                          {q.review_status === "pending" && (
                            <Button variant="ghost" size="sm" className="text-green-600" onClick={() => handleApprove(q)}>
                              승인
                            </Button>
                          )}
                          <Button variant="ghost" size="sm" className="text-red-500 hover:text-red-700" onClick={() => handleDelete(q.question_id)}>
                            <Trash2 className="size-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
          {!loading && questions.length > 0 && (
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

      {/* 문제 상세 / 수정 Dialog */}
      <Dialog open={selectedQuestion !== null} onOpenChange={() => setSelectedQuestion(null)}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>문제 수정</DialogTitle>
            <DialogDescription>문제를 수정하거나 내용을 확인할 수 있습니다.</DialogDescription>
          </DialogHeader>
          {editForm && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>문제 제목 *</Label>
                <Textarea value={editForm.title} onChange={(e) => setEditForm({ ...editForm, title: e.target.value })} rows={2} />
              </div>
              <div className="space-y-2">
                <Label>문제 본문</Label>

                {!isEditing ? (
                  <div className="max-h-[70vh] overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-5 text-[15px] leading-7 text-slate-900 whitespace-pre-wrap font-mono">
                    {editForm.body || "-"}
                  </div>
                ) : (
                  <Textarea
                    value={editForm.body}
                    onChange={(e) => setEditForm({ ...editForm, body: e.target.value })}
                    rows={12}
                    className="font-mono text-sm leading-6"
                  />
                )}
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>문제 유형</Label>
                  <Select
                    value={editForm.question_type}
                    onValueChange={(v) => setEditForm({ ...editForm, question_type: v as "multiple_choice" | "essay" | "coding", })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">전체 유형</SelectItem>
                      <SelectItem value="multiple_choice">객관식</SelectItem>
                      <SelectItem value="essay">서술형</SelectItem>
                      <SelectItem value="coding">코드작성형</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>난이도</Label>
                  <Select value={editForm.difficulty} onValueChange={(v) => setEditForm({ ...editForm, difficulty: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="초급">초급</SelectItem>
                      <SelectItem value="중급">중급</SelectItem>
                      <SelectItem value="고급">고급</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>역량 분류</Label>
                  <Select
                    value={editForm.competency_type || ""}
                    onValueChange={(v) => setEditForm({ ...editForm, competency_type: v })}
                  >
                    <SelectTrigger><SelectValue placeholder="역량 선택" /></SelectTrigger>
                    <SelectContent>
                      {COMPETENCY_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>점수</Label>
                  <Input type="number" value={editForm.score} onChange={(e) => setEditForm({ ...editForm, score: Number(e.target.value) })} min={1} />
                </div>
              </div>

              {editForm.question_type === "multiple_choice" && (
                <div className="space-y-2">
                  <Label>객관식 선택지 (단일 정답)</Label>
                  {((editForm.choices_json as string[]) || ["", "", "", "", ""]).map((c: string, i: number) => (
                    <div key={i} className="flex items-center gap-2">
                      <span className="size-7 flex-shrink-0 flex items-center justify-center rounded-full bg-slate-100 text-slate-600 text-sm font-medium">
                        {i + 1}
                      </span>
                      <Textarea
                        value={c}
                        onChange={(e) => {
                          const updated = [...((editForm.choices_json as string[]) || ["", "", "", "", ""])];
                          updated[i] = e.target.value;
                          setEditForm({ ...editForm, choices_json: updated });
                        }}
                        rows={2}
                        className="text-sm leading-6 resize-none"
                      />
                      <label className="flex items-center gap-1 cursor-pointer">
                        <input
                          type="radio"
                          name="edit-answer"
                          className="size-4"
                          checked={Number(editForm.answer_json) === i + 1}
                          onChange={() => setEditForm({ ...editForm, answer_json: i + 1 })}
                        />
                        <span className={`text-sm ml-1 ${Number(editForm.answer_json) === i + 1 ? "text-green-600 font-bold" : "text-slate-500"}`}>
                          정답체크
                        </span>
                      </label>
                    </div>
                  ))}
                </div>
              )}
              {(editForm.question_type === "essay" || editForm.question_type === "coding") && (
                <div className="space-y-2">
                  <Label>
                    {editForm.question_type === "coding" ? "예시 코드 / 풀이 방향" : "모범답안"}
                  </Label>
                  <Input
                    value={editForm.answer_json || ""}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        answer_json: e.target.value,
                      })
                    }
                    placeholder="정답 입력"
                  />
                </div>
              )}
              <div className="space-y-2">
                <Label>해설</Label>
                <Textarea
                  value={editForm.explanation}
                  onChange={(e) => setEditForm({ ...editForm, explanation: e.target.value })}
                  rows={5}
                  className="text-sm leading-6"
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedQuestion(null)}>
              닫기
            </Button>

            {selectedQuestion && !isEditing && (
              <Button
                variant="outline"
                onClick={() => setIsEditing(true)}
              >
                <Edit className="size-4 mr-2" />
                수정
              </Button>
            )}

            {selectedQuestion && isEditing && (
              <Button
                className="bg-sky-600 hover:bg-sky-700"
                onClick={handleUpdate}
                disabled={saving}
              >
                {saving ? (
                  <Loader2 className="size-4 animate-spin mr-2" />
                ) : (
                  <Save className="size-4 mr-2" />
                )}
                저장
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 문제 추가 Dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>문제 추가</DialogTitle>
            <DialogDescription>새 문제를 등록합니다.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>문제 제목 *</Label>
              <Textarea value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="문제를 입력하세요" rows={2} />
            </div>
            <div className="space-y-2">
              <Label>문제 본문</Label>
              <Textarea
                value={form.body}
                onChange={(e) => setForm({ ...form, body: e.target.value })}
                placeholder="코드 예시, SQL 쿼리, 실행 계획, 추가 설명 등을 입력하세요."
                rows={10}
                className="font-mono text-sm leading-6"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>문제 유형</Label>
                <Select
                  value={form.question_type}
                  onValueChange={(v) => setForm({ ...form, question_type: v as "multiple_choice" | "essay" | "coding", })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">전체 유형</SelectItem>
                    <SelectItem value="multiple_choice">객관식</SelectItem>
                    <SelectItem value="essay">서술형</SelectItem>
                    <SelectItem value="coding">코드작성형</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>난이도</Label>
                <Select value={form.difficulty} onValueChange={(v) => setForm({ ...form, difficulty: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="초급">초급</SelectItem>
                    <SelectItem value="중급">중급</SelectItem>
                    <SelectItem value="고급">고급</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>역량 분류</Label>
                <Select
                  value={form.competency_type || ""}
                  onValueChange={(v) => setForm({ ...form, competency_type: v })}
                >
                  <SelectTrigger><SelectValue placeholder="역량 선택" /></SelectTrigger>
                  <SelectContent>
                    {COMPETENCY_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>점수</Label>
                <Input type="number" value={form.score} onChange={(e) => setForm({ ...form, score: Number(e.target.value) })} min={1} />
              </div>
            </div>
            {form.question_type === "multiple_choice" && (
              <div className="space-y-2">
                <Label>객관식 선택지 (단일 정답)</Label>
                {((form.choices_json as string[]) || ["", "", "", "", ""]).map((c: string, i: number) => (
                  <div key={i} className="flex items-center gap-2">
                    <span className="size-7 flex-shrink-0 flex items-center justify-center rounded-full bg-slate-100 text-slate-600 text-sm font-medium">
                      {i + 1}
                    </span>
                    <Input
                      value={c}
                      onChange={(e) => {
                        const updated = [...((form.choices_json as string[]) || ["", "", "", "", ""])];
                        updated[i] = e.target.value;
                        setForm({ ...form, choices_json: updated });
                      }}
                      placeholder={`선택지 ${i + 1}`}
                    />
                    <label className="flex items-center gap-1 cursor-pointer">
                      <input
                        type="radio"
                        name="create-answer"
                        className="size-4"
                        checked={Number(form.answer_json) === i + 1}
                        onChange={() => setForm({ ...form, answer_json: i + 1 })}
                      />
                      <span className={`text-sm ml-1 ${Number(form.answer_json) === i + 1 ? "text-green-600 font-bold" : "text-slate-500"}`}>
                        정답체크
                      </span>
                    </label>
                  </div>
                ))}
              </div>
            )}
            {(form.question_type === "essay" || form.question_type === "coding") && (
              <div className="space-y-2">
                <Label>
                  {form.question_type === "coding" ? "예시 코드 / 풀이 방향" : "모범답안"}
                </Label>
                <Input
                  value={form.answer_json || ""}
                  onChange={(e) => setForm({ ...form, answer_json: e.target.value })}
                  placeholder="정답 입력"
                />
              </div>
            )}
            <div className="space-y-2">
              <Label>해설</Label>
              <Textarea value={form.explanation} onChange={(e) => setForm({ ...form, explanation: e.target.value })} placeholder="정답 해설" rows={3} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreate(false)}>취소</Button>
            <Button className="bg-sky-600 hover:bg-sky-700" onClick={handleCreate} disabled={saving}>
              {saving ? <Loader2 className="size-4 animate-spin mr-2" /> : null}
              등록
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
