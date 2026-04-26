import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Checkbox } from "../components/ui/checkbox";
import { Badge } from "../components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { ArrowLeft, Search, Plus, Trash2, Save, Loader2 } from "lucide-react";
import { diagnosesApi, questionsApi } from "../../lib/api";
import type { DiagnosisCreate, Question } from "../../lib/types";
import { LEVEL_LABELS } from "../../lib/types";

export default function ExamForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEdit = Boolean(id);

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // Form State
  const [form, setForm] = useState<DiagnosisCreate>({
    title: "",
    description: "",
    target_role: "",
    level: "intermediate",
    duration_minutes: 60,
    pass_score: 70,
    status: "draft",
  });

  // Questions State
  const [allQuestions, setAllQuestions] = useState<Question[]>([]);
  const [selectedQuestions, setSelectedQuestions] = useState<Question[]>([]); // The applied questions
  const [checkedIds, setCheckedIds] = useState<Set<number>>(new Set()); // For the pool table

  // Filters for pool
  const [searchTerm, setSearchTerm] = useState("");
  const [difficultyFilter, setDifficultyFilter] = useState("all");

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const qList = await questionsApi.list();
        setAllQuestions(qList);

        if (isEdit) {
          const diag = await diagnosesApi.get(Number(id));
          setForm({
            title: diag.title,
            description: diag.description || "",
            target_role: diag.target_role || "",
            level: diag.level,
            duration_minutes: diag.duration_minutes,
            pass_score: diag.pass_score,
            status: diag.status,
          });

          const dqList = await diagnosesApi.getQuestions(Number(id));
          // map dqList to Questions based on qList
          const selected = dqList.map(dq => {
            const match = qList.find(q => q.question_id === dq.question_id);
            return match;
          }).filter(Boolean) as Question[];
          setSelectedQuestions(selected);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [id, isEdit]);

  const handleApplyChecked = () => {
    const toAdd = allQuestions.filter(q => checkedIds.has(q.question_id) && !selectedQuestions.some(sq => sq.question_id === q.question_id));
    if (toAdd.length === 0) return alert("이미 적용되었거나 선택된 문제가 없습니다.");
    setSelectedQuestions([...selectedQuestions, ...toAdd]);
    setCheckedIds(new Set()); // clear selection
  };

  const handleRemoveApplied = (qId: number) => {
    setSelectedQuestions(selectedQuestions.filter(q => q.question_id !== qId));
  };

  const handleSave = async () => {
    if (!form.title) return alert("시험명은 필수입니다.");
    setSaving(true);
    try {
      const question_idxs = selectedQuestions.map(q => q.question_id).join(",");
      const payload = { ...form, question_idxs };

      if (isEdit) {
        await diagnosesApi.update(Number(id), payload as any);
      } else {
        await diagnosesApi.create(payload);
      }
      alert("저장되었습니다.");
      navigate("/exams");
    } catch (err: any) {
      alert(err.response?.data?.detail || "저장 실패");
    } finally {
      setSaving(false);
    }
  };

  const filteredPool = allQuestions.filter(q => {
    if (searchTerm && !q.title.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    if (difficultyFilter !== "all" && q.difficulty !== difficultyFilter) return false;
    // hide already selected?
    // if (selectedQuestions.some(sq => sq.question_id === q.question_id)) return false;
    return true;
  });

  const allFilteredChecked = filteredPool.length > 0 && filteredPool.every(q => checkedIds.has(q.question_id));

  const toggleCheckAll = () => {
    const newKeys = new Set(checkedIds);
    if (allFilteredChecked) {
      filteredPool.forEach(q => newKeys.delete(q.question_id));
    } else {
      filteredPool.forEach(q => newKeys.add(q.question_id));
    }
    setCheckedIds(newKeys);
  };

  const toggleCheck = (id: number) => {
    const newKeys = new Set(checkedIds);
    if (newKeys.has(id)) newKeys.delete(id);
    else newKeys.add(id);
    setCheckedIds(newKeys);
  };

  const difficultyColor: Record<string, string> = {
    고급: "bg-red-100 text-red-700",
    중급: "bg-amber-100 text-amber-700",
    초급: "bg-green-100 text-green-700",
  };

  if (loading) {
    return <div className="p-8 flex justify-center py-16"><Loader2 className="size-6 animate-spin text-sky-500" /></div>;
  }

  const totalScore = selectedQuestions.reduce((acc, q) => acc + (q.score || 0), 0);

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/exams")}>
          <ArrowLeft className="size-5" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-semibold text-slate-800">{isEdit ? "시험 수정" : "시험 생성"}</h1>
          <p className="text-sm text-slate-500 mt-1">시험의 기본 정보와 구성 문제를 관리합니다.</p>
        </div>
        <Button className="bg-sky-600 hover:bg-sky-700 w-24" onClick={handleSave} disabled={saving}>
          {saving ? <Loader2 className="size-4 animate-spin mr-2" /> : <Save className="size-4 mr-2" />}
          저장
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="xl:col-span-1 space-y-6">
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle>기본 정보</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>시험명 *</Label>
                <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="예: Spring Boot 심화" />
              </div>
              <div className="space-y-2">
                <Label>설명</Label>
                <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="시험 설명" />
              </div>
              <div className="space-y-2">
                <Label>대상 직무</Label>
                <Select value={form.target_role} onValueChange={(v) => setForm({ ...form, target_role: v })}>
                  <SelectTrigger><SelectValue placeholder="직무 선택" /></SelectTrigger>
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
                <Label>난이도</Label>
                <Select value={form.level} onValueChange={(v: any) => setForm({ ...form, level: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="beginner">초급</SelectItem>
                    <SelectItem value="intermediate">중급</SelectItem>
                    <SelectItem value="advanced">고급</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>제한 시간 (분)</Label>
                <Input type="number" value={form.duration_minutes} onChange={(e) => setForm({ ...form, duration_minutes: Number(e.target.value) })} />
              </div>
              <div className="space-y-2">
                <Label>합격 기준 (%)</Label>
                <Input type="number" value={form.pass_score} onChange={(e) => setForm({ ...form, pass_score: Number(e.target.value) })} />
              </div>
              <div className="space-y-2">
                <Label>활성화 상태</Label>
                <Select value={form.status} onValueChange={(v: any) => setForm({ ...form, status: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="draft">준비 중(Draft)</SelectItem>
                    <SelectItem value="active">활성</SelectItem>
                    <SelectItem value="inactive">비활성</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="xl:col-span-2 space-y-6">
          <Card className="border-slate-200">
            <CardHeader className="flex flex-row justify-between items-center bg-slate-50 border-b pb-4 pt-4">
              <div>
                <CardTitle>적용된 문제 목록</CardTitle>
                <CardDescription>현재 시험에 포함될 문제들입니다. ({selectedQuestions.length}개 / 자동 총점: {totalScore}점)</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {selectedQuestions.length === 0 ? (
                <div className="text-center py-8 text-slate-400 text-sm">아래 문제 리스트에서 문제를 선택한 뒤 "적용하기"를 눌러 추가하세요.</div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>#</TableHead>
                      <TableHead>문제명</TableHead>
                      <TableHead>난이도</TableHead>
                      <TableHead>점수</TableHead>
                      <TableHead className="text-right">제거</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {selectedQuestions.map((q, idx) => (
                      <TableRow key={`sq-${q.question_id}`}>
                        <TableCell className="text-slate-500">{idx + 1}</TableCell>
                        <TableCell className="max-w-[200px] truncate" title={q.title}>{q.title}</TableCell>
                        <TableCell>
                          <Badge variant="secondary" className={difficultyColor[q.difficulty || ""] || "bg-slate-100"}>{q.difficulty}</Badge>
                        </TableCell>
                        <TableCell>{q.score}점</TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="sm" className="text-red-600 hover:text-red-700" onClick={() => handleRemoveApplied(q.question_id)}>
                            <Trash2 className="size-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          <Card className="border-slate-200">
            <CardHeader className="flex flex-row justify-between items-center border-b pb-4 pt-4">
              <div>
                <CardTitle>전체 문제 검색</CardTitle>
                <CardDescription>체크박스로 문제를 선택하고 위 "적용된 문제 목록"에 추가하세요.</CardDescription>
              </div>
              <div className="flex gap-2 items-center">
                <Button variant="secondary" className="bg-sky-100 text-sky-700 hover:bg-sky-200" onClick={handleApplyChecked}>
                  <Plus className="size-4 mr-2" />
                  선택 {checkedIds.size}개 적용하기
                </Button>
              </div>
            </CardHeader>
            <div className="p-4 flex gap-4 bg-slate-50 border-b">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-slate-400" />
                <Input
                  className="pl-9 bg-white"
                  placeholder="제목으로 문제 검색..."
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                />
              </div>
              <Select value={difficultyFilter} onValueChange={setDifficultyFilter}>
                <SelectTrigger className="w-32 bg-white"><SelectValue placeholder="난이도" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">전체</SelectItem>
                  <SelectItem value="초급">초급</SelectItem>
                  <SelectItem value="중급">중급</SelectItem>
                  <SelectItem value="고급">고급</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <CardContent className="p-0 max-h-96 overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">
                      <Checkbox checked={allFilteredChecked} onCheckedChange={toggleCheckAll} />
                    </TableHead>
                    <TableHead>문제명</TableHead>
                    <TableHead>난이도</TableHead>
                    <TableHead>역량</TableHead>
                    <TableHead>점수</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredPool.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-8 text-slate-400">결과가 없습니다.</TableCell>
                    </TableRow>
                  ) : filteredPool.map((q) => {
                    const isAlreadyApplied = selectedQuestions.some(sq => sq.question_id === q.question_id);
                    return (
                      <TableRow key={`pool-${q.question_id}`} className={isAlreadyApplied ? "bg-slate-50 opacity-60" : ""}>
                        <TableCell>
                          <Checkbox
                            checked={checkedIds.has(q.question_id) || isAlreadyApplied}
                            disabled={isAlreadyApplied}
                            onCheckedChange={() => toggleCheck(q.question_id)}
                          />
                        </TableCell>
                        <TableCell className="max-w-[200px]">
                          <p className={`text-sm truncate ${isAlreadyApplied ? "line-through text-slate-400" : ""}`} title={q.title}>{q.title}</p>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary" className={difficultyColor[q.difficulty || ""] || "bg-slate-100"}>{q.difficulty}</Badge>
                        </TableCell>
                        <TableCell className="text-sm">{q.competency_type}</TableCell>
                        <TableCell className="text-sm">{q.score}점</TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
